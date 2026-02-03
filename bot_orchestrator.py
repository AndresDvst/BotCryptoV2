"""
Orquestador principal del bot de criptomonedas.
Refactor completo con inicialización robusta, cooldowns por categoría,
reintentos con backoff, separación análisis/publicación, health-check
y tracking de performance por paso.
"""
from services.binance_service import BinanceService
from services.market_sentiment_service import MarketSentimentService
from services.ai_analyzer_service import AIAnalyzerService
from services.telegram_service import TelegramService
from services.twitter_service import TwitterService

from utils.logger import logger

# Import opcional para traditional_markets_service (puede fallar en Python 3.14)
try:
    from services.traditional_markets_service import TraditionalMarketsService
except Exception as e:
    logger.warning(f"⚠️ No se pudo importar TraditionalMarketsService: {e}")
    TraditionalMarketsService = None

from services.technical_analysis_service import TechnicalAnalysisService
from services.price_monitor_service import PriceMonitorService
from services.tradingview_news_service import TradingViewNewsService
from services.news_service import NewsService
from services.backtest_service import BacktestService
from config.config import Config
from utils.logger import logger
from utils.security import get_redactor
from datetime import datetime, timedelta
import time
import json
import os
from database.mysql_manager import MySQLManager
from typing import Any, Dict, Optional, List, Tuple
import threading

class CryptoBotOrchestrator:
    """Orquestador principal que coordina servicios y ciclo de análisis/publicación"""

    COOLDOWNS: Dict[str, float] = {
        "market_analysis": 2.0,
        "technical_signals": 1.0,
        "news": 0.5,
        "price_alerts": 0.25,
        "stable_coins": 1.0,
    }

    COOLDOWN_FILE = "last_publication.json"

    class RecoverableError(Exception):
        """Error recuperable para reintentos automáticos"""

    class CriticalError(Exception):
        """Error crítico que aborta el ciclo"""

    class _PerfCtx:
        """Context manager auxiliar para medir tiempos de ejecución"""
        def __init__(self, end_fn):
            self._end = end_fn
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self._end()

    class PerformanceTracker:
        """Context manager para medir tiempos de pasos"""
        def __init__(self):
            self._steps: List[Tuple[str, float]] = []
        def step(self, name: str):
            start = time.time()
            def _end():
                elapsed = time.time() - start
                self._steps.append((name, elapsed))
            return CryptoBotOrchestrator._PerfCtx(_end)
        def summary(self) -> List[Tuple[str, float]]:
            return sorted(self._steps, key=lambda x: x[1], reverse=True)

    def __init__(self):
        """Inicializa servicios con modo degradado y prepara estructuras internas"""
        logger.info("=" * 60)
        logger.info("🤖 INICIANDO CRYPTO BOT")
        logger.info("=" * 60)
        Config.validate()
        self._services: Dict[str, Any] = {}
        self._failed_services: List[str] = []
        self._lock = threading.RLock()
        self._pub_lock = threading.RLock()
        self._category_last_pub: Dict[str, float] = self._load_last_publication_time()
        self._init_all_services()
        self._bind_service_attrs()

        # Registrar secretos desde Config en el redactor global para evitar fugas en logs
        try:
            get_redactor().register_secrets_from_config(Config)
        except Exception:
            pass

        if getattr(Config, "TWITTER_USERNAME", None) and getattr(Config, "TWITTER_PASSWORD", None):
            try:
                self.twitter.login_twitter(Config.TWITTER_USERNAME, Config.TWITTER_PASSWORD)
            except Exception as e:
                logger.warning(f"⚠️ Login automático de Twitter falló: {e}")

    def _init_service(self, name: str, cls: Any, critical: bool = False) -> None:
        """Inicializa un servicio con manejo de errores y modo degradado"""
        try:
            instance = cls()
            with self._lock:
                self._services[name] = instance
        except Exception as e:
            with self._lock:
                self._services[name] = None
                self._failed_services.append(name)
            if critical:
                raise RuntimeError(f"Servicio crítico {name} falló: {e}")
            logger.warning(f"⚠️ Servicio opcional {name} degradado: {e}")

    def _init_all_services(self) -> None:
        """Inicializa todos los servicios requeridos"""
        self._init_service("binance", BinanceService, critical=True)
        self._init_service("market_sentiment", MarketSentimentService, critical=False)
        self._init_service("ai_analyzer", AIAnalyzerService, critical=True)
        self._init_service("telegram", TelegramService, critical=False)
        self._init_service("twitter", TwitterService, critical=False)
        self._init_service("db", MySQLManager, critical=False)
        self._init_service("technical_analysis", TechnicalAnalysisService, critical=False)
        if TraditionalMarketsService is not None:
            self._init_service("traditional_markets", lambda: TraditionalMarketsService(self._services.get("telegram"), self._services.get("twitter"), self._services.get("ai_analyzer")), critical=False)
        else:
            logger.info("ℹ️ TraditionalMarketsService no disponible (compatibilidad Python 3.14)")
        self._init_service("price_monitor", lambda: PriceMonitorService(self._services.get("db"), self._services.get("telegram"), self._services.get("twitter")), critical=False)
        self._init_service("news_service", lambda: NewsService(self._services.get("db"), self._services.get("telegram"), self._services.get("twitter"), self._services.get("ai_analyzer")), critical=False)
        self._init_service("tradingview_news", lambda: TradingViewNewsService(self._services.get("telegram"), self._services.get("twitter"), self._services.get("ai_analyzer")), critical=False)
        self._init_service("backtest", lambda: BacktestService(self._services.get("binance")), critical=False)

    def _bind_service_attrs(self) -> None:
        """Expone servicios como atributos para compatibilidad"""
        self.binance = self._services.get("binance")
        self.market_sentiment = self._services.get("market_sentiment")
        self.ai_analyzer = self._services.get("ai_analyzer")
        self.telegram = self._services.get("telegram")
        self.twitter = self._services.get("twitter")
        self.db = self._services.get("db")
        self.traditional_markets = self._services.get("traditional_markets")
        self.technical_analysis = self._services.get("technical_analysis")
        self.price_monitor = self._services.get("price_monitor")
        self.news_service = self._services.get("news_service")
        self.tradingview_news = self._services.get("tradingview_news")
        self.backtest = self._services.get("backtest")

    def _load_last_publication_time(self) -> Dict[str, float]:
        """Carga timestamps por categoría desde JSON"""
        try:
            if os.path.exists(self.COOLDOWN_FILE):
                with open(self.COOLDOWN_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return {k: float(v) for k, v in data.items()}
            return {}
        except Exception:
            return {}

    def _save_last_publication_time(self, category: str) -> None:
        """Guarda timestamp por categoría con persistencia"""
        with self._pub_lock:
            self._category_last_pub[category] = time.time()
            try:
                with open(self.COOLDOWN_FILE, "w", encoding="utf-8") as f:
                    json.dump(self._category_last_pub, f, indent=2)
            except Exception:
                pass

    def _can_publish(self, category: str) -> bool:
        """Determina si puede publicar para una categoría según cooldown"""
        cooldown_hours = self.COOLDOWNS.get(category, 1.0)
        last_ts = self._category_last_pub.get(category)
        if not last_ts:
            return True
        hours = (time.time() - last_ts) / 3600.0
        return hours >= cooldown_hours

    def _log_summary(self, key: str, text: str, max_lines: int = 3) -> None:
        """Logea solo primeras líneas de un resumen"""
        lines = text.strip().splitlines()
        snippet = "\n".join(lines[:max_lines])
        logger.info(f"{key}:\n{snippet}")

    def health_check(self) -> Dict[str, Any]:
        """Verifica estado de servicios y reconecta Twitter si es posible"""
        status: Dict[str, Any] = {}
        status["binance"] = bool(self.binance)
        status["ai_analyzer"] = bool(self.ai_analyzer)
        status["market_sentiment"] = bool(self.market_sentiment)
        status["telegram"] = bool(self.telegram)
        status["twitter"] = bool(self.twitter and getattr(self.twitter, "driver", None))
        if self.twitter and not status["twitter"] and getattr(Config, "TWITTER_USERNAME", None) and getattr(Config, "TWITTER_PASSWORD", None):
            try:
                ok = self.twitter.login_twitter(Config.TWITTER_USERNAME, Config.TWITTER_PASSWORD)
                status["twitter"] = bool(ok and getattr(self.twitter, "driver", None))
            except Exception:
                status["twitter"] = False
        status["failed_services"] = list(self._failed_services)
        return status

    def _execute_analysis_steps(self) -> Dict[str, Any]:
        """Ejecuta pasos de análisis y retorna resultados agregados"""
        if not self.binance or not self.ai_analyzer:
            raise self.CriticalError("Servicios críticos no disponibles")
        perf = self.PerformanceTracker()
        with perf.step("binance_filter"):
            significant_coins = self.binance.filter_significant_changes()
            if not significant_coins:
                raise self.RecoverableError("Sin monedas significativas")
        with perf.step("binance_2h"):
            # Enriquecer monedas con cambio 2h sobre una muestra amplia del mercado (top por volumen)
            try:
                all_tickers = self.binance.get_all_tickers()
                # Filtrar pares USDT y ordenar por volumen (quoteVolume o volume)
                usdt_pairs = [ (s, d) for s, d in all_tickers.items() if s.endswith('/USDT') ]
                usdt_pairs_sorted = sorted(
                    usdt_pairs,
                    key=lambda sd: float(sd[1].get('quoteVolume') or sd[1].get('volume') or 0.0),
                    reverse=True,
                )

                top_n = int(getattr(Config, 'BINANCE_TOP_2H_SCAN_LIMIT', 150))
                top_symbols = [s for s, _ in usdt_pairs_sorted[:top_n]]
                coins_for_2h = [{'symbol': sym} for sym in top_symbols]
                coins_enriched = self.binance.get_2hour_change(coins_for_2h)
            except Exception as e:
                logger.warning(f"⚠️ Error obteniendo cambios 2h globales: {e}")
                # Fallback: enriquecer solo las monedas significativas (comportamiento previo)
                coins_enriched = self.binance.get_2hour_change(significant_coins)
        with perf.step("technical_analysis"):
            technical_signals = None
            if self.technical_analysis:
                technical_signals = self.technical_analysis.analyze_significant_coins(
                    significant_coins,
                    telegram=self.telegram,
                    twitter=self.twitter
                )
        with perf.step("market_sentiment"):
            market_data = None
            if self.market_sentiment:
                market_data = self.market_sentiment.analyze_market_sentiment()
                
        # --- NUEVO: ANÁLISIS BATCH (Todo en una llamada) ---
        with perf.step("ai_batch_analysis"):
            # Obtener noticias top para el contexto
            news_titles = []
            if self.news_service:
                 # Hack: traer ultimas noticias de DB o memoria si es posible
                 # Por simplicidad, pasamos lista vacía o implementamos get_recent_titles en news_service luego
                 pass
            
            # Llamada optimizada
            batch_result = self.ai_analyzer.analyze_complete_market_batch(
                coins=coins_enriched,
                market_sentiment=market_data,
                news_titles=news_titles
            )
            
        summary = perf.summary()
        logger.info("⏱ Performance por paso:")
        for name, elapsed in summary:
            logger.info(f"{name}: {elapsed:.2f}s")
            
        return {
            "significant_coins": significant_coins,
            "coins_enriched": coins_enriched,
            "technical_signals": technical_signals,
            "market_data": market_data,
            # Mapear resultado batch a estructura esperada
            "ai_analysis": {
                "full_analysis": batch_result['market_analysis'].get('overview', ''),
                "recommendation": batch_result['trading_summary'].get('main_recommendation', ''),
                "confidence_level": batch_result['trading_summary'].get('confidence', 0),
                "top_buys": batch_result['crypto_recommendations'].get('top_buys', []),
                "top_sells": batch_result['crypto_recommendations'].get('top_sells', []),
            },
            # Generar tweets localmente con funcion existing o usar logic nueva?
            # Por consistencia, usamos la funcion de AI service que ya teniamos para generar los 4 tweets
            # usando los datos enriquecidos localmente, ya que el batch analysis no retorna tweets formateados.
            "twitter_summaries": self.ai_analyzer.generate_twitter_4_summaries(
                market_data, significant_coins, coins_enriched, max_chars=280
            ),
        }

    def _publish_twitter_batch(self, summaries: Dict[str, str], delay_seconds: int = 30) -> Dict[str, bool]:
        """Publica resúmenes en batch con delay configurable"""
        result = {"up_24h": False, "down_24h": False, "up_2h": False, "down_2h": False}
        if not self.twitter:
            return result
        image_24h = getattr(Config, "REPORT_24H_IMAGE_PATH", None)
        image_2h = getattr(Config, "REPORT_2H_IMAGE_PATH", None)
        order = [("up_24h", image_24h), ("down_24h", image_24h), ("up_2h", image_2h), ("down_2h", image_2h)]
        for key, img in order:
            ok = self.twitter.post_tweet(summaries.get(key, ""), img)
            result[key] = bool(ok)
            time.sleep(delay_seconds)
        return result

    def _publish_stable_coins_2h(self) -> None:
        """Genera y publica cambios 2h de monedas estables configuradas"""
        if not self.binance or not self.twitter:
            return
        symbols = getattr(Config, "STABLE_COINS", ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "LTC/USDT"])
        stable_coins = [{"symbol": s} for s in symbols]
        enriched = self.binance.get_2hour_change(stable_coins)
        lines: List[str] = []
        for coin in enriched:
            sym = coin.get("symbol", "").replace("/USDT", "")
            ch2 = coin.get("change_2h")
            if ch2 is not None:
                arrow = "📈" if ch2 >= 0 else "📉"
                lines.append(f"{sym}{arrow} 2h:{ch2:+.1f}%")
        content = "⏱ Cambios 2h - Cryptos estables:\n" + ("\n".join(lines) if lines else "Sin cambios disponibles")
        ok = self.twitter.post_tweet(content.strip(), image_path=getattr(Config, "REPORT_2H_IMAGE_PATH", None), category="crypto_stable")
        if not ok:
            if getattr(self.twitter, "last_reason", None) == "duplicate":
                logger.info("⏭️ Tweet duplicado (Cryptos estables 2h), saltando publicación")
            else:
                logger.error("❌ Falló la publicación en Twitter (Cryptos estables 2h)")
        if self.telegram:
            self.telegram.send_crypto_message(content.strip(), image_path=getattr(Config, "REPORT_2H_IMAGE_PATH", None))

    def _publish_results(self, results: Dict[str, Any], category: str) -> Dict[str, Any]:
        """Publica resultados según categoría y retorna estado"""
        status = {"telegram": False, "twitter": False}
        can_pub = self._can_publish(category)
        if not can_pub:
            return status
        twitter_summaries = results.get("twitter_summaries", {})
        ai_analysis = results.get("ai_analysis")
        market_data = results.get("market_data")
        significant_coins = results.get("significant_coins", [])
        coins_enriched = results.get("coins_enriched", [])
        if self.telegram:
            status["telegram"] = bool(self.telegram.send_report(ai_analysis, market_data, significant_coins, coins_enriched))
        tw = self._publish_twitter_batch(twitter_summaries, delay_seconds=30)
        status["twitter"] = all(tw.values())
        if status["twitter"]:
            self._save_last_publication_time(category)
        if category == "stable_coins":
            self._publish_stable_coins_2h()
        return status

    def run_analysis_cycle(self, category: str = "market_analysis", max_retries: int = 3, dry_run: bool = False, is_morning: bool = False) -> bool:
        """Ejecuta ciclo de análisis con reintentos y publicación separada"""
        hc = self.health_check()
        if not hc.get("binance") or not hc.get("ai_analyzer"):
            logger.error("❌ Servicios críticos no disponibles")
            return False
        backoffs = [30, 60, 120]
        attempt = 0
        if self.ai_analyzer:
            self.ai_analyzer.reset_cycle_status()
        while attempt < max_retries:
            attempt += 1
            try:
                logger.info(f"🚀 Inicio ciclo análisis {category} intento {attempt}")
                results = self._execute_analysis_steps()
                if is_morning and self.tradingview_news:
                    try:
                        self.tradingview_news.publish_morning_report(self.telegram, self.twitter)
                    except Exception:
                        pass
                
                # --- ANÁLISIS DE MERCADOS TRADICIONALES (3 veces al día) ---
                if self.traditional_markets:
                    current_hour = datetime.now().hour
                    # Ejecutar a las 8 (mañana), 14 (tarde), 20 (noche) aprox.
                    # Se usa un rango pequeño para asegurar ejecución
                    target_hours = [8, 14, 20]
                    # Solo si estamos en la hora target y no se ha ejecutado recientemente (cooldown simple)
                    should_run_signals = any(h == current_hour for h in target_hours)
                    
                    # Ejecutar siempre el resumen general (movers), pero signals solo en horas clave
                    try:
                        self.traditional_markets.run_traditional_markets_analysis(publish=True, get_signals=should_run_signals)
                    except Exception as e:
                       logger.error(f"❌ Error en análisis tradicional: {e}")

                # --- NOTICIAS ---
                if self.news_service:
                    try:
                        self.news_service.run_news_scraping_cycle()
                    except Exception as e:
                        logger.error(f"❌ Error en ciclo de noticias: {e}")

                if self.tradingview_news and not is_morning: # Evitar duplicar con reporte matutino
                     try:
                        self.tradingview_news.process_and_publish()
                     except Exception as e:
                        logger.error(f"❌ Error en ciclo de noticias TradingView: {e}")

                if dry_run:
                    logger.info("🧪 Dry-run activo, no se publica")
                    return True
                pub = self._publish_results(results, category)
                self._log_summary("Resumen up_24h", results["twitter_summaries"].get("up_24h", ""), max_lines=3)
                self._log_summary("Resumen down_24h", results["twitter_summaries"].get("down_24h", ""), max_lines=3)
                self._log_summary("Resumen up_2h", results["twitter_summaries"].get("up_2h", ""), max_lines=3)
                self._log_summary("Resumen down_2h", results["twitter_summaries"].get("down_2h", ""), max_lines=3)
                next_execution = datetime.now() + timedelta(hours=Config.REPORT_INTERVAL_HOURS)
                logger.info(f"⏰ Próxima ejecución: {next_execution.strftime('%Y-%m-%d %H:%M:%S')}")
                if self.ai_analyzer and self.ai_analyzer.get_cycle_status():
                    logger.info("✅ Conexión con proveedores IA: OK")
                else:
                    logger.info("❌ Conexión con proveedores IA: FALLIDA")
                return bool(pub["telegram"] or pub["twitter"])
            except self.RecoverableError as e:
                if attempt >= max_retries:
                    logger.error(f"❌ Error recuperable agotó reintentos: {e}")
                    logger.info("❌ Conexión con proveedores IA: FALLIDA")
                    return False
                delay = backoffs[min(attempt - 1, len(backoffs) - 1)]
                logger.warning(f"⚠️ Error recuperable: {e}. Reintentando en {delay}s")
                time.sleep(delay)
                continue
            except self.CriticalError as e:
                logger.error(f"❌ Error crítico: {e}")
                logger.info("❌ Conexión con proveedores IA: FALLIDA")
                return False
            except Exception as e:
                if attempt >= max_retries:
                    logger.error(f"❌ Error inesperado: {e}")
                    logger.info("❌ Conexión con proveedores IA: FALLIDA")
                    return False
                delay = backoffs[min(attempt - 1, len(backoffs) - 1)]
                logger.warning(f"⚠️ Error inesperado: {e}. Reintentando en {delay}s")
                time.sleep(delay)
                continue

    def setup_twitter_login(self, username: str, password: str) -> bool:
        """Configura login de Twitter"""
        if not self.twitter:
            return False
        try:
            return bool(self.twitter.login_twitter(username, password))
        except Exception:
            return False

    def cleanup(self) -> None:
        """Cierra recursos"""
        try:
            if self.twitter:
                self.twitter.close()
        except Exception:
            pass

class _PerfCtx:
    def __init__(self, end_cb):
        self._end = end_cb
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        self._end()

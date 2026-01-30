"""
Orquestador principal del bot de criptomonedas.
Coordina todos los servicios y ejecuta el flujo completo del análisis.
"""
from services.binance_service import BinanceService
from services.market_sentiment_service import MarketSentimentService
from services.ai_analyzer_service import AIAnalyzerService
from services.telegram_service import TelegramService
from services.twitter_service import TwitterService
from services.traditional_markets_service import TraditionalMarketsService
from services.technical_analysis_service import TechnicalAnalysisService
from services.price_monitor_service import PriceMonitorService
from services.tradingview_news_service import TradingViewNewsService
from services.news_service import NewsService
from config.config import Config
from utils.logger import logger
from datetime import datetime, timedelta
import time
import json
import os
from database.mysql_manager import MySQLManager

class CryptoBotOrchestrator:
    """Orquestador principal que coordina todos los servicios"""
    
    # Archivo para guardar timestamps de última publicación
    COOLDOWN_FILE = "last_publication.json"
    COOLDOWN_HOURS = 2  # Horas de cooldown entre publicaciones
    
    def __init__(self):
        """Inicializa todos los servicios necesarios"""
        logger.info("=" * 60)
        logger.info("🤖 INICIANDO CRYPTO BOT")
        logger.info("=" * 60)
        
        try:
            # Validar configuración
            Config.validate()
            
            # Inicializar servicios básicos
            self.binance = BinanceService()
            self.market_sentiment = MarketSentimentService()
            self.ai_analyzer = AIAnalyzerService()
            self.telegram = TelegramService()
            self.twitter = TwitterService()
            self.db = MySQLManager()
            
            # Inicializar servicios V3
            self.traditional_markets = TraditionalMarketsService(self.telegram, self.twitter)
            self.technical_analysis = TechnicalAnalysisService()
            self.price_monitor = PriceMonitorService(self.db, self.telegram, self.twitter)
            self.news_service = NewsService(self.db, self.telegram, self.twitter, self.ai_analyzer)
            self.tradingview_news = TradingViewNewsService(self.telegram, self.twitter, self.ai_analyzer)

            # Intentar login automático en Twitter si hay credenciales en la configuración
            if getattr(Config, 'TWITTER_USERNAME', None) and getattr(Config, 'TWITTER_PASSWORD', None):
                try:
                    login_ok = self.twitter.login_twitter(Config.TWITTER_USERNAME, Config.TWITTER_PASSWORD)
                    if login_ok:
                        logger.info("✅ Twitter: login automático completado")
                    else:
                        logger.warning("⚠️ Twitter: login automático falló")
                except Exception as e:
                    logger.error(f"❌ Error en login automático de Twitter: {e}")
            
            logger.info("✅ Todos los servicios inicializados correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error crítico al inicializar servicios: {e}")
            raise
    
    def _load_last_publication_time(self) -> dict:
        """Carga el timestamp de la última publicación desde archivo JSON"""
        try:
            if os.path.exists(self.COOLDOWN_FILE):
                with open(self.COOLDOWN_FILE, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.warning(f"⚠️ Error cargando cooldown: {e}")
            return {}
    
    def _save_last_publication_time(self):
        """Guarda el timestamp actual como última publicación"""
        try:
            data = {
                'last_publication': datetime.now().isoformat(),
                'timestamp': time.time()
            }
            with open(self.COOLDOWN_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"✅ Timestamp de publicación guardado")
        except Exception as e:
            logger.warning(f"⚠️ Error guardando cooldown: {e}")
    
    def _can_publish(self) -> bool:
        """
        Verifica si han pasado suficientes horas desde la última publicación.
        
        Returns:
            True si puede publicar, False si está en cooldown
        """
        last_pub = self._load_last_publication_time()
        
        if not last_pub or 'timestamp' not in last_pub:
            logger.info("✅ Primera publicación, no hay cooldown")
            return True
        
        last_time = last_pub['timestamp']
        current_time = time.time()
        hours_passed = (current_time - last_time) / 3600
        
        if hours_passed >= self.COOLDOWN_HOURS:
            logger.info(f"✅ Han pasado {hours_passed:.1f} horas, puede publicar")
            return True
        else:
            hours_remaining = self.COOLDOWN_HOURS - hours_passed
            logger.warning(f"⏳ COOLDOWN ACTIVO: Faltan {hours_remaining:.1f} horas para poder publicar")
            logger.warning(f"   Última publicación: {last_pub.get('last_publication', 'N/A')}")
            return False
    
    def run_analysis_cycle(self, is_morning: bool = False) -> bool:
        """
        Ejecuta un ciclo completo de análisis.
        
        Args:
            is_morning: True si es el reporte matutino de las 6 AM
            
        Returns:
            True si el ciclo se completó exitosamente
        """
        try:
            start_time = time.time()
            logger.info("\n" + "=" * 60)
            logger.info(f"🚀 INICIANDO CICLO DE ANÁLISIS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 60 + "\n")
            
            # PASO 1: Consultar Binance y filtrar monedas
            logger.info("📊 PASO 1: Consultando Binance y filtrando monedas...")
            significant_coins = self.binance.filter_significant_changes()
            if not significant_coins:
                logger.warning("⚠️ No se encontraron monedas con cambios significativos")
                return False

            # PASO 2: Obtener cambios de 2 horas usando Binance
            logger.info("\n⏱️ PASO 2: Consultando cambios de 2h en Binance...")
            coins_enriched = self.binance.get_2hour_change(significant_coins)

            # Verificar cooldown antes de publicar
            can_publish = self._can_publish()

            # PASO 2.5: Análisis técnico de monedas significativas (Top 5 LONG/SHORT)
            logger.info("\n🎯 PASO 2.5: Análisis técnico de monedas significativas...")
            technical_signals = self.technical_analysis.analyze_significant_coins(
                significant_coins,
                self.telegram if can_publish else None,
                self.twitter if can_publish else None,
                capital=30,
                risk_percent=30
            )

            # PASO 3: Analizar sentimiento del mercado
            logger.info("\n🌡️ PASO 3: Analizando sentimiento del mercado...")
            market_data = self.market_sentiment.analyze_market_sentiment()

            # PASO 4: Análisis con IA (Sentimiento de Mercado)
            logger.info("\n🧠 PASO 4: Analizando datos con Inteligencia Artificial (Gemini)...")
            ai_analysis = self.ai_analyzer.analyze_and_recommend(
                coins_enriched,
                market_data
            )

            # PASO 4.5: Scraping de Noticias TradingView
            if can_publish:
                logger.info("\n📰 PASO 4.5: Buscando noticias en TradingView...")
                self.tradingview_news.process_and_publish()
            else:
                logger.info("\n⏭️ PASO 4.5: SALTADO - Cooldown activo, no se buscarán noticias")

            # PASO 5: Generar resúmenes para Twitter
            logger.info("\n✍️ PASO 5: Generando resúmenes para Twitter...")
            twitter_summaries = self.ai_analyzer.generate_twitter_4_summaries(
                market_data,
                significant_coins,  # Monedas sin datos de 2h
                coins_enriched,     # Monedas con datos de 2h
                max_chars=280
            )
            
            # PASO 6: Enviar a Telegram (solo si no hay cooldown)
            telegram_success = False
            if can_publish:
                logger.info("\n✈️ PASO 6: Enviando reporte detallado a Telegram...")
                telegram_success = self.telegram.send_report(
                    ai_analysis,
                    market_data,
                    significant_coins,  # Monedas sin datos de 2h
                    coins_enriched      # Monedas con datos de 2h
                )
            else:
                logger.info("\n⏭️ PASO 6: SALTADO - Cooldown activo, no se enviará a Telegram")

            # PASO 8: Publicar en Twitter (solo si no hay cooldown)
            twitter_success_up_24h = False
            twitter_success_down_24h = False
            twitter_success_up_2h = False
            twitter_success_down_2h = False
            
            if can_publish:
                logger.info("\n🐦 PASO 7: Publicando en Twitter...")
                if is_morning:
                    image_path = Config.MORNING_IMAGE_PATH
                    logger.info("☀️ Usando imagen de reporte matutino")
                else:
                    image_path = Config.REPORT_IMAGE_PATH
                    logger.info("📊 Usando imagen de reporte regular")

                import time as _time
                twitter_success_up_24h = self.twitter.post_tweet(twitter_summaries["up_24h"], image_path)
                logger.info("⏳ Esperando 30 segundos para la siguiente publicación...")
                _time.sleep(30)
                twitter_success_down_24h = self.twitter.post_tweet(twitter_summaries["down_24h"], image_path)
                logger.info("⏳ Esperando 30 segundos para la siguiente publicación...")
                _time.sleep(30)
                twitter_success_up_2h = self.twitter.post_tweet(twitter_summaries["up_2h"], image_path)
                logger.info("⏳ Esperando 30 segundos para la siguiente publicación...")
                _time.sleep(30)
                twitter_success_down_2h = self.twitter.post_tweet(twitter_summaries["down_2h"], image_path)
                
                # Guardar timestamp de publicación exitosa
                if twitter_success_up_24h or twitter_success_down_24h:
                    self._save_last_publication_time()
                
                # Publicación extra: Cambio 2h de monedas estables (BTC, ETH, SOL, BNB, LTC)
                try:
                    stable_symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'LTC/USDT']
                    stable_coins = [{'symbol': s} for s in stable_symbols]
                    logger.info("⏱️ Generando cambios 2h de monedas estables (BTC, ETH, SOL, BNB, LTC)...")
                    stable_enriched = self.binance.get_2hour_change(stable_coins)
                    lines = []
                    for coin in stable_enriched:
                        sym = coin.get('symbol', '').replace('/USDT', '')
                        ch2 = coin.get('change_2h', None)
                        if ch2 is not None:
                            arrow = '📈' if ch2 >= 0 else '📉'
                            lines.append(f"{sym}{arrow} 2h:{ch2:+.1f}%")
                    tweet_stables = "⏱ Cambios 2h - Estables:\n" + ("\n".join(lines) if lines else "Sin cambios disponibles")
                    logger.info("🐦 Publicando estables 2h en Twitter...")
                    self.twitter.post_tweet(tweet_stables.strip(), category='crypto_stable')
                except Exception as e:
                    logger.warning(f"⚠️ Error generando/publicando estables 2h: {e}")
            else:
                logger.info("\n⏭️ PASO 7: SALTADO - Cooldown activo, no se publicará en Twitter")

            logger.info(f"\n📝 RESUMEN SUBIDAS 24H ({len(twitter_summaries['up_24h'])} caracteres):")
            logger.info("-" * 60)
            logger.info(twitter_summaries["up_24h"])
            logger.info("-" * 60)
            logger.info(f"\n📝 RESUMEN BAJADAS 24H ({len(twitter_summaries['down_24h'])} caracteres):")
            logger.info("-" * 60)
            logger.info(twitter_summaries["down_24h"])
            logger.info("-" * 60)
            logger.info(f"\n📝 RESUMEN SUBIDAS 2H ({len(twitter_summaries['up_2h'])} caracteres):")
            logger.info("-" * 60)
            logger.info(twitter_summaries["up_2h"])
            logger.info("-" * 60)
            logger.info(f"\n📝 RESUMEN BAJADAS 2H ({len(twitter_summaries['down_2h'])} caracteres):")
            logger.info("-" * 60)
            logger.info(twitter_summaries["down_2h"])
            logger.info("-" * 60)

            # Estadísticas finales
            elapsed_time = time.time() - start_time
            logger.info("\n" + "=" * 60)
            logger.info("✅ CICLO COMPLETADO EXITOSAMENTE")
            logger.info(f"⏱ Tiempo total: {elapsed_time:.2f} segundos")
            logger.info(f"📊 Monedas analizadas: {len(coins_enriched)}")
            logger.info(f"📱 Telegram: {'✅ Enviado' if telegram_success else '❌ Error'}")
            logger.info(f"🐦 Twitter: {'✅ Publicado' if twitter_success_up_24h and twitter_success_down_24h and twitter_success_up_2h and twitter_success_down_2h else '⚠️ Error'}")

            # Mostrar próxima ejecución
            next_execution = datetime.now() + timedelta(hours=Config.REPORT_INTERVAL_HOURS)
            logger.info(f"⏰ Próxima ejecución: {next_execution.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 60 + "\n")

            return True

            
        except Exception as e:
            logger.error(f"❌ Error en el ciclo de análisis: {e}")
            # Mostrar próxima ejecución incluso si hay error
            try:
                next_execution = datetime.now() + timedelta(hours=Config.REPORT_INTERVAL_HOURS)
                logger.info(f"⏰ Próxima ejecución programada: {next_execution.strftime('%Y-%m-%d %H:%M:%S')}")
            except Exception:
                pass
            return False
    
    def setup_twitter_login(self, username: str, password: str):
        """
        Configura el login de Twitter (se hace una sola vez).
        
        Args:
            username: Usuario de Twitter
            password: Contraseña de Twitter
        """
        try:
            logger.info("🐦 Configurando login de Twitter...")
            success = self.twitter.login_twitter(username, password)
            
            if success:
                logger.info("✅ Twitter configurado correctamente")
            else:
                logger.error("❌ Error al configurar Twitter")
            
            return success
        except Exception as e:
            logger.error(f"❌ Error al configurar Twitter: {e}")
            return False
    
    def cleanup(self):
        """Limpia recursos y cierra conexiones"""
        logger.info("🧹 Limpiando recursos...")
        try:
            self.twitter.close()
            logger.info("✅ Recursos liberados")
        except Exception as e:
            logger.warning(f"⚠️ Error al limpiar recursos: {e}")

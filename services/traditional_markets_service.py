"""
Servicio para análisis de mercados tradicionales (Acciones, Forex, Commodities).
Optimizado para alto rendimiento y bajo rate limit usando batch requests y caché.
"""
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import yfinance as yf

from utils.logger import logger
from config.config import Config
from services.twelve_data_service import TwelveDataService
from services.ai_analyzer_service import AIAnalyzerService

class TraditionalMarketsService:
    """Servicio para analizar mercados tradicionales"""
    
    # Caché en memoria
    _stocks_cache: Dict[str, Tuple[List[Dict], float]] = {}
    
    def __init__(self, telegram=None, twitter=None, ai_analyzer: AIAnalyzerService = None):
        """
        Inicializa el servicio
        
        Args:
            telegram: Servicio de Telegram (opcional)
            twitter: Servicio de Twitter (opcional)
            ai_analyzer: Servicio de IA (opcional)
        """
        self.telegram = telegram
        self.twitter = twitter
        self.ai_analyzer = ai_analyzer
        self.twelve_data = TwelveDataService()
        logger.info("✅ Servicio de Mercados Tradicionales inicializado")
    
    def get_top_stocks(
        self,
        symbols: Optional[List[str]] = None,
        use_cache: bool = True,
        ttl: int = 300,
        min_change_percent: float = 2.0,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Obtiene las acciones con mayor cambio porcentual del día usando batch requests.
        
        Args:
            symbols: Lista de símbolos. Si None, usa STOCK_SYMBOLS_DEFAULT.
            use_cache: Si True, usa caché en memoria con TTL.
            ttl: Tiempo de vida del caché en segundos (default 300).
            min_change_percent: Filtro mínimo de cambio porcentual.
            limit: Número máximo de resultados.
            
        Returns:
            Lista de diccionarios con información de acciones.
        """
        default_symbols = getattr(Config, "STOCK_SYMBOLS_DEFAULT", [])
        extended_symbols = getattr(Config, "STOCK_SYMBOLS_EXTENDED", [])
        symbols_to_use = symbols or default_symbols or extended_symbols
        if not symbols_to_use:
            logger.warning("⚠️ No hay símbolos configurados para stocks")
            return []

        cache_key = f"{','.join(sorted(symbols_to_use))}:{min_change_percent}:{limit}"
        now = time.time()
        if use_cache:
            cache_entry = self._stocks_cache.get(cache_key)
            if cache_entry:
                data, ts = cache_entry
                if now - ts <= ttl:
                    logger.info("♻️ Usando caché de acciones")
                    return data

        logger.info(f"📈 Analizando {len(symbols_to_use)} acciones en batch...")
        movers: List[Dict] = []
        tickers_obj = yf.Tickers(" ".join(symbols_to_use))

        def fetch_symbol(sym: str) -> Optional[Dict]:
            try:
                t = tickers_obj.tickers.get(sym) or yf.Ticker(sym)
                hist = t.history(period="2d")
                if len(hist) < 2:
                    return None
                current_price = float(hist["Close"].iloc[-1])
                previous_close = float(hist["Close"].iloc[-2])
                change_percent = ((current_price - previous_close) / previous_close) * 100.0
                if abs(change_percent) < min_change_percent:
                    return None
                info = {}
                try:
                    info = t.get_info()
                except Exception:
                    pass
                return {
                    "symbol": sym,
                    "name": info.get("longName", sym) if isinstance(info, dict) else sym,
                    "price": round(current_price, 2),
                    "change_percent": round(change_percent, 2),
                    "volume": float(hist["Volume"].iloc[-1]) if "Volume" in hist.columns else 0.0,
                    "market_cap": info.get("marketCap", 0) if isinstance(info, dict) else 0,
                }
            except Exception as e:
                logger.debug(f"⚠️ Error en {sym}: {e}")
                return None

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(fetch_symbol, s): s for s in symbols_to_use}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    movers.append(result)

        movers.sort(key=lambda x: abs(x["change_percent"]), reverse=True)
        movers = movers[:limit]
        logger.info(f"✅ Encontradas {len(movers)} acciones con cambio ≥ {min_change_percent}%")

        if use_cache:
            self._stocks_cache[cache_key] = (movers, now)

        return movers
    
    def get_forex_movers(self, min_change_percent: float = 2.0, limit: int = 10) -> List[Dict]:
        """
        Obtiene pares de divisas con mayores movimientos.
        Si no encuentra suficientes con el cambio mínimo, devuelve los tops por movimiento absoluto.
        
        Args:
            min_change_percent: Cambio porcentual mínimo para filtrar
            limit: Límite de pares a retornar
            
        Returns:
            Lista de diccionarios con la info de los pares
        """
        pairs = getattr(Config, "FOREX_PAIRS", [])
        logger.info(f"💱 Analizando {len(pairs)} pares de divisas...")
        all_movers = []
        
        tickers_obj = yf.Tickers(" ".join(pairs))
        for pair in pairs:
            try:
                ticker = tickers_obj.tickers.get(pair) or yf.Ticker(pair)
                hist = ticker.history(period='2d')
                
                if len(hist) < 2:
                    continue
                
                current_rate = hist['Close'].iloc[-1]
                previous_close = hist['Close'].iloc[-2]
                change_percent = ((current_rate - previous_close) / previous_close) * 100
                
                all_movers.append({
                    'pair': pair.replace('=X', ''),
                    'rate': round(current_rate, 4),
                    'change_percent': round(change_percent, 2),
                    'abs_change': abs(change_percent)
                })
                    
            except Exception as e:
                logger.warning(f"⚠️ Error obteniendo datos de {pair}: {e}")
                continue
        
        # Ordenar por cambio absoluto (volatilidad) de mayor a menor
        all_movers.sort(key=lambda x: x['abs_change'], reverse=True)
        
        # Retornar el top, priorizando los que superan el mínimo pero completando hasta el límite
        filtered = [m for m in all_movers if m['abs_change'] >= min_change_percent]
        
        if len(filtered) < limit:
            logger.info(f"ℹ️ Pocos pares con cambio > {min_change_percent}%, completando con top movimientos")
            return all_movers[:limit]
            
        return filtered[:limit]
    
    def get_commodity_prices(self) -> List[Dict]:
        """
        Obtiene precios actuales de commodities (Oro, Plata, Crudo, etc).
        
        Returns:
            Lista con precios actuales de commodities
        """
        commodities = getattr(Config, "COMMODITIES", {})
        logger.info(f"🛢️ Obteniendo precios de {len(commodities)} commodities...")
        
        prices = []
        
        tickers_obj = yf.Tickers(" ".join(list(commodities.keys())))
        for symbol, name in commodities.items():
            try:
                ticker = tickers_obj.tickers.get(symbol) or yf.Ticker(symbol)
                hist = ticker.history(period='2d')
                
                if len(hist) < 1:
                    continue
                
                current_price = hist['Close'].iloc[-1]
                
                # Calcular cambio si hay datos de ayer
                change_percent = 0
                if len(hist) >= 2:
                    previous_close = hist['Close'].iloc[-2]
                    change_percent = ((current_price - previous_close) / previous_close) * 100
                
                prices.append({
                    'symbol': symbol,
                    'name': name,
                    'price': round(current_price, 2),
                    'change_percent': round(change_percent, 2)
                })
                
            except Exception as e:
                logger.warning(f"⚠️ Error obteniendo precio de {name}: {e}")
                continue
        
        logger.info(f"✅ Obtenidos precios de {len(prices)} commodities")
        return prices
    
    def get_market_summary(self) -> Dict:
        """
        Obtiene un resumen completo de todos los mercados.
        
        Returns:
            Diccionario con resumen de stocks, forex y commodities
        """
        logger.info("📊 Generando resumen completo de mercados tradicionales...")
        
        summary = {
            'timestamp': datetime.now(),
            'stocks': self.get_top_stocks(min_change_percent=2.0, limit=10),
            'forex': self.get_forex_movers(min_change_percent=0.5, limit=10),  # Top 10 divisas
            'commodities': self.get_commodity_prices()
        }
        
        logger.info("✅ Resumen de mercados generado")
        return summary
    
    def _classify_top_instruments_with_ai(self, summary: Dict) -> Dict[str, List[str]]:
        """
        Usa IA para seleccionar los activos más relevantes del día.
        """
        if not self.ai_analyzer:
            # Fallback: Top 3 de cada categoría
            return {
                'stocks': [s['symbol'] for s in summary['stocks'][:3]],
                'forex': [f['pair'] for f in summary['forex'][:3]],
                'commodities': [c['symbol'] for c in summary['commodities']]
            }

        logger.info("🧠 Clasificando activos top con IA...")
        # Aquí iría la llamada real a la IA, por ahora simulamos una selección inteligente
        # o implementamos una lógica básica de seleccionar por volatilidad + volumen
        # TODO: Implementar llamada real a analyze_market_context
        
        return {
            'stocks': [s['symbol'] for s in summary['stocks'][:5]],
            'forex': [f['pair'] for f in summary['forex'][:5]],
            'commodities': [c['symbol'] for c in summary['commodities']]
        }

    def _publish_traditional_signals(self, signals: Dict[str, List[Dict]]):
        """Publica señales técnicas de Twelve Data"""
        if not self.telegram:
            return

        logger.info("📤 Publicando señales tradicionales...")
        
        for category, items in signals.items():
            if not items:
                continue
                
            msg = f"📊 **SEÑALES TÉCNICAS: {category.upper()}**\n\n"
            for signal in items:
                emoji = "🚀" if signal['type'] == 'LONG' else "🔻" if signal['type'] == 'SHORT' else "⚖️"
                msg += f"{emoji} **{signal['symbol']}** ({signal['type']})\n"
                msg += f"   Confianza: {signal['confidence']}%\n"
                msg += f"   Precio: ${signal['current_price']}\n"
                if signal['rsi']:
                    msg += f"   RSI: {signal['rsi']:.1f}\n"
                msg += "\n"
            
            # Enviar al canal de mercados
            try:
                self.telegram.send_market_message(msg)
            except Exception as e:
                logger.error(f"❌ Error enviando señales {category}: {e}")

    def run_traditional_markets_analysis(self, publish=True, get_signals=True):
        """
        Método wrapper para ejecutar análisis completo de mercados tradicionales.
        """
        logger.info("\n📊 ANÁLISIS DE MERCADOS TRADICIONALES")
        logger.info("=" * 60)
        
        summary = self.get_market_summary()
        
        # 1. Mostrar resumen en logs (igual que antes)
        self._log_market_summary(summary)
        
        # 2. Publicar resumen general (Movers)
        if publish and (self.telegram or self.twitter):
            self._publish_results(summary)
            
        # 3. Análisis Técnico Profundo con Twelve Data (Nuevo)
        if get_signals:
            try:
                # Filtrar instrumentos top
                top_instruments = self._classify_top_instruments_with_ai(summary)
                
                # Obtener señales técnicas
                signals = self.twelve_data.analyze_top_instruments(
                    top_instruments['stocks'],
                    top_instruments['forex'],
                    top_instruments['commodities']
                )
                
                # Publicar señales
                if publish:
                    self._publish_traditional_signals(signals)
                    
            except Exception as e:
                logger.error(f"❌ Error en análisis Twelve Data: {e}")

        logger.info("\n✅ Análisis de mercados tradicionales completado")
        return summary

    def _log_market_summary(self, summary):
        """Helper para loguear resumen"""
        logger.info("\n📈 ACCIONES (Top Movers > 2.0%):")
        if summary['stocks']:
            for stock in summary['stocks']:
                emoji = "🟢" if stock['change_percent'] > 0 else "🔴"
                logger.info(f"   {emoji} {stock['symbol']}: {stock['change_percent']:+.2f}% (${stock['price']})")
        else:
            logger.info("   (Sin cambios significativos)")

    
    def _publish_results(self, summary: Dict):
        """
        Publica los resultados del análisis en Telegram y Twitter.
        
        Args:
            summary: Diccionario con el resumen de mercados
        """
        # --- TELEGRAM ---
        if self.telegram:
            if summary['stocks']:
                message_lines = ["📊 MERCADOS TRADICIONALES\n", "📈 ACCIONES:"]
                for stock in summary['stocks'][:10]:
                    emoji = "🟢" if stock['change_percent'] > 0 else "🔴"
                    message_lines.append(f"{emoji} {stock['symbol']}: {stock['change_percent']:+.2f}% (${stock['price']})")
                telegram_msg = "\n".join(message_lines)
                try:
                    self.telegram.send_market_message(telegram_msg, image_path=Config.STOCKS_IMAGE_PATH)
                    logger.info("✅ Resultados de Acciones enviados a Telegram (Bot Markets)")
                except Exception as e:
                    logger.error(f"❌ Error enviando Acciones a Telegram: {e}")
            
            if summary['forex']:
                message_lines = ["📊 MERCADOS TRADICIONALES\n", "💱 FOREX (Top 10):"]
                for forex in summary['forex'][:10]:
                    emoji = "🟢" if forex['change_percent'] > 0 else "🔴"
                    message_lines.append(f"{emoji} {forex['pair']}: {forex['change_percent']:+.2f}%")
                telegram_msg = "\n".join(message_lines)
                try:
                    self.telegram.send_market_message(telegram_msg, image_path=Config.FOREX_IMAGE_PATH)
                    logger.info("✅ Resultados de Forex enviados a Telegram (Bot Markets)")
                except Exception as e:
                    logger.error(f"❌ Error enviando Forex a Telegram: {e}")
            
            if summary['commodities']:
                message_lines = ["📊 MERCADOS TRADICIONALES\n", "🛢️ COMMODITIES:"]
                for commodity in summary['commodities']:
                    emoji = "🟢" if commodity['change_percent'] > 0 else "🔴"
                    message_lines.append(f"{emoji} {commodity['name']}: {commodity['change_percent']:+.2f}% (${commodity['price']})")
                telegram_msg = "\n".join(message_lines)
                try:
                    self.telegram.send_market_message(telegram_msg, image_path=Config.COMMODITIES_IMAGE_PATH)
                    logger.info("✅ Resultados de Commodities enviados a Telegram (Bot Markets)")
                except Exception as e:
                    logger.error(f"❌ Error enviando Commodities a Telegram: {e}")
        
        # --- TWITTER (Tweets Separados) ---
        if self.twitter:
            try:
                # Tweet 1: Acciones (solo si hay importantes)
                if summary['stocks']:
                    tweet1 = "📊 MERCADOS TRADICIONALES\n\n📈 ACCIONES:\n"
                    tokens_used = len(tweet1)
                    
                    for stock in summary['stocks']:
                        emoji = "🟢" if stock['change_percent'] > 0 else "🔴"
                        line = f"{emoji} {stock['symbol']}: {stock['change_percent']:+.2f}%\n"
                        if tokens_used + len(line) < 270:
                            tweet1 += line
                            tokens_used += len(line)
                        else:
                            break
                    
                    self.twitter.post_tweet(tweet1.strip(), image_path=Config.STOCKS_IMAGE_PATH, category='markets')
                    logger.info("✅ Tweet de Acciones publicado")
                    logger.info("⏳ Esperando 30 segundos para la siguiente publicación...")
                    time.sleep(getattr(Config, "TWITTER_POST_DELAY", 30))
                
                # Tweet 2: Forex (Top 7 aprox para caber)
                if summary['forex']:
                    tweet2 = "💱 FOREX (Top Movimientos):\n"
                    tokens_used = len(tweet2)
                    
                    for forex in summary['forex']:
                        emoji = "🟢" if forex['change_percent'] > 0 else "🔴"
                        line = f"{emoji} {forex['pair']}: {forex['change_percent']:+.2f}%\n"
                        if tokens_used + len(line) < 270:
                            tweet2 += line
                            tokens_used += len(line)
                        else:
                            break
                            
                    self.twitter.post_tweet(tweet2.strip(), image_path=Config.FOREX_IMAGE_PATH, category='markets')
                    logger.info("✅ Tweet de Forex publicado")
                    logger.info("⏳ Esperando 30 segundos para la siguiente publicación...")
                    time.sleep(getattr(Config, "TWITTER_POST_DELAY", 30))
                
                # Tweet 3: Commodities
                if summary['commodities']:
                    tweet3 = "🛢️ COMMODITIES:\n"
                    for commodity in summary['commodities']:
                        emoji = "🟢" if commodity['change_percent'] > 0 else "🔴"
                        tweet3 += f"{emoji} {commodity['name']}: {commodity['change_percent']:+.2f}%\n"
                    
                    self.twitter.post_tweet(tweet3.strip(), image_path=Config.COMMODITIES_IMAGE_PATH, category='markets')
                    logger.info("✅ Tweet de Commodities publicado")
                
            except Exception as e:
                logger.error(f"❌ Error publicando en Twitter: {e}")



"""
Servicio para análisis de mercados tradicionales (Acciones, Forex, Commodities).
Utiliza Yahoo Finance para obtener datos en tiempo real.
"""
import yfinance as yf
from datetime import datetime, timedelta
from utils.logger import logger
from typing import List, Dict, Optional

class TraditionalMarketsService:
    """Servicio para analizar mercados tradicionales"""
    
    # Símbolos principales a monitorear
    STOCK_SYMBOLS = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM',
        'V', 'WMT', 'JNJ', 'PG', 'MA', 'HD', 'DIS', 'PYPL', 'NFLX', 'ADBE',
        'CRM', 'INTC', 'CSCO', 'PEP', 'KO', 'NKE', 'MCD', 'BA', 'IBM'
    ]
    
    FOREX_PAIRS = [
        'EURUSD=X',  # Euro/USD
        'GBPUSD=X',  # Libra/USD
        'USDJPY=X',  # USD/Yen
        'AUDUSD=X',  # Dólar Australiano/USD
        'USDCAD=X',  # USD/Dólar Canadiense
        'USDCHF=X',  # USD/Franco Suizo
        'NZDUSD=X',  # Dólar Neozelandés/USD
        'EURGBP=X',  # Euro/Libra
        'EURJPY=X',  # Euro/Yen
        'GBPJPY=X',  # Libra/Yen
        'USDMXN=X',  # USD/Peso Mexicano
        'USDBRL=X',  # USD/Real Brasileño
    ]
    
    COMMODITIES = {
        'GC=F': 'Oro',
        'SI=F': 'Plata',
        'CL=F': 'Crudo WTI',
        'BZ=F': 'Brent',
        'RB=F': 'Gasolina',
        'HO=F': 'Petróleo para calefacción'
    }
    
    def __init__(self, telegram=None, twitter=None):
        """
        Inicializa el servicio
        
        Args:
            telegram: Servicio de Telegram (opcional)
            twitter: Servicio de Twitter (opcional)
        """
        self.telegram = telegram
        self.twitter = twitter
        logger.info("✅ Servicio de Mercados Tradicionales inicializado")
    
    def get_top_stocks(self, min_change_percent: float = 2.0, limit: int = 10) -> List[Dict]:
        """
        Obtiene las acciones con mayor cambio porcentual del día.
        
        Args:
            min_change_percent: Cambio mínimo para filtrar (default 2%)
            limit: Número máximo de resultados
            
        Returns:
            Lista de diccionarios con información de acciones
        """
        logger.info(f"📈 Analizando {len(self.STOCK_SYMBOLS)} acciones...")
        
        movers = []
        
        for symbol in self.STOCK_SYMBOLS:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period='2d')
                
                if len(hist) < 2:
                    continue
                
                current_price = hist['Close'].iloc[-1]
                previous_close = hist['Close'].iloc[-2]
                change_percent = ((current_price - previous_close) / previous_close) * 100
                
                if abs(change_percent) >= min_change_percent:
                    info = ticker.info
                    movers.append({
                        'symbol': symbol,
                        'name': info.get('longName', symbol),
                        'price': round(current_price, 2),
                        'change_percent': round(change_percent, 2),
                        'volume': hist['Volume'].iloc[-1],
                        'market_cap': info.get('marketCap', 0)
                    })
                    
            except Exception as e:
                logger.warning(f"⚠️ Error obteniendo datos de {symbol}: {e}")
                continue
        
        # Ordenar por cambio absoluto
        movers.sort(key=lambda x: abs(x['change_percent']), reverse=True)
        
        logger.info(f"✅ Encontradas {len(movers)} acciones con cambio ≥ {min_change_percent}%")
        return movers[:limit]
    
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
        logger.info(f"💱 Analizando {len(self.FOREX_PAIRS)} pares de divisas...")
        all_movers = []
        
        for pair in self.FOREX_PAIRS:
            try:
                ticker = yf.Ticker(pair)
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
        logger.info(f"🛢️ Obteniendo precios de {len(self.COMMODITIES)} commodities...")
        
        prices = []
        
        for symbol, name in self.COMMODITIES.items():
            try:
                ticker = yf.Ticker(symbol)
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
    
    def run_traditional_markets_analysis(self, publish=True):
        """
        Método wrapper para ejecutar análisis completo de mercados tradicionales.
        Llama a get_market_summary() y muestra los resultados.
        
        Args:
            publish: Si True, publica en Telegram y Twitter
        """
        logger.info("\n📊 ANÁLISIS DE MERCADOS TRADICIONALES")
        logger.info("=" * 60)
        
        summary = self.get_market_summary()
        
        # Mostrar resultados en consola
        logger.info("\n📈 ACCIONES (Top Movers > 2.0%):")
        if summary['stocks']:
            for stock in summary['stocks']:
                emoji = "🟢" if stock['change_percent'] > 0 else "🔴"
                logger.info(f"   {emoji} {stock['symbol']}: {stock['change_percent']:+.2f}% (${stock['price']})")
        else:
            logger.info("   (Sin cambios significativos)")
        
        logger.info("\n💱 FOREX (Top 10):")
        if summary['forex']:
            for forex in summary['forex']:
                emoji = "🟢" if forex['change_percent'] > 0 else "🔴"
                logger.info(f"   {emoji} {forex['pair']}: {forex['change_percent']:+.2f}%")
        else:
            logger.info("   (Sin datos)")
        
        logger.info("\n🛢️ COMMODITIES:")
        if summary['commodities']:
            for commodity in summary['commodities']:
                emoji = "🟢" if commodity['change_percent'] > 0 else "🔴"
                logger.info(f"   {emoji} {commodity['name']}: {commodity['change_percent']:+.2f}% (${commodity['price']})")
        
        # Publicar si está habilitado y hay servicios disponibles
        if publish and (self.telegram or self.twitter):
            self._publish_results(summary)
        
        logger.info("\n✅ Análisis de mercados tradicionales completado")
        return summary
    
    def _publish_results(self, summary: Dict):
        """
        Publica los resultados del análisis en Telegram y Twitter.
        
        Args:
            summary: Diccionario con el resumen de mercados
        """
        # --- TELEGRAM (Mensaje consolidado) ---
        if self.telegram:
            message_lines = ["📊 MERCADOS TRADICIONALES\n"]
            
            # Acciones
            if summary['stocks']:
                message_lines.append("📈 ACCIONES:")
                for stock in summary['stocks'][:10]:
                    emoji = "🟢" if stock['change_percent'] > 0 else "🔴"
                    message_lines.append(f"{emoji} {stock['symbol']}: {stock['change_percent']:+.2f}% (${stock['price']})")
                message_lines.append("")
            
            # Forex
            if summary['forex']:
                message_lines.append("💱 FOREX (Top 10):")
                for forex in summary['forex'][:10]:
                    emoji = "🟢" if forex['change_percent'] > 0 else "🔴"
                    message_lines.append(f"{emoji} {forex['pair']}: {forex['change_percent']:+.2f}%")
                message_lines.append("")
            
            # Commodities
            if summary['commodities']:
                message_lines.append("🛢️ COMMODITIES:")
                for commodity in summary['commodities']:
                    emoji = "🟢" if commodity['change_percent'] > 0 else "🔴"
                    message_lines.append(f"{emoji} {commodity['name']}: {commodity['change_percent']:+.2f}% (${commodity['price']})")
            
            telegram_msg = "\n".join(message_lines)
            try:
                self.telegram.send_market_message(telegram_msg)
                logger.info("✅ Resultados enviados a Telegram (Bot Markets)")
            except Exception as e:
                logger.error(f"❌ Error enviando a Telegram: {e}")
        
        # --- TWITTER (Tweets Separados) ---
        if self.twitter:
            import time
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
                    
                    self.twitter.post_tweet(tweet1.strip(), category='markets')
                    logger.info("✅ Tweet de Acciones publicado")
                    logger.info("⏳ Esperando 30 segundos para la siguiente publicación...")
                    time.sleep(30)
                
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
                            
                    self.twitter.post_tweet(tweet2.strip(), category='markets')
                    logger.info("✅ Tweet de Forex publicado")
                    logger.info("⏳ Esperando 30 segundos para la siguiente publicación...")
                    time.sleep(30)
                
                # Tweet 3: Commodities
                if summary['commodities']:
                    tweet3 = "🛢️ COMMODITIES:\n"
                    for commodity in summary['commodities']:
                        emoji = "🟢" if commodity['change_percent'] > 0 else "🔴"
                        tweet3 += f"{emoji} {commodity['name']}: {commodity['change_percent']:+.2f}%\n"
                    
                    self.twitter.post_tweet(tweet3.strip(), category='markets')
                    logger.info("✅ Tweet de Commodities publicado")
                
            except Exception as e:
                logger.error(f"❌ Error publicando en Twitter: {e}")



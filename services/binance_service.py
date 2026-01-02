"""
Servicio para interactuar con la API de Binance.
Obtiene todas las monedas y filtra las que han tenido cambios significativos.
"""
import ccxt
from typing import List, Dict
from config.config import Config
from utils.logger import logger

class BinanceService:
    """Servicio para consultar datos de Binance"""
    
    def __init__(self):
        """Inicializa la conexión con Binance"""
        try:
            self.exchange = ccxt.binance({
                'apiKey': Config.BINANCE_API_KEY,
                'secret': Config.BINANCE_API_SECRET,
                'enableRateLimit': True,
            })
            logger.info("✅ Conexión con Binance establecida")
        except Exception as e:
            logger.error(f"❌ Error al conectar con Binance: {e}")
            raise
    
    def get_all_tickers(self) -> Dict:
        """
        Obtiene información de todas las monedas en Binance.
        
        Returns:
            Diccionario con información de precios de todas las monedas
        """
        try:
            logger.info("📊 Obteniendo todas las monedas de Binance...")
            tickers = self.exchange.fetch_tickers()
            logger.info(f"✅ Se obtuvieron {len(tickers)} monedas de Binance")
            return tickers
        except Exception as e:
            logger.error(f"❌ Error al obtener tickers de Binance: {e}")
            return {}
    
    def filter_significant_changes(self, min_change_percent: float = None) -> List[Dict]:
        """
        Filtra las monedas que han tenido un cambio significativo en 24h.
        
        Args:
            min_change_percent: Porcentaje mínimo de cambio (default: 10%)
            
        Returns:
            Lista de monedas con cambios significativos
        """
        if min_change_percent is None:
            min_change_percent = Config.MIN_CHANGE_PERCENT
        
        try:
            tickers = self.get_all_tickers()
            significant_coins = []
            
            for symbol, data in tickers.items():
                # Verificar que sea un par con USDT y que tenga datos de cambio
                if '/USDT' in symbol and data.get('percentage') is not None:
                    change_percent = abs(data['percentage'])
                    
                    if change_percent >= min_change_percent:
                        coin_data = {
                            'symbol': symbol,
                            'base': symbol.split('/')[0],  # BTC de BTC/USDT
                            'price': data['last'],
                            'change_24h': data['percentage'],
                            'volume_24h': data.get('quoteVolume', 0),
                            'high_24h': data.get('high', 0),
                            'low_24h': data.get('low', 0),
                        }
                        significant_coins.append(coin_data)
            
            # Ordenar por cambio porcentual (mayor a menor en valor absoluto)
            significant_coins.sort(key=lambda x: abs(x['change_24h']), reverse=True)
            
            logger.info(f"🔍 Encontradas {len(significant_coins)} monedas con cambio ≥ {min_change_percent}%")
            
            # Mostrar las top 5
            if significant_coins:
                logger.info("🏆 Top 5 monedas con mayor cambio:")
                for i, coin in enumerate(significant_coins[:5], 1):
                    logger.info(f"   {i}. {coin['symbol']}: {coin['change_24h']:.2f}%")
            
            return significant_coins
            
        except Exception as e:
            logger.error(f"❌ Error al filtrar monedas: {e}")
            return []
    
    def get_coin_info(self, symbol: str) -> Dict:
        """
        Obtiene información detallada de una moneda específica.
        
        Args:
            symbol: Símbolo de la moneda (ej: 'BTC/USDT')
            
        Returns:
            Diccionario con información de la moneda
        """
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return {
                'symbol': symbol,
                'price': ticker['last'],
                'change_24h': ticker.get('percentage', 0),
                'volume_24h': ticker.get('quoteVolume', 0),
                'high_24h': ticker.get('high', 0),
                'low_24h': ticker.get('low', 0),
            }
        except Exception as e:
            logger.error(f"❌ Error al obtener info de {symbol}: {e}")
            return {}
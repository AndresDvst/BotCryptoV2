"""
Servicio para interactuar con la API de Bybit.
Consulta el cambio de precio en las últimas 2 horas para monedas específicas.
"""
import ccxt
from typing import List, Dict
from config.config import Config
from utils.logger import logger
from datetime import datetime, timedelta

class BybitService:
    """Servicio para consultar datos de Bybit"""
    
    def __init__(self):
        """Inicializa la conexión con Bybit"""
        try:
            self.exchange = ccxt.bybit({
                'apiKey': Config.BYBIT_API_KEY,
                'secret': Config.BYBIT_API_SECRET,
                'enableRateLimit': True,
            })
            logger.info("✅ Conexión con Bybit establecida")
        except Exception as e:
            logger.error(f"❌ Error al conectar con Bybit: {e}")
            raise
    
    def get_2hour_change(self, coins: List[Dict]) -> List[Dict]:
        """
        Obtiene el cambio de precio en las últimas 2 horas (promedio de 2 velas de 1h) para las monedas dadas.
        Solo consulta las monedas filtradas por Binance.
        """
        logger.info(f"📊 Consultando cambios de 2 horas (2 velas de 1h) en Bybit para {len(coins)} monedas...")
        enriched_coins = []
        for coin in coins:
            try:
                symbol = coin['symbol']
                # Obtener las últimas 2 velas de 1 hora
                ohlcv = self.exchange.fetch_ohlcv(
                    symbol,
                    timeframe='1h',
                    limit=2
                )
                if len(ohlcv) == 2:
                    price_2h_ago = ohlcv[0][4]  # Cierre de la vela más antigua
                    current_price = ohlcv[1][4]  # Cierre de la vela más reciente
                    change_2h = ((current_price - price_2h_ago) / price_2h_ago) * 100
                    coin['price_2h_ago'] = price_2h_ago
                    coin['current_price_bybit'] = current_price
                    coin['change_2h'] = change_2h
                    coin['bybit_data_available'] = True
                    enriched_coins.append(coin)
                    logger.debug(f"   {symbol}: Cambio 2h = {change_2h:.2f}%")
                else:
                    coin['change_2h'] = 0
                    coin['bybit_data_available'] = False
                    enriched_coins.append(coin)
                    logger.warning(f"   ⚠️ {symbol}: Datos insuficientes en Bybit")
            except Exception as e:
                logger.warning(f"   ⚠️ Error al obtener datos de {coin['symbol']}: {e}")
                coin['change_2h'] = 0
                coin['bybit_data_available'] = False
                enriched_coins.append(coin)
        logger.info(f"✅ Datos de Bybit agregados a {len(enriched_coins)} monedas")
        # Mostrar resumen de cambios de 2h
        valid_data = [c for c in enriched_coins if c.get('bybit_data_available')]
        if valid_data:
            logger.info("📈 Top 10 cambios en 2 horas:")
            sorted_coins = sorted(valid_data, key=lambda x: abs(x['change_2h']), reverse=True)
            for i, coin in enumerate(sorted_coins[:10], 1):
                logger.info(f"   {i}. {coin['symbol']}: {coin['change_2h']:.2f}%")
        return enriched_coins
    
    def get_current_price(self, symbol: str) -> float:
        """
        Obtiene el precio actual de una moneda en Bybit.
        
        Args:
            symbol: Símbolo de la moneda (ej: 'BTC/USDT')
            
        Returns:
            Precio actual
        """
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            logger.error(f"❌ Error al obtener precio de {symbol}: {e}")
            return 0
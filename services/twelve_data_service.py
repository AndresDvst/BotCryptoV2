"""
Servicio para obtener señales de mercados tradicionales usando Twelve Data API.
Límite: 800 requests/día → 3 análisis diarios (266 requests/análisis aprox)
"""
import requests
from typing import List, Dict, Optional
from config.config import Config
from utils.logger import logger
import time

class TwelveDataService:
    """Genera señales técnicas para stocks, forex, commodities usando Twelve Data"""
    
    BASE_URL = "https://api.twelvedata.com"
    MAX_DAILY_REQUESTS = 800
    # Limitar para no consumir todo el quota en un ciclo
    MAX_REQUESTS_PER_ANALYSIS = 250  
    
    def __init__(self):
        self.api_key = getattr(Config, 'TWELVEDATA_API_KEY', '')
        if not self.api_key:
            logger.warning("⚠️ Twelve Data API key no configurada")
        self._request_count = 0
    
    def get_technical_signal(self, symbol: str, interval: str = '1h', 
                            exchange: Optional[str] = None) -> Optional[Dict]:
        """
        Obtiene señal técnica para un símbolo.
        
        Args:
            symbol: AAPL, EURUSD, GOLD, etc
            interval: 1min, 5min, 15min, 1h, 1day
            exchange: NYSE, NASDAQ, FOREX, COMMODITY
        """
        if self._request_count >= self.MAX_REQUESTS_PER_ANALYSIS:
            logger.warning(f"⚠️ Límite de requests alcanzado ({self.MAX_REQUESTS_PER_ANALYSIS})")
            return None
        
        try:
            # Endpoint: /time_series 
            params = {
                'symbol': symbol,
                'interval': interval,
                'apikey': self.api_key,
                'outputsize': 30  # Últimas 30 velas
            }
            
            if exchange:
                params['exchange'] = exchange
            
            response = requests.get(f"{self.BASE_URL}/time_series", params=params, timeout=10)
            self._request_count += 1
            
            if response.status_code != 200:
                logger.warning(f"⚠️ Error API Twelve Data ({symbol}): {response.text}")
                return None
            
            data = response.json()
            if 'values' not in data:
                 logger.warning(f"⚠️ Datos no encontrados para {symbol}")
                 return None
            
            # Obtener RSI
            rsi = self._get_rsi(symbol, interval)
            self._request_count += 1
            
            # Obtener MACD
            macd = self._get_macd(symbol, interval)
            self._request_count += 1
            
            # Generar señal
            signal = self._generate_signal_from_indicators(symbol, data, rsi, macd)
            
            logger.info(f"✅ Señal obtenida para {symbol}: {signal.get('type', 'NEUTRAL')}")
            return signal
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo señal para {symbol}: {e}")
            return None
    
    def _get_rsi(self, symbol: str, interval: str) -> Optional[float]:
        """Obtiene RSI actual"""
        try:
            params = {
                'symbol': symbol,
                'interval': interval,
                'apikey': self.api_key,
                'time_period': 14
            }
            response = requests.get(f"{self.BASE_URL}/rsi", params=params, timeout=10)
            data = response.json()
            
            if 'values' in data and len(data['values']) > 0:
                return float(data['values'][0]['rsi'])
            return None
        except:
            return None
    
    def _get_macd(self, symbol: str, interval: str) -> Optional[Dict]:
        """Obtiene MACD actual"""
        try:
            params = {
                'symbol': symbol,
                'interval': interval,
                'apikey': self.api_key
            }
            response = requests.get(f"{self.BASE_URL}/macd", params=params, timeout=10)
            data = response.json()
            
            if 'values' in data and len(data['values']) > 0:
                return {
                    'macd': float(data['values'][0]['macd']),
                    'signal': float(data['values'][0]['macd_signal']),
                    'histogram': float(data['values'][0]['macd_hist'])
                }
            return None
        except:
            return None
    
    def _generate_signal_from_indicators(self, symbol: str, price_data: dict, 
                                         rsi: Optional[float], macd: Optional[Dict]) -> Dict:
        """Genera señal basada en indicadores"""
        signal_type = "NEUTRAL"
        confidence = 50
        reasons = []
        
        # Análisis RSI
        if rsi:
            if rsi < 30:
                # Posible rebote alcista (sobreventa)
                # OJO: Si es fuerte tendencia bajista, puede seguir bajando.
                # Pero como señal de reversión clásica:
                if signal_type == "NEUTRAL": signal_type = "LONG"
                confidence += 15
                reasons.append(f"RSI sobreventa ({rsi:.1f})")
            elif rsi > 70:
                if signal_type == "NEUTRAL": signal_type = "SHORT"
                confidence += 15
                reasons.append(f"RSI sobrecompra ({rsi:.1f})")
        
        # Análisis MACD
        if macd:
            if macd['histogram'] > 0 and macd['macd'] > macd['signal']:
                if signal_type == "LONG":
                    confidence += 20
                elif signal_type == "NEUTRAL":
                    signal_type = "LONG"
                    confidence += 10
                reasons.append("MACD Cruz alcista")
            elif macd['histogram'] < 0 and macd['macd'] < macd['signal']:
                if signal_type == "SHORT":
                    confidence += 20
                elif signal_type == "NEUTRAL":
                    signal_type = "SHORT"
                    confidence += 10
                reasons.append("MACD Cruz bajista")
        
        # Obtener precio actual
        current_price = 0.0
        if 'values' in price_data and len(price_data['values']) > 0:
            current_price = float(price_data['values'][0]['close'])
        
        return {
            'symbol': symbol,
            'type': signal_type,
            'confidence': min(confidence, 95),
            'current_price': current_price,
            'rsi': rsi,
            'macd': macd,
            'reasons': reasons,
            'timestamp': time.time()
        }
    
    def analyze_top_instruments(self, top_stocks: list, top_forex: list, 
                                top_commodities: list) -> Dict[str, List[Dict]]:
        """
        Analiza los instrumentos más relevantes clasificados por IA.
        
        Args:
            top_stocks: Top 5 acciones más relevantes
            top_forex: Top 5 pares forex más relevantes
            top_commodities: Top 3 commodities más relevantes
        
        Returns:
            Diccionario con señales por categoría
        """
        logger.info("🎯 Analizando instrumentos tradicionales con Twelve Data")
        logger.info(f"📊 Request budget: {self.MAX_REQUESTS_PER_ANALYSIS} requests")
        
        results = {
            'stocks': [],
            'forex': [],
            'commodities': []
        }
        
        # Stocks (5 símbolos × 3 requests = 15)
        logger.info("📈 Analizando acciones...")
        for stock in top_stocks[:5]:
            # Limpiar nombre si viene con descripción (ej: "AAPL (Apple)")
            symbol = stock.split(' ')[0]
            signal = self.get_technical_signal(symbol, interval='1h', exchange='NYSE') # Assumed NYSE/NASDAQ default
            if signal:
                results['stocks'].append(signal)
            time.sleep(1.5)  # Rate limiting (8 requests/min free tier usually allows 8/minute so we need >= 8s delay total per batch.. 
            # Free tier standard 12 data is 8 requests/minute.
            # If we make 3 requests per symbol, 1 symbol takes <1s.
            # We need to be careful. 8 req/min = 1 req / 7.5s.
            # If User has paid plan, it's faster. Assuming free tier safe mode:
            # Let's use 8s delay between symbols if errors occur, but assume reasonable limit.
            # Better to be safe: 
            time.sleep(8) 
        
        # Forex (5 pares)
        logger.info("💱 Analizando divisas...")
        for pair in top_forex[:5]:
            symbol = pair.split(' ')[0]
            signal = self.get_technical_signal(symbol, interval='1h', exchange='FOREX')
            if signal:
                results['forex'].append(signal)
            time.sleep(8)
        
        # Commodities (3 símbolos)
        logger.info("🛢️ Analizando commodities...")
        for commodity in top_commodities[:3]:
            # Mapeo de nombres comunes a símbolos 12Data si es necesario
            # Pero asumiremos que vienen como símbolos (GC, CL, etc o XAU/USD)
            # Twelve data usa symbols como XAU/USD, WTI, etc.
            # Usaremos los del Config map si es posible, o directos.
            symbol = commodity.split(' ')[0]
            signal = self.get_technical_signal(symbol, interval='1h', exchange=None)
            if signal:
                results['commodities'].append(signal)
            time.sleep(8)
        
        logger.info(f"✅ Análisis completado. Requests usados: {self._request_count}")
        
        return results

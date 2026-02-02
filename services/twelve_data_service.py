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
    
    def _convert_symbol_for_twelvedata(self, symbol: str, asset_type: str) -> Optional[str]:
        """
        Convierte símbolos de Yahoo Finance a formato Twelve Data.
        
        Args:
            symbol: Símbolo en formato Yahoo Finance (ej: 'CADJPY=X', 'GC=F')
            asset_type: 'forex' o 'commodity'
            
        Returns:
            Símbolo en formato Twelve Data (ej: 'CAD/JPY', 'GLD') o None si no está disponible
        """
        if asset_type == 'forex':
            # Usar mapeo de config
            forex_map = getattr(Config, 'FOREX_YAHOO_TO_TWELVE', {})
            if symbol in forex_map:
                mapped = forex_map[symbol]
                if mapped is None:
                    logger.debug(f"⚠️ {symbol} no disponible en Twelve Data (plan free)")
                    return None
                return mapped
            # Intentar convertir automáticamente (CADJPY -> CAD/JPY)
            clean = symbol.replace('=X', '')
            if len(clean) == 6:
                return f"{clean[:3]}/{clean[3:]}"
            return symbol
            
        elif asset_type == 'commodity':
            # Usar mapeo de config (ahora usa ETFs)
            commodity_map = getattr(Config, 'COMMODITIES_YAHOO_TO_TWELVE', {})
            if symbol in commodity_map:
                mapped = commodity_map[symbol]
                if mapped is None:
                    logger.debug(f"⚠️ {symbol} no disponible en Twelve Data (plan free)")
                    return None
                return mapped
            return symbol
            
        return symbol
    
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
            symbol = stock.split(' ')[0]
            signal = self.get_technical_signal(symbol, interval='1h', exchange='NYSE')
            if signal:
                results['stocks'].append(signal)
            time.sleep(8)
        
        # Forex (5 pares) - USAR CONVERSIÓN DE SÍMBOLOS
        logger.info("💱 Analizando divisas...")
        for pair in top_forex[:5]:
            raw_symbol = pair.split(' ')[0]
            # Convertir a formato Twelve Data (CADJPY=X -> CAD/JPY)
            symbol = self._convert_symbol_for_twelvedata(raw_symbol, 'forex')
            if symbol is None:
                logger.debug(f"⏭️ Forex: {raw_symbol} omitido (no disponible en plan free)")
                continue
            logger.debug(f"📊 Forex: {raw_symbol} -> {symbol}")
            signal = self.get_technical_signal(symbol, interval='1h', exchange=None)  # Forex no necesita exchange
            if signal:
                signal['original_symbol'] = raw_symbol  # Guardar símbolo original
                results['forex'].append(signal)
            time.sleep(8)
        
        # Commodities (3 símbolos) - USAR CONVERSIÓN DE SÍMBOLOS (ahora usa ETFs)
        logger.info("🛢️ Analizando commodities...")
        for commodity in top_commodities[:3]:
            raw_symbol = commodity.split(' ')[0]
            # Convertir a formato Twelve Data (GC=F -> GLD ETF)
            symbol = self._convert_symbol_for_twelvedata(raw_symbol, 'commodity')
            if symbol is None:
                logger.debug(f"⏭️ Commodity: {raw_symbol} omitido (no disponible en plan free)")
                continue
            logger.debug(f"📊 Commodity: {raw_symbol} -> {symbol}")
            signal = self.get_technical_signal(symbol, interval='1h', exchange='NYSE')  # ETFs cotizan en NYSE
            if signal:
                signal['original_symbol'] = raw_symbol  # Guardar símbolo original
                results['commodities'].append(signal)
            time.sleep(8)
        
        logger.info(f"✅ Análisis completado. Requests usados: {self._request_count}")
        
        return results

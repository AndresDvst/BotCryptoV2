"""
Servicio para analizar el sentimiento del mercado de criptomonedas.
Consulta CoinGecko y CoinMarketCap para obtener indicadores de mercado.
"""
import requests
from typing import Dict
from utils.logger import logger

class MarketSentimentService:
    """Servicio para analizar el sentimiento del mercado"""
    
    def __init__(self):
        """Inicializa el servicio de análisis de sentimiento"""
        self.coingecko_url = "https://api.coingecko.com/api/v3"
        logger.info("✅ Servicio de análisis de sentimiento inicializado")
    
    def get_fear_greed_index(self) -> Dict:
        """
        Obtiene el índice de miedo y codicia (Fear & Greed Index).
        
        Returns:
            Diccionario con información del índice
        """
        try:
            # API alternativa de Fear & Greed Index
            url = "https://api.alternative.me/fng/"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and len(data['data']) > 0:
                    index_data = data['data'][0]
                    return {
                        'value': int(index_data['value']),
                        'classification': index_data['value_classification'],
                        'timestamp': index_data['timestamp']
                    }
            
            logger.warning("⚠️ No se pudo obtener el Fear & Greed Index")
            return {'value': 50, 'classification': 'Neutral', 'timestamp': ''}
            
        except Exception as e:
            logger.error(f"❌ Error al obtener Fear & Greed Index: {e}")
            return {'value': 50, 'classification': 'Neutral', 'timestamp': ''}
    
    def get_global_market_data(self) -> Dict:
        """
        Obtiene datos globales del mercado de criptomonedas.
        
        Returns:
            Diccionario con datos globales del mercado
        """
        try:
            url = f"{self.coingecko_url}/global"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                global_data = data.get('data', {})
                
                return {
                    'total_market_cap_usd': global_data.get('total_market_cap', {}).get('usd', 0),
                    'total_volume_24h_usd': global_data.get('total_volume', {}).get('usd', 0),
                    'btc_dominance': global_data.get('market_cap_percentage', {}).get('btc', 0),
                    'eth_dominance': global_data.get('market_cap_percentage', {}).get('eth', 0),
                    'active_cryptocurrencies': global_data.get('active_cryptocurrencies', 0),
                    'markets': global_data.get('markets', 0),
                }
            
            logger.warning("⚠️ No se pudieron obtener datos globales del mercado")
            return {}
            
        except Exception as e:
            logger.error(f"❌ Error al obtener datos globales: {e}")
            return {}
    
    def get_trending_coins(self) -> list:
        """
        Obtiene las monedas en tendencia según CoinGecko.
        
        Returns:
            Lista de monedas en tendencia
        """
        try:
            url = f"{self.coingecko_url}/search/trending"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                coins = data.get('coins', [])
                
                trending = []
                for coin in coins[:10]:  # Top 10
                    item = coin.get('item', {})
                    trending.append({
                        'name': item.get('name', ''),
                        'symbol': item.get('symbol', ''),
                        'market_cap_rank': item.get('market_cap_rank', 0),
                        'price_btc': item.get('price_btc', 0),
                    })
                
                return trending
            
            logger.warning("⚠️ No se pudieron obtener monedas en tendencia")
            return []
            
        except Exception as e:
            logger.error(f"❌ Error al obtener monedas en tendencia: {e}")
            return []
    
    def analyze_market_sentiment(self) -> Dict:
        """
        Realiza un análisis completo del sentimiento del mercado.
        
        Returns:
            Diccionario con análisis completo del sentimiento
        """
        logger.info("🔍 Analizando sentimiento del mercado...")
        
        # Obtener todos los datos
        fear_greed = self.get_fear_greed_index()
        global_data = self.get_global_market_data()
        trending = self.get_trending_coins()
        
        # Calcular un sentimiento promedio basado en varios factores
        sentiment_score = fear_greed['value']
        
        # Clasificar el sentimiento
        if sentiment_score <= 25:
            overall_sentiment = "Miedo Extremo"
            emoji = "😱"
        elif sentiment_score <= 45:
            overall_sentiment = "Miedo"
            emoji = "😰"
        elif sentiment_score <= 55:
            overall_sentiment = "Neutral"
            emoji = "😐"
        elif sentiment_score <= 75:
            overall_sentiment = "Codicia"
            emoji = "😊"
        else:
            overall_sentiment = "Codicia Extrema"
            emoji = "🤑"
        
        analysis = {
            'fear_greed_index': fear_greed,
            'global_market': global_data,
            'trending_coins': trending,
            'overall_sentiment': overall_sentiment,
            'sentiment_score': sentiment_score,
            'sentiment_emoji': emoji
        }
        
        logger.info(f"✅ Análisis completado - Sentimiento: {overall_sentiment} {emoji} ({sentiment_score}/100)")
        
        return analysis
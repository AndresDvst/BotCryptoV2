"""
Servicio para analizar el sentimiento del mercado de criptomonedas.
Consulta CoinGecko y fuentes externas para obtener indicadores de mercado.
"""
import time
from typing import Any, Dict, List, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from utils.logger import logger


class MarketSentimentService:
    """Servicio para analizar el sentimiento del mercado"""

    _cache: Dict[str, Tuple[Any, float]] = {}

    def __init__(self, timeout_seconds: int = 10):
        """
        Inicializa el servicio de análisis de sentimiento.

        Args:
            timeout_seconds: Timeout global para peticiones HTTP
        """
        self.coingecko_url = "https://api.coingecko.com/api/v3"
        self._timeout = timeout_seconds
        self._session = requests.Session()

        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retries)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

        self._ttl_fng = 600
        self._ttl_global = 600
        self._ttl_trending = 600

        logger.info("✅ Servicio de análisis de sentimiento inicializado")

    def _get_cached(self, key: str) -> Any:
        now = time.time()
        if key in self._cache:
            value, expires_at = self._cache[key]
            if expires_at > now:
                return value
        return None

    def _set_cached(self, key: str, value: Any, ttl_seconds: int) -> None:
        self._cache[key] = (value, time.time() + ttl_seconds)

    def _get_json(self, url: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            resp = self._session.get(url, params=params, timeout=self._timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning(f"⚠️ HTTP error: {e}")
            return {}

    def get_fear_greed_index(self) -> Dict[str, Any]:
        """
        Obtiene el índice de miedo y codicia (Fear & Greed Index).

        Returns:
            Diccionario con información del índice
        """
        cached = self._get_cached("fear_greed_index")
        if cached is not None:
            return cached

        url = "https://api.alternative.me/fng/"
        data = self._get_json(url)

        result = {
            "value": 50,
            "classification": "Neutral",
            "timestamp": "",
        }

        try:
            if "data" in data and data["data"]:
                index_data = data["data"][0]
                result = {
                    "value": int(index_data.get("value", 50)),
                    "classification": index_data.get("value_classification", "Neutral"),
                    "timestamp": index_data.get("timestamp", ""),
                }
        except Exception as e:
            logger.warning(f"⚠️ Parse error Fear & Greed Index: {e}")

        self._set_cached("fear_greed_index", result, self._ttl_fng)
        return result

    def get_global_market_data(self) -> Dict[str, Any]:
        """
        Obtiene datos globales del mercado de criptomonedas.

        Returns:
            Diccionario con datos globales del mercado
        """
        cached = self._get_cached("global_market_data")
        if cached is not None:
            return cached

        url = f"{self.coingecko_url}/global"
        data = self._get_json(url)

        global_data = data.get("data", {})
        result = {
            "total_market_cap_usd": global_data.get("total_market_cap", {}).get("usd", 0),
            "total_volume_24h_usd": global_data.get("total_volume", {}).get("usd", 0),
            "btc_dominance": global_data.get("market_cap_percentage", {}).get("btc", 0),
            "eth_dominance": global_data.get("market_cap_percentage", {}).get("eth", 0),
            "active_cryptocurrencies": global_data.get("active_cryptocurrencies", 0),
            "markets": global_data.get("markets", 0),
        }

        self._set_cached("global_market_data", result, self._ttl_global)
        return result

    def get_trending_coins(self) -> List[Dict[str, Any]]:
        """
        Obtiene las monedas en tendencia según CoinGecko.

        Returns:
            Lista de monedas en tendencia
        """
        cached = self._get_cached("trending_coins")
        if cached is not None:
            return cached

        url = f"{self.coingecko_url}/search/trending"
        data = self._get_json(url)

        coins = data.get("coins", [])
        trending: List[Dict[str, Any]] = []
        try:
            for coin in coins[:10]:
                item = coin.get("item", {})
                trending.append(
                    {
                        "name": item.get("name", ""),
                        "symbol": item.get("symbol", ""),
                        "market_cap_rank": item.get("market_cap_rank", 0),
                        "price_btc": item.get("price_btc", 0),
                    }
                )
        except Exception as e:
            logger.warning(f"⚠️ Parse error trending coins: {e}")

        self._set_cached("trending_coins", trending, self._ttl_trending)
        return trending

    def analyze_market_sentiment(self) -> Dict[str, Any]:
        """
        Realiza un análisis completo del sentimiento del mercado.

        Returns:
            Diccionario con análisis completo del sentimiento
        """
        logger.info("🔍 Analizando sentimiento del mercado...")

        fear_greed = self.get_fear_greed_index()
        global_data = self.get_global_market_data()
        trending = self.get_trending_coins()

        sentiment_score = int(fear_greed.get("value", 50))

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
            "fear_greed_index": fear_greed,
            "global_market": global_data,
            "trending_coins": trending,
            "overall_sentiment": overall_sentiment,
            "sentiment_score": sentiment_score,
            "sentiment_emoji": emoji,
        }

        logger.info(f"✅ Análisis completado - Sentimiento: {overall_sentiment} {emoji} ({sentiment_score}/100)")
        return analysis

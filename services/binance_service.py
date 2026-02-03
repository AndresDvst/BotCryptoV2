"""
Servicio para interactuar con la API de Binance.
Obtiene todas las monedas y filtra las que han tenido cambios significativos.
"""

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import ccxt
from concurrent.futures import ThreadPoolExecutor, as_completed

from config.config import Config
from utils.logger import logger


@dataclass
class BinanceServiceConfig:
    """Configuración del servicio de Binance."""

    CACHE_TTL_TICKERS: int = 30
    CACHE_TTL_COIN_INFO: int = 15
    MAX_CONCURRENT_REQUESTS: int = 10
    MIN_VOLUME_USDT: float = 10000.0
    REQUEST_TIMEOUT: int = 10
    RETRY_ATTEMPTS: int = 3
    RATE_LIMIT_PER_MINUTE: int = 1200
    RATE_LIMIT_THRESHOLD: float = 0.8


class BinanceConnectionError(Exception):
    """Error de conexión con la API de Binance."""


class BinanceAuthError(Exception):
    """Error de autenticación con la API de Binance."""


class BinanceService:
    """Servicio para consultar datos de Binance."""

    def __init__(self, config: Optional[BinanceServiceConfig] = None) -> None:
        """Inicializa la conexión con Binance y el sistema de caché."""
        self.config = config or BinanceServiceConfig()

        self.exchange: Optional[ccxt.binance] = None
        self.authenticated: bool = False
        self.read_only: bool = False

        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._cache_ttl: Dict[str, int] = {}

        self._request_count_total: int = 0
        self._total_response_time: float = 0.0
        self._cache_hits: int = 0
        self._cache_lookups: int = 0

        self._rate_limit_window_start: Optional[float] = None
        self._rate_limit_window_count: int = 0

        self._initialize_exchange()

    def _initialize_exchange(self) -> None:
        """Inicializa el cliente ccxt.binance con validación de credenciales."""
        api_key = getattr(Config, "BINANCE_API_KEY", None)
        api_secret = getattr(Config, "BINANCE_API_SECRET", None)

        params: Dict[str, Any] = {"enableRateLimit": True}

        if api_key and api_secret:
            params["apiKey"] = api_key
            params["secret"] = api_secret
        else:
            self.read_only = True
            logger.info("ℹ️ BinanceService inicializado en modo solo lectura (sin credenciales)")

        try:
            self.exchange = ccxt.binance(params)
            logger.info("✅ Conexión con Binance inicializada")

            if not self.read_only:
                self._validate_credentials()
            else:
                logger.info("ℹ️ Modo solo lectura: solo se usarán endpoints públicos de Binance")
        except (ccxt.AuthenticationError, ccxt.PermissionDenied) as e:
            self.authenticated = False
            self.read_only = True
            logger.error(f"❌ Error de autenticación al conectar con Binance: {e}")
            raise BinanceAuthError("Credenciales de Binance inválidas") from e
        except (ccxt.NetworkError, ccxt.ExchangeError) as e:
            logger.error(f"❌ Error de conexión al inicializar Binance: {e}")
            raise BinanceConnectionError("No se pudo conectar con Binance") from e

    def _validate_credentials(self) -> None:
        """Valida las credenciales realizando una llamada privada de prueba."""
        if not self.exchange:
            raise BinanceConnectionError("Exchange de Binance no inicializado")

        try:
            self._check_rate_limit()
            start = time.time()
            self.exchange.fetch_balance()
            elapsed = time.time() - start
            self._register_request(elapsed)
            self.authenticated = True
            self.read_only = False
            logger.info(f"✅ Credenciales de Binance válidas (respuesta {elapsed:.3f}s)")
        except (ccxt.AuthenticationError, ccxt.PermissionDenied) as e:
            self.authenticated = False
            self.read_only = True
            logger.error(f"❌ Credenciales de Binance inválidas: {e}")
            raise BinanceAuthError("Credenciales de Binance inválidas") from e
        except ccxt.NetworkError as e:
            logger.warning(f"⚠️ Error de red validando credenciales de Binance: {e}")
            raise BinanceConnectionError("Error de red validando credenciales") from e

    def _register_request(self, response_time: float) -> None:
        """Registra métricas internas de la llamada a la API."""
        self._request_count_total += 1
        self._total_response_time += response_time

    def _check_rate_limit(self) -> None:
        """Controla el uso aproximado del rate limit de Binance."""
        now = time.time()
        if self._rate_limit_window_start is None:
            self._rate_limit_window_start = now
            self._rate_limit_window_count = 0

        elapsed = now - self._rate_limit_window_start
        if elapsed >= 60.0:
            self._rate_limit_window_start = now
            self._rate_limit_window_count = 0

        self._rate_limit_window_count += 1

        usage_ratio = self._rate_limit_window_count / float(self.config.RATE_LIMIT_PER_MINUTE)
        if usage_ratio >= self.config.RATE_LIMIT_THRESHOLD:
            logger.warning(
                f"⚠️ Uso de rate limit de Binance alto: {usage_ratio * 100:.1f}% de "
                f"{self.config.RATE_LIMIT_PER_MINUTE} req/min"
            )
            if usage_ratio >= 1.0:
                sleep_time = max(0.0, 60.0 - elapsed)
                if sleep_time > 0:
                    logger.warning(f"⏸ Pausando requests a Binance durante {sleep_time:.1f}s para evitar límite")
                    time.sleep(sleep_time)
                    self._rate_limit_window_start = time.time()
                    self._rate_limit_window_count = 0

    def _execute_request(self, func, *args, **kwargs) -> Any:
        """Ejecuta una llamada a la API de Binance con retry y métricas."""
        if not self.exchange:
            raise BinanceConnectionError("Exchange de Binance no inicializado")

        backoff_seconds = [2, 4, 8]
        attempt = 0

        while True:
            attempt += 1
            self._check_rate_limit()
            start = time.time()

            try:
                logger.debug(f"➡️ Llamada a Binance ({func.__name__}) intento {attempt}")
                result = func(*args, **kwargs)
                elapsed = time.time() - start
                self._register_request(elapsed)
                logger.debug(f"⬅️ Respuesta de Binance ({func.__name__}) en {elapsed:.3f}s")
                return result
            except ccxt.NetworkError as e:
                elapsed = time.time() - start
                self._register_request(elapsed)
                logger.warning(
                    f"⚠️ Error de red en llamada a Binance ({func.__name__}) intento {attempt}: {e}"
                )
                if attempt >= self.config.RETRY_ATTEMPTS:
                    logger.error("❌ Agotados los intentos de retry para llamada a Binance")
                    raise BinanceConnectionError("Error de red persistente al llamar a Binance") from e
                wait_time = backoff_seconds[min(attempt - 1, len(backoff_seconds) - 1)]
                logger.info(f"⏳ Reintentando en {wait_time}s...")
                time.sleep(wait_time)
            except (ccxt.AuthenticationError, ccxt.PermissionDenied) as e:
                elapsed = time.time() - start
                self._register_request(elapsed)
                self.authenticated = False
                self.read_only = True
                logger.error(f"❌ Error de autenticación en llamada a Binance ({func.__name__}): {e}")
                raise BinanceAuthError("Error de autenticación con Binance") from e
            except ccxt.ExchangeError as e:
                elapsed = time.time() - start
                self._register_request(elapsed)
                logger.error(f"❌ Error de intercambio en llamada a Binance ({func.__name__}): {e}")
                raise

    def _is_cache_valid(self, cache_key: str, ttl_seconds: int) -> bool:
        """Verifica si una entrada de caché es válida según su TTL."""
        entry = self._cache.get(cache_key)
        if not entry:
            return False
        _, timestamp = entry
        return (time.time() - timestamp) <= ttl_seconds

    def _get_from_cache(self, cache_key: str, ttl_seconds: int) -> Optional[Any]:
        """Obtiene datos del caché si son válidos."""
        self._cache_lookups += 1
        if self._is_cache_valid(cache_key, ttl_seconds):
            data, _ = self._cache[cache_key]
            self._cache_hits += 1
            return data
        if cache_key in self._cache:
            self._cache.pop(cache_key, None)
            self._cache_ttl.pop(cache_key, None)
        return None

    def _save_to_cache(self, cache_key: str, data: Any, ttl_seconds: int) -> None:
        """Guarda datos en caché con timestamp."""
        self._cache[cache_key] = (data, time.time())
        self._cache_ttl[cache_key] = ttl_seconds
        self._cleanup_cache()

    def _cleanup_cache(self) -> None:
        """Limpia entradas expiradas del caché."""
        now = time.time()
        keys_to_delete: List[str] = []
        
        # Limpiar entradas expiradas
        for key, (_, timestamp) in self._cache.items():
            ttl = self._cache_ttl.get(key)
            if ttl is None:
                keys_to_delete.append(key)  # Eliminar entradas sin TTL
                continue
            if now - timestamp > ttl:
                keys_to_delete.append(key)
        
        # Limpiar también entradas del TTL dict
        for key in list(self._cache_ttl.keys()):
            if key not in self._cache:
                keys_to_delete.append(key)
        
        # Eliminar todas las entradas expiradas
        for key in set(keys_to_delete):  # Usar set para evitar duplicados
            self._cache.pop(key, None)
            self._cache_ttl.pop(key, None)
            logger.debug(f"🗑️ Eliminada entrada expirada del caché: {key}")

    def get_all_tickers(self, force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Obtiene información de todas las monedas en Binance.

        Args:
            force_refresh: Si es True, ignora el caché y fuerza actualización.

        Returns:
            Diccionario con información de precios de todas las monedas.
        """
        cache_key = "tickers_all"
        ttl = self.config.CACHE_TTL_TICKERS

        if not force_refresh:
            cached = self._get_from_cache(cache_key, ttl)
            if isinstance(cached, dict):
                logger.debug("♻️ get_all_tickers usando datos de caché")
                return cached

        try:
            logger.info("📊 Obteniendo todas las monedas de Binance...")
            tickers = self._execute_request(self.exchange.fetch_tickers)
            if not isinstance(tickers, dict):
                logger.warning("⚠️ Respuesta de fetch_tickers no válida")
                return {}
            self._save_to_cache(cache_key, tickers, ttl)
            logger.info(f"✅ Se obtuvieron {len(tickers)} monedas de Binance")
            return tickers
        except BinanceAuthError:
            logger.error("❌ Error de autenticación al obtener tickers de Binance")
            return {}
        except BinanceConnectionError:
            logger.error("❌ Error de conexión al obtener tickers de Binance")
            return {}

    def filter_significant_changes(
        self,
        min_change_percent: Optional[float] = None,
        min_volume_usdt: Optional[float] = None,
        max_results: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Filtra las monedas que han tenido un cambio significativo en 24h.

        Args:
            min_change_percent: Porcentaje mínimo de cambio (default: Config.MIN_CHANGE_PERCENT).
            min_volume_usdt: Volumen mínimo en USDT para considerar la moneda.
            max_results: Número máximo de monedas a retornar.

        Returns:
            Lista de monedas con cambios significativos.
        """
        if min_change_percent is None:
            min_change_percent = float(getattr(Config, "MIN_CHANGE_PERCENT", 10.0))

        if min_volume_usdt is None:
            min_volume_usdt = self.config.MIN_VOLUME_USDT

        tickers = self.get_all_tickers()
        significant_coins: List[Dict[str, Any]] = []

        for symbol, data in tickers.items():
            if not isinstance(symbol, str) or not symbol.endswith("/USDT"):
                continue

            if not data.get("active", True):
                continue

            percentage = data.get("percentage")
            last_price = data.get("last")

            if percentage is None or last_price is None:
                continue

            try:
                change_percent = abs(float(percentage))
                price = float(last_price)
            except (TypeError, ValueError):
                continue

            if price <= 0:
                continue

            volume_quote_raw = data.get("quoteVolume", 0)
            try:
                volume_quote = float(volume_quote_raw)
            except (TypeError, ValueError):
                volume_quote = 0.0

            if volume_quote < float(min_volume_usdt):
                continue

            bid = data.get("bid")
            ask = data.get("ask")
            if bid is not None and ask is not None:
                try:
                    bid_f = float(bid)
                    ask_f = float(ask)
                except (TypeError, ValueError):
                    bid_f = 0.0
                    ask_f = 0.0
                if bid_f > 0 and ask_f > 0:
                    mid = (bid_f + ask_f) / 2.0
                    if mid > 0:
                        spread_percent = (ask_f - bid_f) / mid * 100.0
                        if spread_percent > 1.0:
                            continue

            if change_percent < float(min_change_percent):
                continue

            high_raw = data.get("high", 0)
            low_raw = data.get("low", 0)
            try:
                high_val = float(high_raw or 0)
            except (TypeError, ValueError):
                high_val = 0.0
            try:
                low_val = float(low_raw or 0)
            except (TypeError, ValueError):
                low_val = 0.0

            coin_data: Dict[str, Any] = {
                "symbol": symbol,
                "base": symbol.split("/")[0],
                "price": price,
                "change_24h": float(percentage),
                "volume_24h": volume_quote,
                "high_24h": high_val,
                "low_24h": low_val,
            }
            significant_coins.append(coin_data)

        significant_coins.sort(key=lambda x: abs(x.get("change_24h", 0)), reverse=True)

        if max_results is not None and max_results > 0:
            significant_coins = significant_coins[: max_results]

        logger.info(
            f"🎯 Encontradas {len(significant_coins)} monedas con cambio ≥ {min_change_percent}% "
            f"y volumen ≥ {min_volume_usdt} USDT"
        )

        if significant_coins:
            logger.info("🏅 Top 5 monedas con mayor cambio:")
            for i, coin in enumerate(significant_coins[:5], 1):
                change = coin.get("change_24h", 0)
                trend_emoji = "🔥" if change > 0 else "📉"
                logger.info(f"   {i}. {coin['symbol']}: {trend_emoji} {change:+.2f}%")

        return significant_coins

    def get_coin_info(self, symbol: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Obtiene información detallada de una moneda específica.

        Args:
            symbol: Símbolo de la moneda (por ejemplo, 'BTC/USDT').
            force_refresh: Si es True, ignora el caché y fuerza actualización.

        Returns:
            Diccionario con información de la moneda.
        """
        ttl = self.config.CACHE_TTL_COIN_INFO
        cache_key = f"coin_info:{symbol}"

        if not force_refresh:
            cached = self._get_from_cache(cache_key, ttl)
            if isinstance(cached, dict) and cached:
                logger.debug(f"♻️ get_coin_info usando caché para {symbol}")
                return cached

        tickers_cache = self._get_from_cache("tickers_all", self.config.CACHE_TTL_TICKERS)
        data = None
        if isinstance(tickers_cache, dict):
            data = tickers_cache.get(symbol)

        if data is None:
            try:
                logger.info(f"📊 Obteniendo información individual de {symbol} en Binance...")
                ticker = self._execute_request(self.exchange.fetch_ticker, symbol)
            except BinanceAuthError:
                logger.error(f"❌ Error de autenticación al obtener info de {symbol}")
                return {}
            except BinanceConnectionError:
                logger.error(f"❌ Error de conexión al obtener info de {symbol}")
                return {}
            except ccxt.ExchangeError as e:
                logger.error(f"❌ Error de intercambio al obtener info de {symbol}: {e}")
                return {}

            data = ticker

        last_price = data.get("last")
        if last_price is None:
            logger.warning(f"⚠️ Datos incompletos para {symbol}: falta precio")
            return {}

        try:
            price = float(last_price)
        except (TypeError, ValueError):
            logger.warning(f"⚠️ Precio inválido para {symbol}")
            return {}

        if price <= 0:
            logger.warning(f"⚠️ Precio no positivo para {symbol}")
            return {}

        percentage_raw = data.get("percentage", 0)
        volume_raw = data.get("quoteVolume", 0)
        high_raw = data.get("high", 0)
        low_raw = data.get("low", 0)

        try:
            change_24h = float(percentage_raw or 0)
        except (TypeError, ValueError):
            change_24h = 0.0

        try:
            volume_24h = float(volume_raw or 0)
        except (TypeError, ValueError):
            volume_24h = 0.0

        try:
            high_24h = float(high_raw or 0)
        except (TypeError, ValueError):
            high_24h = 0.0

        try:
            low_24h = float(low_raw or 0)
        except (TypeError, ValueError):
            low_24h = 0.0

        info: Dict[str, Any] = {
            "symbol": symbol,
            "price": price,
            "change_24h": change_24h,
            "volume_24h": volume_24h,
            "high_24h": high_24h,
            "low_24h": low_24h,
        }

        self._save_to_cache(cache_key, info, ttl)

        return info

    def _get_2hour_change_for_coin(self, coin: Dict[str, Any]) -> Dict[str, Any]:
        """
        Obtiene el cambio de precio de las últimas 2 horas para una moneda.

        Args:
            coin: Diccionario con datos de la moneda.

        Returns:
            Diccionario de la moneda enriquecido con change_2h si es posible.
        """
        symbol = coin.get("symbol")
        if not symbol or not isinstance(symbol, str):
            return coin

        try:
            ohlcv = self._execute_request(self.exchange.fetch_ohlcv, symbol, "1h", limit=3)
        except BinanceAuthError as e:
            logger.error(f"❌ Error de autenticación obteniendo OHLCV para {symbol}: {e}")
            return coin
        except BinanceConnectionError as e:
            logger.warning(f"⚠️ Error de conexión obteniendo OHLCV para {symbol}: {e}")
            return coin
        except ccxt.ExchangeError as e:
            logger.warning(f"⚠️ Error de intercambio obteniendo OHLCV para {symbol}: {e}")
            return coin

        if not isinstance(ohlcv, list) or len(ohlcv) < 2:
            logger.warning(f"⚠️ Datos OHLCV insuficientes para {symbol} para calcular cambio 2h")
            return coin

        first = ohlcv[0]
        last = ohlcv[-1]

        if len(first) < 5 or len(last) < 5:
            logger.warning(f"⚠️ Datos OHLCV incompletos para {symbol}")
            return coin

        ts_first = first[0]
        ts_last = last[0]

        try:
            diff_seconds = (ts_last - ts_first) / 1000.0
        except TypeError:
            logger.warning(f"⚠️ Timestamps inválidos en OHLCV para {symbol}")
            return coin

        if diff_seconds < 5400:
            logger.warning(
                f"⚠️ Ventana temporal insuficiente para cambio 2h en {symbol} ({diff_seconds / 3600:.2f}h)"
            )
            return coin

        price_start = first[4]
        price_end = last[4]

        try:
            price_start_f = float(price_start)
            price_end_f = float(price_end)
        except (TypeError, ValueError):
            logger.warning(f"⚠️ Precios inválidos en OHLCV para {symbol}")
            return coin

        if price_start_f <= 0 or price_end_f <= 0:
            logger.warning(f"⚠️ Precios no positivos en OHLCV para {symbol}")
            return coin

        change_2h = (price_end_f - price_start_f) / price_start_f * 100.0

        enriched_coin = coin.copy()
        enriched_coin["change_2h"] = change_2h
        return enriched_coin

    def get_2hour_change(self, coins: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Calcula el cambio de precio de las últimas 2 horas para las monedas dadas.
        Usa procesamiento concurrente con límite de requests simultáneos.

        Args:
            coins: Lista de monedas con sus datos.

        Returns:
            Lista de monedas enriquecida con datos de cambio de 2h.
        """
        logger.info(f"🔍 Consultando cambios de 2h en Binance para {len(coins)} monedas...")

        if not coins:
            return []

        enriched_coins: List[Dict[str, Any]] = []

        with ThreadPoolExecutor(max_workers=self.config.MAX_CONCURRENT_REQUESTS) as executor:
            future_to_coin = {executor.submit(self._get_2hour_change_for_coin, coin): coin for coin in coins}

            for future in as_completed(future_to_coin):
                coin = future_to_coin[future]
                try:
                    result = future.result(timeout=self.config.REQUEST_TIMEOUT)
                    enriched_coins.append(result)
                except TimeoutError:
                    logger.warning(f"⚠️ Timeout obteniendo cambio 2h para {coin.get('symbol', 'N/A')}")
                    enriched_coins.append(coin)
                except Exception as e:
                    logger.debug(f"⚠️ No se pudo obtener cambio de 2h para {coin.get('symbol', 'N/A')}: {e}")
                    enriched_coins.append(coin)

        logger.info(f"   ✅ Datos de 2h enriquecidos para {len(enriched_coins)} monedas")
        return enriched_coins

    def get_stats(self) -> Dict[str, float]:
        """
        Retorna métricas básicas de uso del servicio.

        Returns:
            Diccionario con métricas de rendimiento y uso de caché.
        """
        avg_response_time = (
            self._total_response_time / self._request_count_total if self._request_count_total else 0.0
        )
        cache_hit_rate = (self._cache_hits / self._cache_lookups * 100.0) if self._cache_lookups else 0.0

        return {
            "request_count": float(self._request_count_total),
            "avg_response_time": avg_response_time,
            "cache_hit_rate": cache_hit_rate,
        }

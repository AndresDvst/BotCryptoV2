"""
Servicio de Análisis Técnico Avanzado.
Calcula indicadores técnicos, position sizing, stop loss y take profit dinámicos.
"""
import os
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
try:
    import talib.abstract as ta
except Exception:
    ta = None
from utils.security import validate_dataframe

from utils.logger import logger
from config.config import Config

if TYPE_CHECKING:
    from services.binance_service import BinanceService


@dataclass
class TechnicalAnalysisConfig:
    """Configuración ajustable para el análisis técnico."""
    RSI_OVERSOLD: int = 30
    RSI_OVERBOUGHT: int = 70
    RSI_NEUTRAL_LOWER: int = 45
    RSI_NEUTRAL_UPPER: int = 55
    MIN_CONFIDENCE: float = 40.0  # Umbral de confianza mínimo (40%)
    MIN_CONFLUENCE_INDICATORS: int = 2
    MIN_VOLUME_MULTIPLIER: float = 1.2
    MIN_VOLUME_RATIO: float = 1.2  # Alias para compatibilidad
    
    # Parámetros para señales de baja confianza
    ALLOW_LOW_CONFIDENCE: bool = True
    MIN_SIGNALS_TARGET: int = 5
    RELAXED_MIN_CONFIDENCE: float = 25.0  # Para reintento con filtros relajados
    ATR_MULTIPLIER_SL: float = 2.0
    ATR_MULTIPLIER_TP: float = 3.0
    ATR_MULTIPLIER_SL_LOW: float = 1.8
    ATR_MULTIPLIER_TP_LOW: float = 3.2
    ATR_MULTIPLIER_SL_HIGH: float = 2.7
    ATR_MULTIPLIER_TP_HIGH: float = 4.5
    VOLATILITY_LOW_THRESHOLD: float = 2.0
    VOLATILITY_HIGH_THRESHOLD: float = 5.0
    BB_MIDDLE_PROXIMITY_PERCENT: float = 2.0
    MAX_SPREAD_PERCENT: float = 0.5
    MAX_PORTFOLIO_EXPOSURE_PERCENT: float = 50.0
    MAX_POSITIONS: int = 5
    INDICATOR_WEIGHT_RSI: float = 2.0
    INDICATOR_WEIGHT_MACD: float = 2.0
    INDICATOR_WEIGHT_EMA_TREND: float = 2.0
    INDICATOR_WEIGHT_EMA_CROSS: float = 3.0
    INDICATOR_WEIGHT_BB: float = 1.5
    INDICATOR_WEIGHT_STOCH: float = 1.5
    
    # Validación con Backtest
    ENABLE_BACKTEST_VALIDATION: bool = True
    BACKTEST_MIN_WIN_RATE: float = 40.0  # Win rate mínimo para validar señal
    BACKTEST_DAYS: int = 14  # Días de histórico para backtest rápido
    BACKTEST_CACHE_TTL: int = 3600  # Cache de resultados por 1 hora



class TechnicalAnalysisService:
    def analyze_significant_coins(self, coins: list, telegram=None, twitter=None):
        """
        Analiza monedas con cambio >=10% (24h o 2h) y evita repetidas. Si no hay nuevas, baja el umbral a 5%.
        Devuelve solo monedas que cumplen el criterio y no han sido reportadas recientemente.
        """
        results = []
        # Primer filtro: cambio >=10%
        filtered = [c for c in coins if (abs(c.get('change_24h', 0)) >= 10 or abs(c.get('change_2h', 0)) >= 10)]
        nuevos = []
        logger.info(f"🔍 Analizando monedas con cambio >= 10% (24h o 2h). Total: {len(filtered)}")
        for coin in filtered:
            symbol = coin.get('symbol')
            if not symbol:
                continue
            # Evitar repetidas
            if not self._is_signal_published(symbol, 'alerta'):
                try:
                    ohlcv = self.binance.exchange.fetch_ohlcv(symbol, timeframe='1h', limit=200)
                    df = pd.DataFrame(ohlcv, columns=['timestamp','open','high','low','close','volume'])
                    df = self.calculate_indicators(df)
                    df = self.evaluate_signals(df)
                    res = {
                        "symbol": symbol,
                        "buy": bool(df['buy_signal'].iloc[-1]) if not df.empty else False,
                        "sell": bool(df['sell_signal'].iloc[-1]) if not df.empty else False,
                        "rsi": float(df['rsi'].iloc[-1]) if 'rsi' in df.columns and not df.empty else None,
                        "change_24h": coin.get('change_24h'),
                        "change_2h": coin.get('change_2h'),
                    }
                    results.append(res)
                    self._mark_signal_published(symbol, 'alerta')
                    nuevos.append(symbol)
                except Exception as e:
                    logger.warning(f"⚠️ Error analizando {symbol}: {e}")
        # Si no hay nuevas monedas, relajar criterio a 5%
        if not results:
            logger.info("⚠️ No se encontraron monedas nuevas con cambio >= 10%. Relajando filtro a 5%...")
            filtered_5 = [c for c in coins if (abs(c.get('change_24h', 0)) >= 5 or abs(c.get('change_2h', 0)) >= 5)]
            logger.info(f"🔍 Analizando monedas con cambio >= 5% (24h o 2h). Total: {len(filtered_5)}")
            for coin in filtered_5:
                symbol = coin.get('symbol')
                if not symbol or symbol in nuevos:
                    continue
                if not self._is_signal_published(symbol, 'alerta'):
                    try:
                        ohlcv = self.binance.exchange.fetch_ohlcv(symbol, timeframe='1h', limit=200)
                        df = pd.DataFrame(ohlcv, columns=['timestamp','open','high','low','close','volume'])
                        df = self.calculate_indicators(df)
                        df = self.evaluate_signals(df)
                        res = {
                            "symbol": symbol,
                            "buy": bool(df['buy_signal'].iloc[-1]) if not df.empty else False,
                            "sell": bool(df['sell_signal'].iloc[-1]) if not df.empty else False,
                            "rsi": float(df['rsi'].iloc[-1]) if 'rsi' in df.columns and not df.empty else None,
                            "change_24h": coin.get('change_24h'),
                            "change_2h": coin.get('change_2h'),
                        }
                        results.append(res)
                        self._mark_signal_published(symbol, 'alerta')
                    except Exception as e:
                        logger.warning(f"⚠️ Error analizando {symbol} (umbral 5%): {e}")
        return results

    """Servicio para análisis técnico avanzado y gestión de riesgo"""

    SIGNALS_HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'signals_history.json')

    def __init__(self, config: Optional[TechnicalAnalysisConfig] = None, binance_service: Optional["BinanceService"] = None):
        """Inicializa el servicio, configuración y dependencias."""
        self.config = config or TechnicalAnalysisConfig()
        self._binance = binance_service
        self._htf_trend_cache = {}  # {symbol_timeframe: (trend, timestamp)}
        self._htf_cache_ttl = 3600  # 1 hora
        self._backtest_cache: Dict[str, Tuple[float, float]] = {}  # {symbol: (win_rate, timestamp)}
        self.STATS_HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'stats_history.json')

        logger.info("✅ Servicio de Análisis Técnico inicializado")

        self.images_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'images', 'signals')
        os.makedirs(self.images_dir, exist_ok=True)

        self.published_signals = self._load_signals_history()
        self._reset_stats()
    
    @property
    def binance(self):
        if self._binance is None:
            try:
                from services.binance_service import BinanceService
                self._binance = BinanceService()
                logger.info("✅ BinanceService inicializado (Lazy Loading) en TechnicalAnalysisService")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo inicializar BinanceService (Lazy) en TechnicalAnalysisService: {e}")
                self._binance = None
        return self._binance

    def _reset_stats(self) -> None:
        """Reinicia contadores de estadísticas de señales."""
        self._stats: Dict[str, int] = {
            'signals_evaluated': 0,
            'rejected_volume': 0,
            'rejected_confluence': 0,
            'rejected_rsi_neutral': 0,
            'rejected_spread': 0,
            'rejected_confidence': 0,
            'rejected_bb_middle': 0,
            'rejected_multi_timeframe': 0,
            'rejected_risk_exposure': 0,
            'rejected_risk_positions': 0,
            'rejected_backtest': 0,
            'backtest_validated': 0
        }
    
    def _validate_with_backtest(self, symbol: str) -> Tuple[bool, float, Optional[Dict]]:
        """
        Valida una señal ejecutando un backtest rápido en el símbolo.
        
        Args:
            symbol: Par de trading (ej: 'BTC/USDT')
            
        Returns:
            Tuple (is_valid, win_rate, backtest_metrics)
        """
        import time as time_module
        
        # Verificar cache
        cache_key = symbol
        if cache_key in self._backtest_cache:
            cached_win_rate, cached_time = self._backtest_cache[cache_key]
            if time_module.time() - cached_time < self.config.BACKTEST_CACHE_TTL:
                is_valid = cached_win_rate >= self.config.BACKTEST_MIN_WIN_RATE
                return is_valid, cached_win_rate, None
        
        try:
            # Importar el motor de backtest
            from core.domain import Candle, MarketSeries
            from core.backtest import BacktestEngine, BacktestConfig
            from core.backtest.execution import ExecutionModel, ExecutionConfig
            from core.risk import RiskManager, RiskConfig
            from core.strategies import TrendPullbackStrategy, TrendPullbackConfig
            
            # Obtener datos históricos
            ohlcv = self.binance.exchange.fetch_ohlcv(
                symbol, 
                timeframe='1h', 
                limit=min(500, self.config.BACKTEST_DAYS * 24)
            )
            
            if len(ohlcv) < 100:
                logger.debug(f"⚠️ Datos insuficientes para backtest de {symbol}")
                return True, 50.0, None  # Asumir válido si no hay datos
            
            # Convertir a Candles
            candles = [
                Candle(
                    timestamp=int(row[0]),
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5])
                )
                for row in ohlcv
            ]
            
            # Configurar backtest
            strategy = TrendPullbackStrategy(TrendPullbackConfig())
            risk_manager = RiskManager(RiskConfig(risk_per_trade=0.02, max_drawdown=0.20))
            execution = ExecutionModel(ExecutionConfig(fee_rate=0.001, slippage_pct=0.0005))
            engine = BacktestEngine(
                strategy=strategy,
                risk_manager=risk_manager,
                execution_model=execution,
                config=BacktestConfig(initial_capital=10000.0, allow_short=True)
            )
            
            # Ejecutar backtest
            series = MarketSeries(symbol=symbol, candles=candles)
            result = engine.run(series)
            
            # Calcular métricas
            trades = result.trades
            if not trades:
                # Sin trades = estrategia no aplica, permitir pero con advertencia
                self._backtest_cache[cache_key] = (50.0, time_module.time())
                return True, 50.0, None
            
            winning = len([t for t in trades if t.pnl > 0])
            win_rate = (winning / len(trades)) * 100
            
            # Guardar en cache
            self._backtest_cache[cache_key] = (win_rate, time_module.time())
            
            is_valid = win_rate >= self.config.BACKTEST_MIN_WIN_RATE
            
            metrics = {
                'win_rate': round(win_rate, 1),
                'total_trades': len(trades),
                'winning_trades': winning,
                'total_return': round(result.metrics.total_return * 100, 2) if hasattr(result.metrics, 'total_return') else 0
            }
            
            if is_valid:
                logger.info(f"✅ Backtest {symbol}: Win Rate {win_rate:.1f}% ({winning}/{len(trades)} trades) - VALIDADO")
                self._increment_stat('backtest_validated')
            else:
                logger.info(f"❌ Backtest {symbol}: Win Rate {win_rate:.1f}% < {self.config.BACKTEST_MIN_WIN_RATE}% - RECHAZADO")
                self._increment_stat('rejected_backtest')
            
            return is_valid, win_rate, metrics
            
        except Exception as e:
            logger.warning(f"⚠️ Error en backtest de {symbol}: {e}")
            # En caso de error, permitir la señal pero sin validación
            return True, 50.0, None

    def _increment_stat(self, key: str) -> None:
        """Incrementa un contador estadístico de forma segura."""
        if not hasattr(self, "_stats"):
            self._reset_stats()
        if key not in self._stats:
            self._stats[key] = 0
        self._stats[key] += 1
    
    def _save_stats_to_file(self):
        """Guarda estadísticas del día"""
        try:
            # Cargar histórico
            if os.path.exists(self.STATS_HISTORY_FILE):
                with open(self.STATS_HISTORY_FILE, 'r') as f:
                    historical = json.load(f)
                # Asegurar que tenga la estructura correcta
                if not isinstance(historical, dict):
                    historical = {'daily_stats': []}
                if 'daily_stats' not in historical:
                    historical['daily_stats'] = []
            else:
                historical = {'daily_stats': []}
            
            # Agregar stats de hoy
            today = datetime.now().date().isoformat()
            
            # Buscar entrada de hoy para actualizar en vez de duplicar
            today_entry = next((item for item in historical['daily_stats'] if item['date'] == today), None)
            
            if today_entry:
                # Actualizar contadores sumando nuevos valores
                # En este caso simple, reemplazaremos con el snapshot actual del día si asumimos que _stats acumula el día entero
                # Pero como _reset_stats se llama por ciclo, mejor agregar nueva entrada con timestamp o simplemente append
                # Para simplificar y seguir el prompt: append directo con fecha (puede haber varias entradas por día, o idealmente agrupar)
                # El prompt sugiere append. Seguiré eso.
                historical['daily_stats'].append({
                    'date': today,
                    'timestamp': datetime.now().isoformat(),
                    **self._stats
                })
            else:
                historical['daily_stats'].append({
                    'date': today,
                    'timestamp': datetime.now().isoformat(),
                    **self._stats
                })
            
            # Mantener últimos 30 días (aprox, si hay multiples por día pueden ser más entradas)
            # El prompt dice "Mantener últimos 30 días" refiriendose al array.
            if len(historical['daily_stats']) > 100: # Mas seguro 100 entradas
                historical['daily_stats'] = historical['daily_stats'][-100:]
            
            # Guardar
            with open(self.STATS_HISTORY_FILE, 'w') as f:
                json.dump(historical, f, indent=2)
            
            logger.info("✅ Estadísticas guardadas en histórico")
        except Exception as e:
            logger.warning(f"⚠️ Error guardando stats: {e}")

    def get_stats_summary(self, days: int = 7) -> dict:
        """Retorna resumen de últimos N días"""
        try:
            if not os.path.exists(self.STATS_HISTORY_FILE):
                return {}
            
            with open(self.STATS_HISTORY_FILE, 'r') as f:
                historical = json.load(f)
            
            recent = historical['daily_stats'][-days:]
            if not recent:
                return {}
            
            # Mean of metrics
            summary = {
                'days_analyzed': len(recent),
                'avg_signals_evaluated': sum(d.get('signals_evaluated', 0) for d in recent) / len(recent),
                'total_rejected_volume': sum(d.get('rejected_volume', 0) for d in recent),
            }
            
            return summary
        except Exception as e:
            logger.warning(f"⚠️ Error obteniendo resumen: {e}")
            return {}
    
    def _load_signals_history(self) -> set:
        """Carga el histórico de señales publicadas"""
        import json
        try:
            if os.path.exists(self.SIGNALS_HISTORY_FILE):
                with open(self.SIGNALS_HISTORY_FILE, 'r') as f:
                    data = json.load(f)
                    
                    # Verificar antigüedad (expira en 6 horas)
                    last_updated_str = data.get('last_updated', '')
                    if last_updated_str:
                        last_updated = datetime.fromisoformat(last_updated_str)
                        if datetime.now() - last_updated > timedelta(hours=6):
                            logger.info("🕒 Historial de señales expirado (>6h), iniciando fresco")
                            return set()
                            
                    return set(data.get('published_signals', []))
        except Exception as e:
            logger.warning(f"⚠️ Error cargando histórico de señales: {e}")
        return set()
    
    def _save_signals_history(self):
        """Guarda el histórico de señales publicadas"""
        import json
        try:
            # Mantener solo las últimas 100 señales
            signals_list = list(self.published_signals)[-100:]
            data = {
                'published_signals': signals_list,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.SIGNALS_HISTORY_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"⚠️ Error guardando histórico de señales: {e}")
    
    def _is_signal_published(self, symbol: str, signal_type: str) -> bool:
        """Verifica si una señal ya fue publicada recientemente"""
        key = f"{symbol}_{signal_type}"
        return key in self.published_signals
    
    def _mark_signal_published(self, symbol: str, signal_type: str):
        """Marca una señal como publicada"""
        key = f"{symbol}_{signal_type}"
        self.published_signals.add(key)
        self._save_signals_history()
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula indicadores técnicos y los agrega al DataFrame.
        """
        validate_dataframe(df)

        if ta is None:
            if not getattr(self, "_ta_lib_warning_shown", False):
                logger.warning("⚠️ TA-Lib no está disponible. Usando cálculos internos (fallback) para indicadores.")
                self._ta_lib_warning_shown = True

            close = df["close"].astype(float)
            high = df["high"].astype(float)
            low = df["low"].astype(float)

            def _ema(series: pd.Series, period: int) -> pd.Series:
                return series.ewm(span=period, adjust=False, min_periods=period).mean()

            def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
                delta = series.diff()
                gain = delta.clip(lower=0)
                loss = (-delta).clip(lower=0)
                avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
                avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
                rs = avg_gain / avg_loss.replace(0, np.nan)
                return 100 - (100 / (1 + rs))

            def _adx(high_s: pd.Series, low_s: pd.Series, close_s: pd.Series, period: int = 14) -> pd.Series:
                prev_high = high_s.shift(1)
                prev_low = low_s.shift(1)
                prev_close = close_s.shift(1)

                tr1 = (high_s - low_s).abs()
                tr2 = (high_s - prev_close).abs()
                tr3 = (low_s - prev_close).abs()
                tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

                up_move = high_s - prev_high
                down_move = prev_low - low_s
                plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
                minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
                plus_dm = pd.Series(plus_dm, index=high_s.index)
                minus_dm = pd.Series(minus_dm, index=high_s.index)

                atr = tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
                plus_di = 100 * (plus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean() / atr.replace(0, np.nan))
                minus_di = 100 * (minus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean() / atr.replace(0, np.nan))

                dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
                return dx.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

            df["adx"] = _adx(high, low, close)

            ema12 = _ema(close, 12)
            ema26 = _ema(close, 26)
            macd_line = ema12 - ema26
            signal = _ema(macd_line, 9)
            hist = macd_line - signal
            df["macd"] = macd_line
            df["macdsignal"] = signal
            df["macdhist"] = hist

            df["rsi"] = _rsi(close, 14)
            df["ema10"] = _ema(close, 10)
        else:
            df['adx'] = ta.ADX(df)

            macd = ta.MACD(df)
            df['macd'] = macd['macd']
            df['macdsignal'] = macd['macdsignal']
            df['macdhist'] = macd['macdhist']

            df['rsi'] = ta.RSI(df)
            df['ema10'] = ta.EMA(df, timeperiod=10)

        # Bandas de Bollinger
        bollinger = self.calculate_bollinger_bands(df)
        df['bb_lowerband'] = bollinger['lower']
        df['bb_middleband'] = bollinger['mid']
        df['bb_upperband'] = bollinger['upper']

        return df

    def calculate_bollinger_bands(self, df: pd.DataFrame, window: int = 20, stds: int = 2):
        """
        Calcula las Bandas de Bollinger.
        """
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        rolling_mean = typical_price.rolling(window=window).mean()
        rolling_std = typical_price.rolling(window=window).std()

        return {
            'lower': rolling_mean - (rolling_std * stds),
            'mid': rolling_mean,
            'upper': rolling_mean + (rolling_std * stds),
        }

    def evaluate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Evalúa las condiciones de entrada y salida basadas en indicadores.
        """
        validate_dataframe(df)

        # Señales de compra
        df['buy_signal'] = (
            (df['rsi'] < 30) &
            (df['adx'] > 30) &
            (df['macd'] > df['macdsignal'])
        )

        # Señales de venta
        df['sell_signal'] = (
            (df['rsi'] > 70) &
            (df['adx'] > 30) &
            (df['macd'] < df['macdsignal'])
        )

        return df


    def run_technical_analysis(self, capital: float, risk_percent: float, telegram=None, twitter=None):
        """
        Ejecuta análisis técnico completo para las monedas principales.
        Método wrapper para compatibilidad con main.py.
        """
        logger.info("🎯 Ejecutando Análisis Técnico con Señales...")
        
        # 1. Definir lista de monedas a analizar (Top + LTC)
        # Puedes mover esto a Config si prefieres
        target_coins = [
            'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT', 
            'ADA/USDT', 'DOGE/USDT', 'AVAX/USDT', 'LTC/USDT', 'DOT/USDT',
            'LINK/USDT', 'MATIC/USDT', 'TRX/USDT', 'SHIB/USDT', 'UNI/USDT'
        ]
        
        results = []
        
        for symbol in target_coins:
            try:
                # Obtener datos históricos (4h o 1d para swing trading)
                # FIX: Usar self.binance en lugar de self.binance_service
                if not self.binance:
                    logger.error("❌ BinanceService no disponible")
                    return

                # Nota: get_historical_data podría llamarse fetch_ohlcv_dataframe en otros servicios,
                # verificar si get_historical_data existe en BinanceService. 
                # Asumiremos que si, sino se ajustará.
                # Si falla, podemos usar self.binance.exchange.fetch_ohlcv directamente como en analyze_significant_coins
                
                try:
                    df = self.binance.get_historical_data(symbol, interval='4h', limit=100)
                except AttributeError:
                    # Fallback si get_historical_data no existe
                    ohlcv = self.binance.exchange.fetch_ohlcv(symbol, timeframe='4h', limit=100)
                    df = pd.DataFrame(ohlcv, columns=['timestamp','open','high','low','close','volume'])
                
                if df is None or df.empty:
                    logger.warning(f"⚠️ No hay datos para {symbol}")
                    continue
                
                # Calcular indicadores
                df = self.calculate_indicators(df)
                
                # Evaluar señales
                df = self.evaluate_signals(df)
                
                # Extraer señal del último candle
                last_candle = df.iloc[-1]
                signal = None
                if last_candle.get('buy_signal'):
                    signal = 'BUY'
                elif last_candle.get('sell_signal'):
                    signal = 'SELL'
                
                if signal:
                    # Calcular tamaño de posición
                    entry_price = float(df['close'].iloc[-1])
                    stop_loss = float(df['low'].iloc[-1]) * 0.98  # Ejemplo simple
                    
                    # Validar señal con backtest rápido
                    is_valid, win_rate, _ = self._validate_with_backtest(symbol)
                    
                    if is_valid:
                        results.append({
                            'symbol': symbol,
                            'signal': signal,
                            'price': entry_price,
                            'confidence': win_rate,
                            'stop_loss': stop_loss
                        })
                        
            except Exception as e:
                logger.error(f"❌ Error analizando {symbol}: {e}")
                
        # Publicar resultados
        if results:
            logger.info(f"✅ Se encontraron {len(results)} señales potenciales")
            # Aquí podrías llamar al servicio de Telegram para enviar las señales
            # Por ahora lo dejamos en log
            for res in results:
                logger.info(f"🚀 Señal: {res['symbol']} {res['signal']} (Conf: {res['confidence']}%)")
                
            # Si se pasó el objeto telegram, intentar enviar
            if telegram:
                try:
                    # Verificar si existe el método antes de llamar
                    if hasattr(telegram, 'send_signals_report'):
                        telegram.send_signals_report(results)
                    else:
                        logger.warning("⚠️ El objeto Telegram no tiene método send_signals_report")
                except Exception as e:
                    logger.warning(f"⚠️ Error enviando a Telegram: {e}")
        else:
            logger.info("ℹ️ No se encontraron señales de alta probabilidad en este ciclo.")


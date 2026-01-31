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
from ta.trend import MACD, EMAIndicator, SMAIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange

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
    MIN_CONFIDENCE: float = 40.0
    MIN_CONFLUENCE_INDICATORS: int = 2
    MIN_VOLUME_MULTIPLIER: float = 1.5
    
    # Nuevos parámetros para señales de baja confianza
    ALLOW_LOW_CONFIDENCE: bool = True
    MIN_SIGNALS_TARGET: int = 5
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


class TechnicalAnalysisService:
    """Servicio para análisis técnico avanzado y gestión de riesgo"""
    
    SIGNALS_HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'signals_history.json')
    
    def __init__(self, config: Optional[TechnicalAnalysisConfig] = None, binance_service: Optional["BinanceService"] = None):
        """Inicializa el servicio, configuración y dependencias."""
        self.config = config or TechnicalAnalysisConfig()
        self._binance = binance_service
        self._htf_trend_cache = {}  # {symbol_timeframe: (trend, timestamp)}
        self._htf_cache_ttl = 3600  # 1 hora
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
            'rejected_risk_positions': 0
        }
    
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
        Calcula todos los indicadores técnicos sobre un DataFrame de OHLCV.
        
        Args:
            df: DataFrame con columnas ['open', 'high', 'low', 'close', 'volume']
            
        Returns:
            DataFrame con indicadores agregados
        """
        try:
            # RSI (Relative Strength Index)
            rsi = RSIIndicator(close=df['close'], window=14)
            df['rsi'] = rsi.rsi()
            
            # MACD (Moving Average Convergence Divergence)
            macd = MACD(close=df['close'], window_slow=26, window_fast=12, window_sign=9)
            df['macd'] = macd.macd()
            df['macd_signal'] = macd.macd_signal()
            df['macd_diff'] = macd.macd_diff()
            
            # Bollinger Bands
            bollinger = BollingerBands(close=df['close'], window=20, window_dev=2)
            df['bb_upper'] = bollinger.bollinger_hband()
            df['bb_middle'] = bollinger.bollinger_mavg()
            df['bb_lower'] = bollinger.bollinger_lband()
            df['bb_width'] = bollinger.bollinger_wband()
            
            # ATR (Average True Range) - Para volatilidad
            atr = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=14)
            df['atr'] = atr.average_true_range()
            
            # EMAs (Exponential Moving Averages)
            ema_20 = EMAIndicator(close=df['close'], window=20)
            ema_50 = EMAIndicator(close=df['close'], window=50)
            df['ema_20'] = ema_20.ema_indicator()
            df['ema_50'] = ema_50.ema_indicator()
            
            # SMAs (Simple Moving Averages)
            sma_20 = SMAIndicator(close=df['close'], window=20)
            sma_50 = SMAIndicator(close=df['close'], window=50)
            df['sma_20'] = sma_20.sma_indicator()
            df['sma_50'] = sma_50.sma_indicator()
            
            # Stochastic Oscillator
            stoch = StochasticOscillator(high=df['high'], low=df['low'], close=df['close'], window=14, smooth_window=3)
            df['stoch_k'] = stoch.stoch()
            df['stoch_d'] = stoch.stoch_signal()
            
            logger.info("✅ Indicadores técnicos calculados")
            return df
            
        except Exception as e:
            logger.error(f"❌ Error calculando indicadores: {e}")
            return df
    
    def generate_signal(self, df: pd.DataFrame, symbol: str, spread_percent: Optional[float] = None) -> Optional[Dict]:
        """
        Genera señal de trading basada en indicadores técnicos y filtros avanzados.
        """
        try:
            if df is None or len(df) < 30:
                return None
            
            self._increment_stat('signals_evaluated')
            
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2]
            
            current_price = float(last_row['close'])
            if not np.isfinite(current_price) or current_price <= 0:
                logger.info(f"ℹ️ Señal descartada para {symbol}: precio inválido ({current_price})")
                return None
            
            rsi = float(last_row['rsi'])
            macd = float(last_row['macd'])
            macd_signal = float(last_row['macd_signal'])
            bb_upper = float(last_row['bb_upper'])
            bb_lower = float(last_row['bb_lower'])
            bb_middle = float(last_row['bb_middle'])
            ema_20 = float(last_row['ema_20'])
            ema_50 = float(last_row['ema_50'])
            atr = float(last_row['atr'])
            stoch_k = float(last_row.get('stoch_k', np.nan))
            stoch_d = float(last_row.get('stoch_d', np.nan))
            
            prev_macd = float(prev_row['macd'])
            prev_macd_signal = float(prev_row['macd_signal'])
            prev_ema_20 = float(prev_row['ema_20'])
            prev_ema_50 = float(prev_row['ema_50'])
            prev_stoch_k = float(prev_row.get('stoch_k', np.nan))
            prev_stoch_d = float(prev_row.get('stoch_d', np.nan))
            
            if not np.isfinite(atr) or atr <= 0:
                logger.info(f"ℹ️ Señal descartada para {symbol}: ATR inválido")
                return None
            
            # Filtro RSI neutral
            if self.config.RSI_NEUTRAL_LOWER <= rsi <= self.config.RSI_NEUTRAL_UPPER:
                logger.info(f"ℹ️ Señal rechazada para {symbol}: RSI en zona neutral ({rsi:.2f})")
                self._increment_stat('rejected_rsi_neutral')
                return None
            
            # Filtro de proximidad a la banda media de Bollinger
            if np.isfinite(bb_middle) and bb_middle > 0:
                distance_bb = abs(current_price - bb_middle) / bb_middle * 100
                if distance_bb <= self.config.BB_MIDDLE_PROXIMITY_PERCENT:
                    logger.info(f"ℹ️ Señal rechazada para {symbol}: precio cerca de BB media ({distance_bb:.2f}%)")
                    self._increment_stat('rejected_bb_middle')
                    return None
            
            # Filtro de spread
            if spread_percent is not None and spread_percent > self.config.MAX_SPREAD_PERCENT:
                logger.info(f"ℹ️ Señal rechazada para {symbol}: spread elevado ({spread_percent:.2f}%)")
                self._increment_stat('rejected_spread')
                return None
            
            # Confirmación de volumen
            volume_ratio = 1.0
            volume_series = df['volume'].astype(float)
            if len(volume_series.dropna()) >= 20:
                avg_volume = float(volume_series.tail(20).mean())
                current_volume = float(last_row['volume'])
                if avg_volume > 0 and current_volume > 0:
                    volume_ratio = current_volume / avg_volume
                    if volume_ratio < self.config.MIN_VOLUME_MULTIPLIER:
                        logger.info(
                            f"ℹ️ Señal rechazada para {symbol}: volumen actual {volume_ratio:.2f}x por debajo del mínimo requerido"
                        )
                        self._increment_stat('rejected_volume')
                        return None
            
            score = 0.0
            reasons: List[str] = []
            bullish_count = 0
            bearish_count = 0
            
            # ANÁLISIS RSI
            if rsi <= self.config.RSI_OVERSOLD:
                score += self.config.INDICATOR_WEIGHT_RSI
                bullish_count += 1
                reasons.append("RSI sobreventa")
            elif rsi >= self.config.RSI_OVERBOUGHT:
                score -= self.config.INDICATOR_WEIGHT_RSI
                bearish_count += 1
                reasons.append("RSI sobrecompra")
            
            # ANÁLISIS MACD
            if macd > macd_signal and prev_macd <= prev_macd_signal:
                score += self.config.INDICATOR_WEIGHT_MACD
                bullish_count += 1
                reasons.append("MACD cruce alcista")
            elif macd < macd_signal and prev_macd >= prev_macd_signal:
                score -= self.config.INDICATOR_WEIGHT_MACD
                bearish_count += 1
                reasons.append("MACD cruce bajista")
            
            # ANÁLISIS EMAs
            if ema_20 > ema_50 and prev_ema_20 <= prev_ema_50:
                score += self.config.INDICATOR_WEIGHT_EMA_CROSS
                bullish_count += 1
                reasons.append("Golden Cross (EMA 20 > EMA 50)")
            elif ema_20 < ema_50 and prev_ema_20 >= prev_ema_50:
                score -= self.config.INDICATOR_WEIGHT_EMA_CROSS
                bearish_count += 1
                reasons.append("Death Cross (EMA 20 < EMA 50)")
            
            if ema_20 > ema_50:
                score += self.config.INDICATOR_WEIGHT_EMA_TREND
                bullish_count += 1
                reasons.append("Tendencia alcista (EMA 20 > EMA 50)")
            elif ema_20 < ema_50:
                score -= self.config.INDICATOR_WEIGHT_EMA_TREND
                bearish_count += 1
                reasons.append("Tendencia bajista (EMA 20 < EMA 50)")
            
            # ANÁLISIS BOLLINGER BANDS
            if current_price <= bb_lower:
                score += self.config.INDICATOR_WEIGHT_BB
                bullish_count += 1
                reasons.append("Precio en banda inferior (posible rebote)")
            elif current_price >= bb_upper:
                score -= self.config.INDICATOR_WEIGHT_BB
                bearish_count += 1
                reasons.append("Precio en banda superior (posible corrección)")
            
            # ANÁLISIS STOCHASTIC
            if np.isfinite(stoch_k) and np.isfinite(stoch_d) and np.isfinite(prev_stoch_k) and np.isfinite(prev_stoch_d):
                if stoch_k < 20 and stoch_k > stoch_d and prev_stoch_k <= prev_stoch_d:
                    score += self.config.INDICATOR_WEIGHT_STOCH
                    bullish_count += 1
                    reasons.append("Stochastic rebote alcista en sobreventa")
                elif stoch_k > 80 and stoch_k < stoch_d and prev_stoch_k >= prev_stoch_d:
                    score -= self.config.INDICATOR_WEIGHT_STOCH
                    bearish_count += 1
                    reasons.append("Stochastic giro bajista en sobrecompra")
            
            if score == 0:
                logger.info(f"ℹ️ Señal rechazada para {symbol}: score neutro")
                self._increment_stat('rejected_confluence')
                return None
            
            max_score = (
                self.config.INDICATOR_WEIGHT_RSI
                + self.config.INDICATOR_WEIGHT_MACD
                + self.config.INDICATOR_WEIGHT_EMA_TREND
                + self.config.INDICATOR_WEIGHT_EMA_CROSS
                + self.config.INDICATOR_WEIGHT_BB
                + self.config.INDICATOR_WEIGHT_STOCH
            )
            
            if score > 0 and bullish_count >= self.config.MIN_CONFLUENCE_INDICATORS and bullish_count > bearish_count:
                signal_type = "LONG"
            elif score < 0 and bearish_count >= self.config.MIN_CONFLUENCE_INDICATORS and bearish_count > bullish_count:
                signal_type = "SHORT"
            else:
                logger.info(
                    f"ℹ️ Señal rechazada para {symbol}: falta confluencia (alcistas={bullish_count}, bajistas={bearish_count})"
                )
                self._increment_stat('rejected_confluence')
                return None
            
            confidence = min(100.0, abs(score) / max_score * 100.0)
            if volume_ratio > 1.0 and self.config.MIN_VOLUME_MULTIPLIER > 0:
                factor = min(volume_ratio / self.config.MIN_VOLUME_MULTIPLIER, 2.0)
                confidence = min(100.0, confidence * factor)
            
            if confidence < self.config.MIN_CONFIDENCE:
                logger.info(f"ℹ️ Señal rechazada para {symbol}: confianza insuficiente ({confidence:.2f}%)")
                self._increment_stat('rejected_confidence')
                return None
            
            volatility = (atr / current_price) * 100.0 if current_price > 0 else 0.0
            if volatility >= self.config.VOLATILITY_HIGH_THRESHOLD:
                atr_multiplier_sl = self.config.ATR_MULTIPLIER_SL_HIGH
                atr_multiplier_tp = self.config.ATR_MULTIPLIER_TP_HIGH
            elif volatility <= self.config.VOLATILITY_LOW_THRESHOLD:
                atr_multiplier_sl = self.config.ATR_MULTIPLIER_SL_LOW
                atr_multiplier_tp = self.config.ATR_MULTIPLIER_TP_LOW
            else:
                atr_multiplier_sl = self.config.ATR_MULTIPLIER_SL
                atr_multiplier_tp = self.config.ATR_MULTIPLIER_TP
            
            if signal_type == "LONG":
                stop_loss = current_price - (atr * atr_multiplier_sl)
                take_profit = current_price + (atr * atr_multiplier_tp)
            else:
                stop_loss = current_price + (atr * atr_multiplier_sl)
                take_profit = current_price - (atr * atr_multiplier_tp)
            
            signal = {
                'symbol': symbol,
                'signal_type': signal_type,
                'confidence': round(confidence, 2),
                'entry_price': round(current_price, 8),
                'stop_loss': round(stop_loss, 8),
                'take_profit': round(take_profit, 8),
                'atr': round(atr, 8),
                'rsi': round(rsi, 2),
                'macd': round(macd, 8),
                'score': round(score, 2),
                'reasons': reasons,
                'timestamp': datetime.now()
            }
            
            log_msg = (
                f"{symbol} analizado - Señal {signal_type} "
                f"(Confianza: {signal['confidence']:.1f}%) "
                f"TP: {signal['take_profit']:.4f} - SL: {signal['stop_loss']:.4f}"
            )
            logger.info(log_msg)
            
            return signal
            
        except Exception as e:
            logger.error(f"❌ Error generando señal para {symbol}: {e}")
            return None
    
    def calculate_position_size(
        self,
        capital: float,
        risk_percent: float,
        entry_price: float,
        stop_loss: float
    ) -> Dict:
        """
        Calcula el tamaño de posición basado en gestión de riesgo.
        
        Args:
            capital: Capital disponible en USD
            risk_percent: Porcentaje de capital a arriesgar (ej: 2.0 para 2%)
            entry_price: Precio de entrada
            stop_loss: Precio de stop loss
            
        Returns:
            Diccionario con detalles de position sizing
        """
        try:
            # Calcular riesgo en USD
            risk_usd = capital * (risk_percent / 100)
            
            # Calcular distancia al stop loss
            risk_per_unit = abs(entry_price - stop_loss)
            
            # Calcular cantidad de unidades
            position_size = risk_usd / risk_per_unit if risk_per_unit > 0 else 0
            
            # Calcular valor total de la posición
            position_value = position_size * entry_price
            
            # Calcular porcentaje de exposición
            exposure_percent = (position_value / capital) * 100
            
            result = {
                'capital': capital,
                'risk_percent': risk_percent,
                'risk_usd': round(risk_usd, 2),
                'position_size': round(position_size, 8),
                'position_value': round(position_value, 2),
                'exposure_percent': round(exposure_percent, 2),
                'risk_per_unit': round(risk_per_unit, 8)
            }
            
            logger.info(f"✅ Position size calculado: {position_size:.8f} unidades (${position_value:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error calculando position size: {e}")
            return None
    
    def generate_chart(self, df: pd.DataFrame, signal: Dict, filename: str) -> Optional[str]:
        """
        Genera un gráfico visual con la señal de trading.
        
        Args:
            df: DataFrame con datos OHLCV e indicadores
            signal: Diccionario con la señal generada
            filename: Nombre del archivo a guardar
            
        Returns:
            Ruta del archivo generado o None si hay error
        """
        try:
            # Tomar últimos 100 períodos
            df_plot = df.tail(100).copy()
            
            # Crear figura con subplots
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 10), 
                                                 gridspec_kw={'height_ratios': [3, 1, 1]})
            
            # SUBPLOT 1: Precio + Bollinger Bands + EMAs
            ax1.plot(df_plot.index, df_plot['close'], label='Precio', color='black', linewidth=2)
            ax1.plot(df_plot.index, df_plot['bb_upper'], label='BB Superior', color='red', linestyle='--', alpha=0.5)
            ax1.plot(df_plot.index, df_plot['bb_middle'], label='BB Media', color='blue', linestyle='--', alpha=0.5)
            ax1.plot(df_plot.index, df_plot['bb_lower'], label='BB Inferior', color='green', linestyle='--', alpha=0.5)
            ax1.plot(df_plot.index, df_plot['ema_20'], label='EMA 20', color='orange', alpha=0.7)
            ax1.plot(df_plot.index, df_plot['ema_50'], label='EMA 50', color='purple', alpha=0.7)
            
            # Marcar niveles de entrada, SL y TP
            current_price = signal['entry_price']
            ax1.axhline(y=current_price, color='blue', linestyle='-', linewidth=2, label=f'Entrada: ${current_price:.2f}')
            ax1.axhline(y=signal['stop_loss'], color='red', linestyle='--', linewidth=2, label=f'Stop Loss: ${signal["stop_loss"]:.2f}')
            ax1.axhline(y=signal['take_profit'], color='green', linestyle='--', linewidth=2, label=f'Take Profit: ${signal["take_profit"]:.2f}')
            
            # Título con señal
            signal_emoji = "🟢" if signal['signal_type'] == "LONG" else "🔴" if signal['signal_type'] == "SHORT" else "⚪"
            ax1.set_title(f"{signal_emoji} {signal['symbol']} - Señal: {signal['signal_type']} (Confianza: {signal['confidence']:.1f}%)", 
                         fontsize=16, fontweight='bold')
            ax1.set_ylabel('Precio (USD)', fontsize=12)
            ax1.legend(loc='upper left', fontsize=8)
            ax1.grid(True, alpha=0.3)
            
            # SUBPLOT 2: RSI
            ax2.plot(df_plot.index, df_plot['rsi'], label='RSI', color='purple', linewidth=2)
            ax2.axhline(y=70, color='red', linestyle='--', alpha=0.5, label='Sobrecompra')
            ax2.axhline(y=30, color='green', linestyle='--', alpha=0.5, label='Sobreventa')
            ax2.axhline(y=50, color='gray', linestyle=':', alpha=0.3)
            ax2.set_ylabel('RSI', fontsize=12)
            ax2.set_ylim(0, 100)
            ax2.legend(loc='upper left', fontsize=8)
            ax2.grid(True, alpha=0.3)
            
            # SUBPLOT 3: MACD
            ax3.plot(df_plot.index, df_plot['macd'], label='MACD', color='blue', linewidth=2)
            ax3.plot(df_plot.index, df_plot['macd_signal'], label='Señal', color='red', linewidth=2)
            ax3.bar(df_plot.index, df_plot['macd_diff'], label='Histograma', color='gray', alpha=0.3)
            ax3.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            ax3.set_ylabel('MACD', fontsize=12)
            ax3.set_xlabel('Fecha', fontsize=12)
            ax3.legend(loc='upper left', fontsize=8)
            ax3.grid(True, alpha=0.3)
            
            # Ajustar layout
            plt.tight_layout()
            
            # Guardar
            filepath = os.path.join(self.images_dir, filename)
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close()
            
            logger.info(f"✅ Gráfico generado: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"❌ Error generando gráfico: {e}")
            return None
    
    def _get_higher_timeframe_trend(self, symbol: str, timeframe: str = '4h') -> Optional[str]:
        """
        Obtiene la tendencia del timeframe superior usando EMA 20/50.
        Devuelve 'bull' (alcista), 'bear' (bajista) o None si no hay datos suficientes.
        """
        if not self.binance:
            return None
            
        cache_key = f"{symbol}_{timeframe}"
        now = datetime.now().timestamp()
        
        # Verificar caché
        if cache_key in self._htf_trend_cache:
            trend, timestamp = self._htf_trend_cache[cache_key]
            if now - timestamp < self._htf_cache_ttl:
                return trend
        
        try:
            ohlcv = self.binance.exchange.fetch_ohlcv(symbol, timeframe, limit=60)
            if not ohlcv:
                return None
            
            df_htf = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df_htf['timestamp'] = pd.to_datetime(df_htf['timestamp'], unit='ms')
            df_htf.set_index('timestamp', inplace=True)
            
            ema20 = EMAIndicator(close=df_htf['close'], window=20).ema_indicator()
            ema50 = EMAIndicator(close=df_htf['close'], window=50).ema_indicator()
            
            if ema20.dropna().empty or ema50.dropna().empty:
                return None
            
            last_ema20 = float(ema20.iloc[-1])
            last_ema50 = float(ema50.iloc[-1])
            
            trend = None
            if last_ema20 > last_ema50:
                trend = "bull"
            elif last_ema20 < last_ema50:
                trend = "bear"
            
            # Guardar en caché
            if trend:
                self._htf_trend_cache[cache_key] = (trend, now)
                
            return trend
        except Exception as e:
            logger.info(f"ℹ️ No se pudo obtener tendencia superior para {symbol} ({timeframe}): {e}")
            return None
    
    def run_technical_analysis(self, capital: float = 1000, risk_percent: float = 2):
        """
        Método wrapper para ejecutar análisis técnico completo.
        Analiza las top monedas de Binance y genera señales.
        
        Args:
            capital: Capital disponible en USD
            risk_percent: Porcentaje de riesgo por operación
        """
        logger.info("\n🎯 ANÁLISIS TÉCNICO CON SEÑALES DE TRADING")
        logger.info("=" * 60)
        logger.info(f"💰 Capital: ${capital}")
        logger.info(f"⚠️  Riesgo por operación: {risk_percent}%")
        
        if not self.binance:
            logger.error("❌ BinanceService no disponible en TechnicalAnalysisService")
            return []
        
        self._reset_stats()
        
        # Obtener top 10 monedas por volumen
        logger.info("\n📊 Obteniendo top monedas por volumen...")
        tickers = self.binance.exchange.fetch_tickers()
        usdt_pairs = {k: v for k, v in tickers.items() if k.endswith('/USDT')}
        sorted_pairs = sorted(usdt_pairs.items(), key=lambda x: x[1].get('quoteVolume', 0), reverse=True)[:10]
        
        signals = []
        used_exposure_percent = 0.0
        open_positions = 0
        
        for symbol, ticker in sorted_pairs:
            try:
                # Obtener datos históricos (100 velas de 1h)
                ohlcv = self.binance.exchange.fetch_ohlcv(symbol, '1h', limit=100)
                
                # Convertir a DataFrame
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                
                # Calcular indicadores
                df = self.calculate_indicators(df)
                
                spread_percent = None
                bid = ticker.get('bid')
                ask = ticker.get('ask')
                if bid and ask and bid > 0 and ask > 0:
                    mid = (bid + ask) / 2
                    spread_percent = ((ask - bid) / mid) * 100
                
                signal = self.generate_signal(df, symbol, spread_percent=spread_percent)
                
                if signal:
                    higher_trend = self._get_higher_timeframe_trend(symbol, timeframe='4h')
                    if higher_trend == "bull" and signal['signal_type'] == "SHORT":
                        logger.info(f"ℹ️ Señal SHORT rechazada en {symbol}: tendencia 4h alcista")
                        self._increment_stat('rejected_multi_timeframe')
                        continue
                    if higher_trend == "bear" and signal['signal_type'] == "LONG":
                        logger.info(f"ℹ️ Señal LONG rechazada en {symbol}: tendencia 4h bajista")
                        self._increment_stat('rejected_multi_timeframe')
                        continue
                    
                    position = self.calculate_position_size(
                        capital,
                        risk_percent,
                        signal['entry_price'],
                        signal['stop_loss']
                    )
                    
                    if not position:
                        continue
                    
                    exposure = position.get('exposure_percent', 0)
                    if open_positions + 1 > self.config.MAX_POSITIONS:
                        logger.info(f"ℹ️ Señal rechazada por límite de posiciones ({self.config.MAX_POSITIONS}) en {symbol}")
                        self._increment_stat('rejected_risk_positions')
                        continue
                    if used_exposure_percent + exposure > self.config.MAX_PORTFOLIO_EXPOSURE_PERCENT:
                        logger.info(
                            f"ℹ️ Señal rechazada por exposición total (> {self.config.MAX_PORTFOLIO_EXPOSURE_PERCENT}%) en {symbol}"
                        )
                        self._increment_stat('rejected_risk_exposure')
                        continue
                    
                    used_exposure_percent += exposure
                    open_positions += 1
                    
                    signal['position'] = position
                    signals.append(signal)
                
            except Exception as e:
                # Silenciar errores individuales para mantener salida limpia
                continue
        
        long_count = len([s for s in signals if "LONG" in s['signal_type']])
        short_count = len([s for s in signals if "SHORT" in s['signal_type']])
        logger.info(f"\n✅ Análisis técnico completado:")
        logger.info(f"   🟢 {long_count} señales LONG")
        logger.info(f"   🔴 {short_count} señales SHORT")
        logger.info(
            f"   📊 Stats: evaluadas={self._stats.get('signals_evaluated', 0)}, "
            f"rechazadas_volumen={self._stats.get('rejected_volume', 0)}, "
            f"rechazadas_confluencia={self._stats.get('rejected_confluence', 0)}, "
            f"rechazadas_RSI_neutral={self._stats.get('rejected_rsi_neutral', 0)}, "
            f"rechazadas_spread={self._stats.get('rejected_spread', 0)}, "
            f"rechazadas_confianza={self._stats.get('rejected_confidence', 0)}, "
            f"rechazadas_multitimeframe={self._stats.get('rejected_multi_timeframe', 0)}, "
            f"rechazadas_riesgo_exposición={self._stats.get('rejected_risk_exposure', 0)}, "
            f"rechazadas_riesgo_posiciones={self._stats.get('rejected_risk_positions', 0)}"
        )
        
        return signals
    
    def analyze_significant_coins(
        self,
        significant_coins: List[Dict[str, Any]],
        telegram=None,
        twitter=None,
        capital: float = 1000,
        risk_percent: float = 2
    ):
        """
        Analiza las monedas con cambios significativos y genera top 5 LONG y top 5 SHORT.
        Publica los resultados en Telegram y Twitter.
        """
        logger.info("\n🎯 ANÁLISIS TÉCNICO DE MONEDAS SIGNIFICATIVAS")
        logger.info("=" * 60)
        logger.info(f"💰 Capital: ${capital}")
        logger.info(f"⚠️  Riesgo por operación: {risk_percent}%")
        logger.info(f"📊 Analizando {len(significant_coins)} monedas...")
        
        if not self.binance:
            logger.error("❌ BinanceService no disponible en TechnicalAnalysisService")
            return {'top_longs': [], 'top_shorts': []}
        
        self._reset_stats()
        
        long_signals = []
        short_signals = []
        used_exposure_percent = 0.0
        open_positions = 0
        
        for coin in significant_coins:
            try:
                symbol = coin['symbol']
                # logger.info(f"\n🔍 Analizando {symbol}...") # Comentado para limpiar salida
                
                # Obtener datos históricos
                ohlcv = self.binance.exchange.fetch_ohlcv(symbol, '1h', limit=100)
                
                # Convertir a DataFrame
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                
                df = self.calculate_indicators(df)
                
                ticker = self.binance.exchange.fetch_ticker(symbol)
                spread_percent = None
                bid = ticker.get('bid')
                ask = ticker.get('ask')
                if bid and ask and bid > 0 and ask > 0:
                    mid = (bid + ask) / 2
                    spread_percent = ((ask - bid) / mid) * 100
                
                signal = self.generate_signal(df, symbol, spread_percent=spread_percent)
                
                if signal:
                    higher_trend = self._get_higher_timeframe_trend(symbol, timeframe='4h')
                    if higher_trend == "bull" and signal['signal_type'] == "SHORT":
                        logger.info(f"ℹ️ Señal SHORT rechazada en {symbol}: tendencia 4h alcista")
                        self._increment_stat('rejected_multi_timeframe')
                        continue
                    if higher_trend == "bear" and signal['signal_type'] == "LONG":
                        logger.info(f"ℹ️ Señal LONG rechazada en {symbol}: tendencia 4h bajista")
                        self._increment_stat('rejected_multi_timeframe')
                        continue
                    
                    position = self.calculate_position_size(
                        capital,
                        risk_percent,
                        signal['entry_price'],
                        signal['stop_loss']
                    )
                    
                    if not position:
                        continue
                    
                    exposure = position.get('exposure_percent', 0)
                    if open_positions + 1 > self.config.MAX_POSITIONS:
                        logger.info(f"ℹ️ Señal rechazada por límite de posiciones ({self.config.MAX_POSITIONS}) en {symbol}")
                        self._increment_stat('rejected_risk_positions')
                        continue
                    if used_exposure_percent + exposure > self.config.MAX_PORTFOLIO_EXPOSURE_PERCENT:
                        logger.info(
                            f"ℹ️ Señal rechazada por exposición total (> {self.config.MAX_PORTFOLIO_EXPOSURE_PERCENT}%) en {symbol}"
                        )
                        self._increment_stat('rejected_risk_exposure')
                        continue
                    
                    used_exposure_percent += exposure
                    open_positions += 1
                    
                    signal['position'] = position
                    signal['change_24h'] = coin.get('change_24h', 0)
                    
                    if "LONG" in signal['signal_type']:
                        long_signals.append(signal)
                    elif "SHORT" in signal['signal_type']:
                        short_signals.append(signal)
                
            except Exception as e:
                # logger.warning(f"⚠️ Error analizando {symbol}: {e}")
                continue
        
        # --- LÓGICA DE REINTENTO CON RELAJACIÓN DE FILTROS ---
        if len(long_signals) < self.config.MIN_SIGNALS_TARGET or len(short_signals) < self.config.MIN_SIGNALS_TARGET:
            logger.warning("⚠️ Pocas señales generadas, ejecutando análisis con filtros relajados...")
            
            # Guardar configuración original
            original_min_confidence = self.config.MIN_CONFIDENCE
            original_min_confluence = self.config.MIN_CONFLUENCE_INDICATORS
            
            # Reducir filtros temporalmente
            self.config.MIN_CONFIDENCE = 30.0  # Muy permisivo
            self.config.MIN_CONFLUENCE_INDICATORS = 1  # Muy permisivo
            
            # Identificar monedas ya procesadas con señal
            processed_symbols = {s['symbol'] for s in long_signals + short_signals}
            
            for coin in significant_coins:
                symbol = coin['symbol']
                if symbol in processed_symbols:
                    continue
                    
                try:
                    # Re-analizar (copiado de lógica anterior)
                    ohlcv = self.binance.exchange.fetch_ohlcv(symbol, '1h', limit=100)
                    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)
                    df = self.calculate_indicators(df)
                    
                    ticker = self.binance.exchange.fetch_ticker(symbol)
                    spread_percent = None
                    bid = ticker.get('bid')
                    ask = ticker.get('ask')
                    if bid and ask and bid > 0 and ask > 0:
                        mid = (bid + ask) / 2
                        spread_percent = ((ask - bid) / mid) * 100
                    
                    signal = self.generate_signal(df, symbol, spread_percent=spread_percent)
                    
                    if signal:
                        signal['low_confidence_warning'] = True
                        
                        higher_trend = self._get_higher_timeframe_trend(symbol, timeframe='4h')
                        # En modo relajado, podemos ser menos estrictos con la tendencia superior o simplemente notarla
                        if higher_trend == "bull" and signal['signal_type'] == "SHORT":
                            # self._increment_stat('rejected_multi_timeframe') # No incrementamos stats en reintento o si?
                            # Permitimos pero bajamos confianza
                            signal['confidence'] *= 0.8
                        if higher_trend == "bear" and signal['signal_type'] == "LONG":
                             signal['confidence'] *= 0.8
                        
                        position = self.calculate_position_size(capital, risk_percent, signal['entry_price'], signal['stop_loss'])
                        if not position: continue
                        
                        # Chequeos de riesgo (exposure)
                        exposure = position.get('exposure_percent', 0)
                        if used_exposure_percent + exposure > self.config.MAX_PORTFOLIO_EXPOSURE_PERCENT: continue
                        
                        used_exposure_percent += exposure
                        processed_symbols.add(symbol)
                        
                        signal['position'] = position
                        signal['change_24h'] = coin.get('change_24h', 0)
                        
                        if "LONG" in signal['signal_type']:
                            long_signals.append(signal)
                        elif "SHORT" in signal['signal_type']:
                            short_signals.append(signal)
                            
                except Exception:
                    continue
            
            # Restaurar configuración original
            self.config.MIN_CONFIDENCE = original_min_confidence
            self.config.MIN_CONFLUENCE_INDICATORS = original_min_confluence
        
        # Ordenar por confianza
        long_signals.sort(key=lambda x: x['confidence'], reverse=True)
        short_signals.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Top 5
        top_longs = long_signals[:5]
        top_shorts = short_signals[:5]
        
        logger.info(f"\n✅ Análisis completado:")
        logger.info(f"   🟢 {len(top_longs)} señales LONG encontradas")
        logger.info(f"   🔴 {len(top_shorts)} señales SHORT encontradas")
        logger.info(
            f"   📊 Stats: evaluadas={self._stats.get('signals_evaluated', 0)}, "
            f"rechazadas_volumen={self._stats.get('rejected_volume', 0)}, "
            f"rechazadas_confluencia={self._stats.get('rejected_confluence', 0)}, "
            f"rechazadas_RSI_neutral={self._stats.get('rejected_rsi_neutral', 0)}, "
            f"rechazadas_spread={self._stats.get('rejected_spread', 0)}, "
            f"rechazadas_confianza={self._stats.get('rejected_confidence', 0)}, "
            f"rechazadas_multitimeframe={self._stats.get('rejected_multi_timeframe', 0)}, "
            f"rechazadas_riesgo_exposición={self._stats.get('rejected_risk_exposure', 0)}, "
            f"rechazadas_riesgo_posiciones={self._stats.get('rejected_risk_positions', 0)}"
        )
        
        for s in top_longs:
            logger.info(f"   🚀 LONG {s['symbol']} ({s['confidence']:.1f}%) - TP: {s['take_profit']}")
            
        for s in top_shorts:
            logger.info(f"   🔻 SHORT {s['symbol']} ({s['confidence']:.1f}%) - TP: {s['take_profit']}")
        
        # Publicar resultados
        if (top_longs or top_shorts) and (telegram or twitter):
            self._publish_signals(top_longs, top_shorts, telegram, twitter)
        
        self._save_stats_to_file()
        
        return {
            'top_longs': top_longs,
            'top_shorts': top_shorts
        }
    
    def _publish_signals(self, top_longs: list, top_shorts: list, telegram=None, twitter=None):
        """
        Publica las señales de trading en Telegram y Twitter.
        """
        # Filtrar señales ya publicadas
        new_longs = []
        for signal in top_longs:
            if not self._is_signal_published(signal['symbol'], 'LONG'):
                new_longs.append(signal)
            else:
                logger.info(f"   ⏩ {signal['symbol']} LONG ya publicado, saltando...")
        
        new_shorts = []
        for signal in top_shorts:
            if not self._is_signal_published(signal['symbol'], 'SHORT'):
                new_shorts.append(signal)
            else:
                logger.info(f"   ⏩ {signal['symbol']} SHORT ya publicado, saltando...")
        
        # Si NO hay señales nuevas, crear mensaje alternativo
        if not new_longs and not new_shorts:
            logger.info("📊 No hay señales nuevas. Enviando informe de estado neutro.")
            
            no_signals_msg = """📊 ANÁLISIS TÉCNICO
            
⚠️ No se encontraron señales de alta confianza en este momento.

El mercado presenta condiciones neutras o sin confluencia clara de indicadores de alta probabilidad.

💡 Recomendaciones:
- Esperar mejores oportunidades
- Monitorear cambios en volumen
- Revisar próximo análisis en 1-2 horas

🔔 Te notificaremos cuando aparezcan señales con mayor confianza."""
            
            if telegram:
                try:
                    telegram.send_signal_message(no_signals_msg, image_path=Config.SIGNALS_IMAGE_PATH)
                    logger.info("✅ Mensaje de 'sin señales' enviado a Telegram")
                except Exception as e:
                    logger.error(f"❌ Error enviando mensaje a Telegram: {e}")
            return
        
        logger.info(f"📊 Publicando {len(new_longs)} LONG y {len(new_shorts)} SHORT nuevos")
        
        # Construir mensaje con ADVERTENCIAS para señales de baja confianza
        message_lines = ["🎯 SEÑALES DE TRADING\n"]
        
        if new_longs:
            message_lines.append("🟢 TOP LONG:")
            for i, signal in enumerate(new_longs, 1):
                confidence = signal['confidence']
                
                # Emoji según confianza
                if confidence >= 70:
                    conf_emoji = "🚀"
                elif confidence >= 50:
                    conf_emoji = "✅"
                else:
                    conf_emoji = "⚠️"
                
                message_lines.append(f"{i}. {signal['symbol']} {conf_emoji} Confianza: {confidence:.1f}%")
                message_lines.append(f"   Entrada: ${signal['entry_price']:.8f}")
                message_lines.append(f"   SL: ${signal['stop_loss']:.8f} | TP: ${signal['take_profit']:.8f}")
                
                # ADVERTENCIA para baja confianza
                if confidence < 50:
                    message_lines.append(f"   ⚠️ BAJA CONFIANZA - Alto riesgo")
                
                message_lines.append(f"   Cambio 24h: {signal['change_24h']:+.2f}%")
                message_lines.append("")
        
        if new_shorts:
            message_lines.append("🔴 TOP SHORT:")
            for i, signal in enumerate(new_shorts, 1):
                confidence = signal['confidence']
                
                # Emoji según confianza
                if confidence >= 70:
                    conf_emoji = "🚀"
                elif confidence >= 50:
                    conf_emoji = "✅"
                else:
                    conf_emoji = "⚠️"
                
                message_lines.append(f"{i}. {signal['symbol']} {conf_emoji} Confianza: {confidence:.1f}%")
                message_lines.append(f"   Entrada: ${signal['entry_price']:.8f}")
                message_lines.append(f"   SL: ${signal['stop_loss']:.8f} | TP: ${signal['take_profit']:.8f}")
                
                # ADVERTENCIA para baja confianza
                if confidence < 50:
                    message_lines.append(f"   ⚠️ BAJA CONFIANZA - Alto riesgo")
                
                message_lines.append(f"   Cambio 24h: {signal['change_24h']:+.2f}%")
                message_lines.append("")
        
        # DISCLAIMER al final si hay señales de baja confianza
        has_low_conf = any(s['confidence'] < 50 for s in new_longs + new_shorts)
        if has_low_conf:
            message_lines.append("⚠️ ADVERTENCIA:")
            message_lines.append("Las señales con baja confianza (<50%) tienen mayor riesgo.")
            message_lines.append("Opera bajo tu propia responsabilidad.")
        
        telegram_message = "\n".join(message_lines)
        
        # Publicar en Telegram
        if telegram:
            try:
                telegram.send_signal_message(telegram_message, image_path=Config.SIGNALS_IMAGE_PATH)
                logger.info("✅ Señales enviadas a Telegram (Bot Signals)")
            except Exception as e:
                logger.error(f"❌ Error enviando a Telegram: {e}")
        
        # Marcar señales como publicadas
        for signal in new_longs:
            self._mark_signal_published(signal['symbol'], 'LONG')
        for signal in new_shorts:
            self._mark_signal_published(signal['symbol'], 'SHORT')


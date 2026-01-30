"""
Servicio de Análisis Técnico Avanzado.
Calcula indicadores técnicos, position sizing, stop loss y take profit dinámicos.
"""
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime, timedelta
from ta.trend import MACD, EMAIndicator, SMAIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange
from typing import Dict, List, Optional, Tuple
from utils.logger import logger
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
import os


class TechnicalAnalysisService:
    """Servicio para análisis técnico avanzado y gestión de riesgo"""
    
    # Archivo para guardar histórico de señales publicadas
    SIGNALS_HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'signals_history.json')
    
    def __init__(self):
        """Inicializa el servicio"""
        logger.info("✅ Servicio de Análisis Técnico inicializado")
        
        # Crear directorio para imágenes si no existe
        self.images_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'images', 'signals')
        os.makedirs(self.images_dir, exist_ok=True)
        
        # Cargar histórico de señales
        self.published_signals = self._load_signals_history()
    
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
    
    def generate_signal(self, df: pd.DataFrame, symbol: str) -> Dict:
        """
        Genera señal de trading basada en indicadores técnicos.
        
        Args:
            df: DataFrame con indicadores calculados
            symbol: Símbolo del activo
            
        Returns:
            Diccionario con la señal y detalles
        """
        try:
            # Obtener últimos valores
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2]
            
            current_price = last_row['close']
            rsi = last_row['rsi']
            macd = last_row['macd']
            macd_signal = last_row['macd_signal']
            bb_upper = last_row['bb_upper']
            bb_lower = last_row['bb_lower']
            ema_20 = last_row['ema_20']
            ema_50 = last_row['ema_50']
            atr = last_row['atr']
            
            # Inicializar puntuación
            score = 0
            reasons = []
            
            # ANÁLISIS RSI
            if rsi < 30:
                score += 2
                reasons.append("RSI sobreventa (<30)")
            elif rsi > 70:
                score -= 2
                reasons.append("RSI sobrecompra (>70)")
            elif 40 <= rsi <= 60:
                score += 1
                reasons.append("RSI neutral (zona sana)")
            
            # ANÁLISIS MACD
            if macd > macd_signal and prev_row['macd'] <= prev_row['macd_signal']:
                score += 2
                reasons.append("MACD cruce alcista")
            elif macd < macd_signal and prev_row['macd'] >= prev_row['macd_signal']:
                score -= 2
                reasons.append("MACD cruce bajista")
            
            # ANÁLISIS BOLLINGER BANDS
            if current_price <= bb_lower:
                score += 1
                reasons.append("Precio en banda inferior (posible rebote)")
            elif current_price >= bb_upper:
                score -= 1
                reasons.append("Precio en banda superior (posible corrección)")
            
            # ANÁLISIS EMAs
            if ema_20 > ema_50 and prev_row['ema_20'] <= prev_row['ema_50']:
                score += 2
                reasons.append("Golden Cross (EMA 20 > EMA 50)")
            elif ema_20 < ema_50 and prev_row['ema_20'] >= prev_row['ema_50']:
                score -= 2
                reasons.append("Death Cross (EMA 20 < EMA 50)")
            elif ema_20 > ema_50:
                score += 1
                reasons.append("Tendencia alcista (EMA 20 > EMA 50)")
            else:
                score -= 1
                reasons.append("Tendencia bajista (EMA 20 < EMA 50)")
            
            # Determinar señal
            if score >= 4:
                signal_type = "LONG"
                confidence = min(score / 10 * 100, 100)
            elif score <= -4:
                signal_type = "SHORT"
                confidence = min(abs(score) / 10 * 100, 100)
            else:
                # Señales débiles o especulativas (Usuario quiere ver top entradas incluso con baja confianza)
                if score > 0:
                    signal_type = "LONG"
                    confidence = 40 + (score * 2.5) # 42.5 - 47.5%
                    reasons.append("Señal débil (Tendencia levemente alcista)")
                elif score < 0:
                    signal_type = "SHORT"
                    confidence = 40 + (abs(score) * 2.5) # 42.5 - 47.5%
                    reasons.append("Señal débil (Tendencia levemente bajista)")
                else:
                    signal_type = "NEUTRAL"
                    confidence = 50
                    reasons.append("Sin dirección clara")
            
            # Calcular Stop Loss y Take Profit
            atr_multiplier_sl = 2.0
            atr_multiplier_tp = 3.0
            
            if "LONG" in signal_type:
                stop_loss = current_price - (atr * atr_multiplier_sl)
                take_profit = current_price + (atr * atr_multiplier_tp)
            elif "SHORT" in signal_type:
                stop_loss = current_price + (atr * atr_multiplier_sl)
                take_profit = current_price - (atr * atr_multiplier_tp)
            else: # NEUTRAL
                stop_loss = current_price * 0.95
                take_profit = current_price * 1.05
            
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
                'score': score,
                'reasons': reasons,
                'timestamp': datetime.now()
            }
            
            # Log personalizado solicitado por usuario
            log_msg = f"{symbol} analizado - TP: {signal['take_profit']:.4f} - SL: {signal['stop_loss']:.4f}"
            if confidence <= 50 and signal_type != "NEUTRAL":
                log_msg += f" (⚠️ Baja confianza: {confidence:.1f}%)"
            elif signal_type == "NEUTRAL":
                log_msg += " (NEUTRAL)"
                
            logger.info(log_msg)
            
            return signal
            
        except Exception as e:
            logger.error(f"❌ Error generando señal: {e}")
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
    
    def run_technical_analysis(self, capital: float = 1000, risk_percent: float = 2):
        """
        Método wrapper para ejecutar análisis técnico completo.
        Analiza las top monedas de Binance y genera señales.
        
        Args:
            capital: Capital disponible en USD
            risk_percent: Porcentaje de riesgo por operación
        """
        from services.binance_service import BinanceService
        
        logger.info("\n🎯 ANÁLISIS TÉCNICO CON SEÑALES DE TRADING")
        logger.info("=" * 60)
        logger.info(f"💰 Capital: ${capital}")
        logger.info(f"⚠️  Riesgo por operación: {risk_percent}%")
        
        binance = BinanceService()
        
        # Obtener top 10 monedas por volumen
        logger.info("\n📊 Obteniendo top monedas por volumen...")
        tickers = binance.exchange.fetch_tickers()
        usdt_pairs = {k: v for k, v in tickers.items() if k.endswith('/USDT')}
        sorted_pairs = sorted(usdt_pairs.items(), key=lambda x: x[1].get('quoteVolume', 0), reverse=True)[:10]
        
        signals = []
        
        for symbol, ticker in sorted_pairs:
            try:
                # Obtener datos históricos (100 velas de 1h)
                ohlcv = binance.exchange.fetch_ohlcv(symbol, '1h', limit=100)
                
                # Convertir a DataFrame
                import pandas as pd
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                
                # Calcular indicadores
                df = self.calculate_indicators(df)
                
                # Generar señal (generate_signal ya tiene log limpio)
                signal = self.generate_signal(df, symbol)
                
                if signal and "NEUTRAL" not in signal['signal_type']:
                    # Calcular position size
                    position = self.calculate_position_size(
                        capital,
                        risk_percent,
                        signal['entry_price'],
                        signal['stop_loss']
                    )
                    
                    signal['position'] = position
                    signals.append(signal)
                
            except Exception as e:
                # Silenciar errores individuales para mantener salida limpia
                continue
        
        # Resumen final
        long_count = len([s for s in signals if "LONG" in s['signal_type']])
        short_count = len([s for s in signals if "SHORT" in s['signal_type']])
        logger.info(f"\n✅ Análisis técnico completado:")
        logger.info(f"   🟢 {long_count} señales LONG")
        logger.info(f"   🔴 {short_count} señales SHORT")
        
        return signals
    
    def analyze_significant_coins(self, significant_coins: list, telegram=None, twitter=None, capital: float = 1000, risk_percent: float = 2):
        """
        Analiza las monedas con cambios significativos y genera top 5 LONG y top 5 SHORT.
        Publica los resultados en Telegram y Twitter.
        """
        from services.binance_service import BinanceService
        
        logger.info("\n🎯 ANÁLISIS TÉCNICO DE MONEDAS SIGNIFICATIVAS")
        logger.info("=" * 60)
        logger.info(f"💰 Capital: ${capital}")
        logger.info(f"⚠️  Riesgo por operación: {risk_percent}%")
        logger.info(f"📊 Analizando {len(significant_coins)} monedas...")
        
        binance = BinanceService()
        
        long_signals = []
        short_signals = []
        
        for coin in significant_coins:
            try:
                symbol = coin['symbol']
                # logger.info(f"\n🔍 Analizando {symbol}...") # Comentado para limpiar salida
                
                # Obtener datos históricos
                ohlcv = binance.exchange.fetch_ohlcv(symbol, '1h', limit=100)
                
                # Convertir a DataFrame
                import pandas as pd
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                
                # Calcular indicadores
                df = self.calculate_indicators(df)
                
                # Generar señal
                signal = self.generate_signal(df, symbol)
                
                if signal:
                    # Calcular position size si no es neutral
                    if "NEUTRAL" not in signal['signal_type']:
                        position = self.calculate_position_size(
                            capital,
                            risk_percent,
                            signal['entry_price'],
                            signal['stop_loss']
                        )
                        signal['position'] = position
                    
                    signal['change_24h'] = coin.get('change_24h', 0)
                    
                    # Clasificar aunque sean señales "Weak"
                    if "LONG" in signal['signal_type']:
                        long_signals.append(signal)
                    elif "SHORT" in signal['signal_type']:
                        short_signals.append(signal)
                
            except Exception as e:
                # logger.warning(f"⚠️ Error analizando {symbol}: {e}")
                continue
        
        # Ordenar por confianza
        long_signals.sort(key=lambda x: x['confidence'], reverse=True)
        short_signals.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Top 5
        top_longs = long_signals[:5]
        top_shorts = short_signals[:5]
        
        logger.info(f"\n✅ Análisis completado:")
        logger.info(f"   🟢 {len(top_longs)} señales LONG encontradas")
        logger.info(f"   🔴 {len(top_shorts)} señales SHORT encontradas")
        
        for s in top_longs:
            warn = "⚠️ " if "Weak" in s['signal_type'] or s['confidence'] <= 50 else "🚀"
            logger.info(f"   {warn} LONG {s['symbol']} ({s['confidence']:.1f}%) - TP: {s['take_profit']}")
            
        for s in top_shorts:
            warn = "⚠️ " if "Weak" in s['signal_type'] or s['confidence'] <= 50 else "🔻"
            logger.info(f"   {warn} SHORT {s['symbol']} ({s['confidence']:.1f}%) - TP: {s['take_profit']}")
        
        # Publicar resultados
        if (top_longs or top_shorts) and (telegram or twitter):
            self._publish_signals(top_longs, top_shorts, telegram, twitter)
        
        return {
            'top_longs': top_longs,
            'top_shorts': top_shorts
        }
    
    def _publish_signals(self, top_longs: list, top_shorts: list, telegram=None, twitter=None):
        """
        Publica las señales de trading en Telegram y Twitter.
        Filtra señales ya publicadas para evitar duplicados.
        
        Args:
            top_longs: Lista de señales LONG
            top_shorts: Lista de señales SHORT
            telegram: Servicio de Telegram
            twitter: Servicio de Twitter
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
        
        # Si no hay señales nuevas, salir
        if not new_longs and not new_shorts:
            logger.info("📊 No hay señales nuevas para publicar (todas ya fueron publicadas)")
            return
        
        logger.info(f"📊 Publicando {len(new_longs)} LONG y {len(new_shorts)} SHORT nuevos")
        
        # Construir mensaje para Telegram
        message_lines = ["🎯 SEÑALES DE TRADING\n"]
        
        if new_longs:
            message_lines.append("🟢 TOP LONG (NUEVAS):")
            for i, signal in enumerate(new_longs, 1):
                message_lines.append(f"{i}. {signal['symbol']} - Confianza: {signal['confidence']:.1f}%")
                message_lines.append(f"   Entrada: ${signal['entry_price']:.8f}")
                message_lines.append(f"   SL: ${signal['stop_loss']:.8f} | TP: ${signal['take_profit']:.8f}")
                message_lines.append(f"   Cambio 24h: {signal['change_24h']:+.2f}%")
                message_lines.append("")
        
        if new_shorts:
            message_lines.append("🔴 TOP SHORT (NUEVAS):")
            for i, signal in enumerate(new_shorts, 1):
                message_lines.append(f"{i}. {signal['symbol']} - Confianza: {signal['confidence']:.1f}%")
                message_lines.append(f"   Entrada: ${signal['entry_price']:.8f}")
                message_lines.append(f"   SL: ${signal['stop_loss']:.8f} | TP: ${signal['take_profit']:.8f}")
                message_lines.append(f"   Cambio 24h: {signal['change_24h']:+.2f}%")
                message_lines.append("")
        
        telegram_message = "\n".join(message_lines)
        
        # Publicar en Telegram
        if telegram:
            try:
                telegram.send_signal_message(telegram_message)
                logger.info("✅ Señales enviadas a Telegram (Bot Signals)")
            except Exception as e:
                logger.error(f"❌ Error enviando a Telegram: {e}")
        
        # Marcar señales como publicadas
        for signal in new_longs:
            self._mark_signal_published(signal['symbol'], 'LONG')
        for signal in new_shorts:
            self._mark_signal_published(signal['symbol'], 'SHORT')


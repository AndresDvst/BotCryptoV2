"""
Servicio para análisis de mercados tradicionales (Acciones, Forex, Commodities, Bonos).
Optimizado para alto rendimiento y bajo rate limit usando batch requests y caché.
Incluye detección de fines de semana y horarios de mercados.
"""
import time
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Set
from concurrent.futures import ThreadPoolExecutor, as_completed

import yfinance as yf

from utils.logger import logger
from config.config import Config
from services.twelve_data_service import TwelveDataService
from services.ai_analyzer_service import AIAnalyzerService


class TraditionalMarketsService:
    """Servicio para analizar mercados tradicionales"""
    
    # Caché en memoria
    _stocks_cache: Dict[str, Tuple[List[Dict], float]] = {}
    
    def __init__(self, telegram=None, twitter=None, ai_analyzer: AIAnalyzerService = None):
        """
        Inicializa el servicio
        
        Args:
            telegram: Servicio de Telegram (opcional)
            twitter: Servicio de Twitter (opcional)
            ai_analyzer: Servicio de IA (opcional)
        """
        self.telegram = telegram
        self.twitter = twitter
        self.ai_analyzer = ai_analyzer
        self.twelve_data = TwelveDataService()
        
        # Historial de señales para evitar duplicados
        self.SIGNALS_HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'traditional_signals_history.json')
        self._published_signals: Set[str] = self._load_signals_history()
        
        logger.info("✅ Servicio de Mercados Tradicionales inicializado")
    
    def _load_signals_history(self) -> Set[str]:
        """Carga historial de señales publicadas (últimas 24h)"""
        try:
            if os.path.exists(self.SIGNALS_HISTORY_FILE):
                with open(self.SIGNALS_HISTORY_FILE, 'r') as f:
                    data = json.load(f)
                # Filtrar solo señales de las últimas 24 horas
                cutoff = datetime.now().timestamp() - 86400  # 24h
                return {s['key'] for s in data.get('signals', []) if s.get('timestamp', 0) > cutoff}
        except Exception as e:
            logger.warning(f"⚠️ Error cargando historial de señales tradicionales: {e}")
        return set()
    
    def _save_signal_to_history(self, symbol: str, signal_type: str):
        """Guarda señal en historial para evitar duplicados"""
        try:
            key = f"{symbol}_{signal_type}"
            self._published_signals.add(key)
            
            # Cargar existentes
            data = {'signals': []}
            if os.path.exists(self.SIGNALS_HISTORY_FILE):
                with open(self.SIGNALS_HISTORY_FILE, 'r') as f:
                    data = json.load(f)
            
            # Agregar nueva
            data['signals'].append({
                'key': key,
                'symbol': symbol,
                'type': signal_type,
                'timestamp': datetime.now().timestamp()
            })
            
            # Limpiar señales > 24h
            cutoff = datetime.now().timestamp() - 86400
            data['signals'] = [s for s in data['signals'] if s.get('timestamp', 0) > cutoff]
            
            with open(self.SIGNALS_HISTORY_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"⚠️ Error guardando señal en historial: {e}")
    
    def _is_signal_published(self, symbol: str, signal_type: str) -> bool:
        """Verifica si una señal ya fue publicada en las últimas 24h"""
        return f"{symbol}_{signal_type}" in self._published_signals
    
    def is_weekend(self) -> bool:
        """Verifica si es sábado o domingo (mercados tradicionales cerrados)"""
        day = datetime.now().weekday()
        return day >= 5  # 5=Sábado, 6=Domingo
    
    def get_market_status(self) -> Dict[str, Dict]:
        """
        Obtiene el estado actual de cada mercado (abierto/cerrado).
        
        Returns:
            Dict con estado de cada mercado
        """
        from datetime import timezone
        now_utc = datetime.now(timezone.utc)
        current_weekday = now_utc.weekday()
        
        market_hours = getattr(Config, 'MARKET_HOURS', {})
        status = {}
        
        for market_id, info in market_hours.items():
            is_weekend_closed = info.get('weekend_closed', True)
            utc_offset = info.get('utc_offset', 0)
            
            # Hora local del mercado
            local_hour = (now_utc.hour + utc_offset) % 24
            local_time = f"{local_hour:02d}:{now_utc.minute:02d}"
            
            open_time = info.get('open', '00:00')
            close_time = info.get('close', '23:59')
            
            # Determinar si está abierto
            is_open = False
            if is_weekend_closed and current_weekday >= 5:
                is_open = False
            else:
                # Comparar horas
                if open_time <= local_time <= close_time:
                    is_open = True
            
            status[market_id] = {
                'name': info.get('name', market_id),
                'is_open': is_open,
                'local_time': local_time,
                'open_time': open_time,
                'close_time': close_time,
                'timezone': info.get('timezone', 'UTC'),
                'note': info.get('note', '')
            }
        
        return status
    
    def get_open_markets_info(self) -> str:
        """Genera un mensaje con los mercados que están abiertos"""
        status = self.get_market_status()
        open_markets = [m for m, s in status.items() if s['is_open']]
        
        if not open_markets:
            return "🔴 Todos los mercados tradicionales están cerrados"
        
        lines = ["🟢 MERCADOS ABIERTOS:"]
        for market_id in open_markets:
            info = status[market_id]
            lines.append(f"   • {info['name']} ({info['open_time']}-{info['close_time']} {info['timezone']})")
        
        return "\n".join(lines)
    
    def get_bond_prices(self, min_change_percent: float = 0.0) -> List[Dict]:
        """
        Obtiene precios actuales de bonos mundiales.
        
        Args:
            min_change_percent: Cambio porcentual mínimo para filtrar
            
        Returns:
            Lista con precios actuales de bonos
        """
        bonds = getattr(Config, "BONDS", {})
        if not bonds:
            logger.warning("⚠️ No hay bonos configurados")
            return []
            
        logger.info(f"🏦 Obteniendo precios de {len(bonds)} bonos...")
        
        prices = []
        symbols = list(bonds.keys())
        
        tickers_obj = yf.Tickers(" ".join(symbols))
        for symbol, info in bonds.items():
            try:
                ticker = tickers_obj.tickers.get(symbol) or yf.Ticker(symbol)
                hist = ticker.history(period='2d')
                
                if len(hist) < 1:
                    continue
                
                current_price = float(hist['Close'].iloc[-1])
                
                # Calcular cambio si hay datos de ayer
                change_percent = 0.0
                if len(hist) >= 2:
                    previous_close = float(hist['Close'].iloc[-2])
                    change_percent = ((current_price - previous_close) / previous_close) * 100
                
                if abs(change_percent) >= min_change_percent:
                    prices.append({
                        'symbol': symbol,
                        'name': info.get('name', symbol),
                        'country': info.get('country', 'Unknown'),
                        'type': info.get('type', 'bond'),
                        'price': round(current_price, 4),
                        'change_percent': round(change_percent, 2)
                    })
                
            except Exception as e:
                logger.debug(f"⚠️ Error obteniendo precio de bono {symbol}: {e}")
                continue
        
        # Ordenar por cambio absoluto
        prices.sort(key=lambda x: abs(x['change_percent']), reverse=True)
        logger.info(f"✅ Obtenidos precios de {len(prices)} bonos")
        return prices
    
    def get_top_stocks(
        self,
        symbols: Optional[List[str]] = None,
        use_cache: bool = True,
        ttl: int = 300,
        min_change_percent: float = 2.0,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Obtiene las acciones con mayor cambio porcentual del día usando batch requests.
        
        Args:
            symbols: Lista de símbolos. Si None, usa STOCK_SYMBOLS_DEFAULT.
            use_cache: Si True, usa caché en memoria con TTL.
            ttl: Tiempo de vida del caché en segundos (default 300).
            min_change_percent: Filtro mínimo de cambio porcentual.
            limit: Número máximo de resultados.
            
        Returns:
            Lista de diccionarios con información de acciones.
        """
        default_symbols = getattr(Config, "STOCK_SYMBOLS_DEFAULT", [])
        extended_symbols = getattr(Config, "STOCK_SYMBOLS_EXTENDED", [])
        symbols_to_use = symbols or default_symbols or extended_symbols
        if not symbols_to_use:
            logger.warning("⚠️ No hay símbolos configurados para stocks")
            return []

        cache_key = f"{','.join(sorted(symbols_to_use))}:{min_change_percent}:{limit}"
        now = time.time()
        if use_cache:
            cache_entry = self._stocks_cache.get(cache_key)
            if cache_entry:
                data, ts = cache_entry
                if now - ts <= ttl:
                    logger.info("♻️ Usando caché de acciones")
                    return data

        logger.info(f"📈 Analizando {len(symbols_to_use)} acciones en batch...")
        movers: List[Dict] = []
        tickers_obj = yf.Tickers(" ".join(symbols_to_use))

        def fetch_symbol(sym: str) -> Optional[Dict]:
            try:
                t = tickers_obj.tickers.get(sym) or yf.Ticker(sym)
                hist = t.history(period="2d")
                if len(hist) < 2:
                    return None
                current_price = float(hist["Close"].iloc[-1])
                previous_close = float(hist["Close"].iloc[-2])
                change_percent = ((current_price - previous_close) / previous_close) * 100.0
                if abs(change_percent) < min_change_percent:
                    return None
                info = {}
                try:
                    info = t.get_info()
                except Exception:
                    pass
                return {
                    "symbol": sym,
                    "name": info.get("longName", sym) if isinstance(info, dict) else sym,
                    "price": round(current_price, 2),
                    "change_percent": round(change_percent, 2),
                    "volume": float(hist["Volume"].iloc[-1]) if "Volume" in hist.columns else 0.0,
                    "market_cap": info.get("marketCap", 0) if isinstance(info, dict) else 0,
                }
            except Exception as e:
                logger.debug(f"⚠️ Error en {sym}: {e}")
                return None

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(fetch_symbol, s): s for s in symbols_to_use}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    movers.append(result)

        movers.sort(key=lambda x: abs(x["change_percent"]), reverse=True)
        movers = movers[:limit]
        logger.info(f"✅ Encontradas {len(movers)} acciones con cambio ≥ {min_change_percent}%")

        if use_cache:
            self._stocks_cache[cache_key] = (movers, now)

        return movers
    
    def get_forex_movers(self, min_change_percent: float = 2.0, limit: int = 10) -> List[Dict]:
        """
        Obtiene pares de divisas con mayores movimientos.
        Si no encuentra suficientes con el cambio mínimo, devuelve los tops por movimiento absoluto.
        
        Args:
            min_change_percent: Cambio porcentual mínimo para filtrar
            limit: Límite de pares a retornar
            
        Returns:
            Lista de diccionarios con la info de los pares
        """
        pairs = getattr(Config, "FOREX_PAIRS", [])
        logger.info(f"💱 Analizando {len(pairs)} pares de divisas...")
        all_movers = []
        
        tickers_obj = yf.Tickers(" ".join(pairs))
        for pair in pairs:
            try:
                ticker = tickers_obj.tickers.get(pair) or yf.Ticker(pair)
                hist = ticker.history(period='2d')
                
                if len(hist) < 2:
                    continue
                
                current_rate = hist['Close'].iloc[-1]
                previous_close = hist['Close'].iloc[-2]
                change_percent = ((current_rate - previous_close) / previous_close) * 100
                
                all_movers.append({
                    'pair': pair.replace('=X', ''),
                    'rate': round(current_rate, 4),
                    'change_percent': round(change_percent, 2),
                    'abs_change': abs(change_percent)
                })
                    
            except Exception as e:
                logger.warning(f"⚠️ Error obteniendo datos de {pair}: {e}")
                continue
        
        # Ordenar por cambio absoluto (volatilidad) de mayor a menor
        all_movers.sort(key=lambda x: x['abs_change'], reverse=True)
        
        # Retornar el top, priorizando los que superan el mínimo pero completando hasta el límite
        filtered = [m for m in all_movers if m['abs_change'] >= min_change_percent]
        
        if len(filtered) < limit:
            logger.info(f"ℹ️ Pocos pares con cambio > {min_change_percent}%, completando con top movimientos")
            return all_movers[:limit]
            
        return filtered[:limit]
    
    def get_commodity_prices(self) -> List[Dict]:
        """
        Obtiene precios actuales de commodities (Oro, Plata, Crudo, etc).
        
        Returns:
            Lista con precios actuales de commodities
        """
        commodities = getattr(Config, "COMMODITIES", {})
        logger.info(f"🛢️ Obteniendo precios de {len(commodities)} commodities...")
        
        prices = []
        
        tickers_obj = yf.Tickers(" ".join(list(commodities.keys())))
        for symbol, name in commodities.items():
            try:
                ticker = tickers_obj.tickers.get(symbol) or yf.Ticker(symbol)
                hist = ticker.history(period='2d')
                
                if len(hist) < 1:
                    continue
                
                current_price = hist['Close'].iloc[-1]
                
                # Calcular cambio si hay datos de ayer
                change_percent = 0
                if len(hist) >= 2:
                    previous_close = hist['Close'].iloc[-2]
                    change_percent = ((current_price - previous_close) / previous_close) * 100
                
                prices.append({
                    'symbol': symbol,
                    'name': name,
                    'price': round(current_price, 2),
                    'change_percent': round(change_percent, 2)
                })
                
            except Exception as e:
                logger.warning(f"⚠️ Error obteniendo precio de {name}: {e}")
                continue
        
        logger.info(f"✅ Obtenidos precios de {len(prices)} commodities")
        return prices
    
    def get_market_summary(self, include_bonds: bool = True) -> Dict:
        """
        Obtiene un resumen completo de todos los mercados.
        
        Args:
            include_bonds: Si True, incluye análisis de bonos
        
        Returns:
            Diccionario con resumen de stocks, forex, commodities y bonos
        """
        logger.info("📊 Generando resumen completo de mercados tradicionales...")
        
        summary = {
            'timestamp': datetime.now(),
            'is_weekend': self.is_weekend(),
            'stocks': self.get_top_stocks(min_change_percent=2.0, limit=10),
            'forex': self.get_forex_movers(min_change_percent=0.5, limit=10),
            'commodities': self.get_commodity_prices(),
        }
        
        # Agregar bonos si está habilitado
        if include_bonds:
            summary['bonds'] = self.get_bond_prices(min_change_percent=0.1)
        
        logger.info("✅ Resumen de mercados generado")
        return summary
    
    def _classify_top_instruments_with_ai(self, summary: Dict) -> Dict[str, List[str]]:
        """
        Usa IA para seleccionar los activos más relevantes del día.
        """
        if not self.ai_analyzer:
            # Fallback: Top 3 de cada categoría
            return {
                'stocks': [s['symbol'] for s in summary['stocks'][:3]],
                'forex': [f['pair'] for f in summary['forex'][:3]],
                'commodities': [c['symbol'] for c in summary['commodities']]
            }

        logger.info("🧠 Clasificando activos top con IA...")
        
        return {
            'stocks': [s['symbol'] for s in summary['stocks'][:5]],
            'forex': [f['pair'] for f in summary['forex'][:5]],
            'commodities': [c['symbol'] for c in summary['commodities']]
        }

    def _calculate_signal_tp_sl(self, signal: Dict, capital: float = 20.0, risk_percent: float = 25.0) -> Dict:
        """
        Calcula TP, SL y ganancia potencial para una señal tradicional.
        
        Args:
            signal: Señal de Twelve Data
            capital: Capital a usar ($20 por defecto)
            risk_percent: % de riesgo (25% por defecto)
        """
        current_price = signal.get('current_price', 0)
        rsi = signal.get('rsi', 50)
        signal_type = signal.get('type', 'NEUTRAL')
        
        if current_price <= 0:
            return signal
        
        # Calcular ATR aproximado basado en volatilidad típica
        # Para mercados tradicionales usamos 1-2% como rango típico
        atr_percent = 1.5  # 1.5% de volatilidad típica
        atr = current_price * (atr_percent / 100)
        
        # Ajustar multiplicadores según RSI
        if rsi and rsi < 30:
            sl_mult, tp_mult = 1.5, 3.0  # Sobreventa - más espacio para recuperar
        elif rsi and rsi > 70:
            sl_mult, tp_mult = 1.5, 3.0  # Sobrecompra - más espacio para caer
        else:
            sl_mult, tp_mult = 2.0, 3.5  # Normal
        
        if signal_type == 'LONG':
            stop_loss = current_price - (atr * sl_mult)
            take_profit = current_price + (atr * tp_mult)
        elif signal_type == 'SHORT':
            stop_loss = current_price + (atr * sl_mult)
            take_profit = current_price - (atr * tp_mult)
        else:
            stop_loss = current_price
            take_profit = current_price
        
        # Calcular R:R ratio
        risk = abs(current_price - stop_loss)
        reward = abs(take_profit - current_price)
        rr_ratio = reward / risk if risk > 0 else 0
        
        # Calcular position size y ganancia potencial
        risk_usd = capital * (risk_percent / 100)
        risk_per_unit = abs(current_price - stop_loss) if abs(current_price - stop_loss) > 0 else 0.01
        position_size = risk_usd / risk_per_unit
        position_value = position_size * current_price
        
        # Ganancia potencial si cumple TP
        profit_per_unit = abs(take_profit - current_price)
        potential_profit = position_size * profit_per_unit
        
        signal['stop_loss'] = round(stop_loss, 4)
        signal['take_profit'] = round(take_profit, 4)
        signal['rr_ratio'] = round(rr_ratio, 1)
        signal['capital'] = capital
        signal['risk_percent'] = risk_percent
        signal['position_value'] = round(position_value, 2)
        signal['potential_profit'] = round(potential_profit, 2)
        
        return signal
    
    def _publish_traditional_signals(self, signals: Dict[str, List[Dict]], capital: float = 20.0, 
                                      risk_percent: float = 25.0):
        """Publica señales técnicas de Twelve Data con formato profesional"""
        if not self.telegram:
            return

        logger.info("📤 Publicando señales tradicionales...")
        
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        for category, items in signals.items():
            if not items:
                continue
            
            # Filtrar señales ya publicadas (evitar duplicados)
            new_items = []
            for item in items:
                symbol = item.get('symbol', '')
                signal_type = item.get('type', '')
                if self._is_signal_published(symbol, signal_type):
                    logger.info(f"ℹ️ Señal {symbol} {signal_type} ya publicada en las últimas 24h, omitiendo")
                else:
                    new_items.append(item)
            
            if not new_items:
                logger.info(f"ℹ️ No hay señales nuevas para {category}")
                continue
            
            category_emoji = {"stocks": "📈", "forex": "💱", "commodities": "🛢️"}.get(category, "📊")
            category_name = {"stocks": "ACCIONES", "forex": "FOREX", "commodities": "COMMODITIES"}.get(category, category.upper())
            
            lines = [
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                f"{category_emoji} SEÑALES TÉCNICAS: {category_name}",
                f"⏰ {timestamp} | 💰 Capital: ${capital}",
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                ""
            ]
            
            for i, raw_signal in enumerate(new_items, 1):
                # Calcular TP, SL y ganancia
                signal = self._calculate_signal_tp_sl(raw_signal, capital, risk_percent)
                
                emoji = "🚀" if signal['type'] == 'LONG' else "🔻" if signal['type'] == 'SHORT' else "⚖️"
                confidence = signal.get('confidence', 50)
                
                # Rating profesional
                if confidence >= 70:
                    rating = "⭐⭐⭐ Premium"
                elif confidence >= 55:
                    rating = "⭐⭐ Estándar"
                elif confidence >= 40:
                    rating = "⭐ Especulativo"
                else:
                    rating = "⚡ Alto Riesgo"
                
                lines.append(f"#{i} {signal['symbol']} | {rating}")
                lines.append(f"{emoji} Señal: {signal['type']}")
                lines.append(f"💰 Entrada: ${signal['current_price']:,.4f}")
                lines.append(f"🎯 Take Profit: ${signal.get('take_profit', 0):,.4f}")
                lines.append(f"🛑 Stop Loss: ${signal.get('stop_loss', 0):,.4f}")
                lines.append(f"📊 R:R Ratio: 1:{signal.get('rr_ratio', 0):.1f}")
                lines.append(f"🔥 Confianza: {confidence}%")
                
                # Análisis de indicadores
                if signal.get('rsi'):
                    rsi = signal['rsi']
                    rsi_status = "🟢 Sobreventa" if rsi < 30 else "🔴 Sobrecompra" if rsi > 70 else "⚪ Neutral"
                    lines.append(f"📉 RSI: {rsi:.1f} ({rsi_status})")
                
                if signal.get('macd'):
                    macd_data = signal['macd']
                    if isinstance(macd_data, dict):
                        macd_trend = "📈 Alcista" if macd_data.get('histogram', 0) > 0 else "📉 Bajista"
                        lines.append(f"📊 MACD: {macd_trend}")
                
                # Ganancia potencial
                lines.append(f"💵 Ganancia potencial: ${signal.get('potential_profit', 0):,.2f}")
                lines.append("")
            
            # Footer
            lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            lines.append("⚠️ GESTIÓN DE RIESGO")
            lines.append(f"• Riesgo máximo: {risk_percent}% (${capital * risk_percent / 100:.2f})")
            lines.append("• Usa stop loss SIEMPRE")
            lines.append("• DYOR - Haz tu investigación")
            lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
            msg = "\n".join(lines)
            
            try:
                self.telegram.send_market_message(msg)
                # Guardar señales en historial después de publicar exitosamente
                for signal in new_items:
                    self._save_signal_to_history(signal['symbol'], signal['type'])
                logger.info(f"✅ {len(new_items)} señales de {category} publicadas y guardadas en historial")
            except Exception as e:
                logger.error(f"❌ Error enviando señales {category}: {e}")

    def run_traditional_markets_analysis(self, publish: bool = True, get_signals: bool = True, 
                                          force_analysis: bool = False) -> Dict:
        """
        Método wrapper para ejecutar análisis completo de mercados tradicionales.
        
        Args:
            publish: Si True, publica resultados (respeta fin de semana)
            get_signals: Si True, obtiene señales técnicas
            force_analysis: Si True, analiza incluso en fin de semana
            
        Returns:
            Resumen de mercados
        """
        logger.info("\n📊 ANÁLISIS DE MERCADOS TRADICIONALES")
        logger.info("=" * 60)
        
        is_weekend = self.is_weekend()
        capital = getattr(Config, 'DEFAULT_CAPITAL', 20.0)
        risk_percent = getattr(Config, 'DEFAULT_RISK_PERCENT', 25.0)
        
        # Variables de control separadas para reportes y señales
        publish_reports = publish  # Reportes de mercado
        publish_signals = True     # Señales SIEMPRE se publican (incluso fines de semana)
        
        if is_weekend:
            logger.info("📅 Es fin de semana - Mercados tradicionales CERRADOS")
            logger.info("ℹ️ Reportes NO se publican, pero señales SÍ")
            publish_reports = False  # NO publicar reportes los fines de semana
            # publish_signals sigue True - las señales SÍ se publican
        
        # Obtener resumen (siempre, para tener datos)
        summary = self.get_market_summary(include_bonds=True)
        
        # 1. Mostrar resumen en logs
        self._log_market_summary(summary)
        
        # 2. Publicar resumen general (solo si NO es fin de semana)
        if publish_reports and (self.telegram or self.twitter):
            self._publish_results(summary)
        elif is_weekend:
            logger.info("ℹ️ Reportes de mercado omitidos (fin de semana)")
            
        # 3. Análisis Técnico Profundo con Twelve Data
        if get_signals:
            try:
                top_instruments = self._classify_top_instruments_with_ai(summary)
                
                signals = self.twelve_data.analyze_top_instruments(
                    top_instruments['stocks'],
                    top_instruments['forex'],
                    top_instruments['commodities']
                )
                
                # Guardar señales en summary para uso posterior
                summary['signals'] = signals
                
                # Publicar señales (SIEMPRE, incluso fines de semana)
                if publish_signals:
                    self._publish_traditional_signals(signals, capital=capital, risk_percent=risk_percent)
                else:
                    logger.info("ℹ️ Señales generadas pero NO publicadas")
                    for cat, sigs in signals.items():
                        for sig in sigs:
                            logger.info(f"   📊 {cat.upper()} {sig['symbol']}: {sig['type']} ({sig.get('confidence', 0)}%)")
                    
            except Exception as e:
                logger.error(f"❌ Error en análisis Twelve Data: {e}")

        logger.info("\n✅ Análisis de mercados tradicionales completado")
        return summary

    def _log_market_summary(self, summary):
        """Helper para loguear resumen"""
        logger.info("\n📈 ACCIONES (Top Movers > 2.0%):")
        if summary.get('stocks'):
            for stock in summary['stocks']:
                emoji = "🟢" if stock['change_percent'] > 0 else "🔴"
                logger.info(f"   {emoji} {stock['symbol']}: {stock['change_percent']:+.2f}% (${stock['price']})")
        else:
            logger.info("   (Sin cambios significativos)")
        
        # Loguear bonos si existen
        if summary.get('bonds'):
            logger.info("\n🏦 BONOS (Rendimientos):")
            for bond in summary['bonds'][:5]:
                emoji = "🟢" if bond['change_percent'] > 0 else "🔴"
                logger.info(f"   {emoji} {bond['name']}: {bond['change_percent']:+.2f}% ({bond['price']:.2f}%)")

    
    def _publish_results(self, summary: Dict):
        """
        Publica los resultados del análisis en Telegram y Twitter.
        
        Args:
            summary: Diccionario con el resumen de mercados
        """
        # --- TELEGRAM ---
        if self.telegram:
            if summary.get('stocks'):
                message_lines = ["📊 MERCADOS TRADICIONALES\n", "📈 ACCIONES:"]
                for stock in summary['stocks'][:10]:
                    emoji = "🟢" if stock['change_percent'] > 0 else "🔴"
                    message_lines.append(f"{emoji} {stock['symbol']}: {stock['change_percent']:+.2f}% (${stock['price']})")
                telegram_msg = "\n".join(message_lines)
                try:
                    self.telegram.send_market_message(telegram_msg, image_path=Config.STOCKS_IMAGE_PATH)
                    logger.info("✅ Resultados de Acciones enviados a Telegram (Bot Markets)")
                except Exception as e:
                    logger.error(f"❌ Error enviando Acciones a Telegram: {e}")
            
            if summary.get('forex'):
                message_lines = ["📊 MERCADOS TRADICIONALES\n", "💱 FOREX (Top 10):"]
                for forex in summary['forex'][:10]:
                    emoji = "🟢" if forex['change_percent'] > 0 else "🔴"
                    message_lines.append(f"{emoji} {forex['pair']}: {forex['change_percent']:+.2f}%")
                telegram_msg = "\n".join(message_lines)
                try:
                    self.telegram.send_market_message(telegram_msg, image_path=Config.FOREX_IMAGE_PATH)
                    logger.info("✅ Resultados de Forex enviados a Telegram (Bot Markets)")
                except Exception as e:
                    logger.error(f"❌ Error enviando Forex a Telegram: {e}")
            
            if summary.get('commodities'):
                message_lines = ["📊 MERCADOS TRADICIONALES\n", "🛢️ COMMODITIES:"]
                for commodity in summary['commodities']:
                    emoji = "🟢" if commodity['change_percent'] > 0 else "🔴"
                    message_lines.append(f"{emoji} {commodity['name']}: {commodity['change_percent']:+.2f}% (${commodity['price']})")
                telegram_msg = "\n".join(message_lines)
                try:
                    self.telegram.send_market_message(telegram_msg, image_path=Config.COMMODITIES_IMAGE_PATH)
                    logger.info("✅ Resultados de Commodities enviados a Telegram (Bot Markets)")
                except Exception as e:
                    logger.error(f"❌ Error enviando Commodities a Telegram: {e}")
            
            # BONOS MUNDIALES
            if summary.get('bonds'):
                message_lines = ["📊 MERCADOS TRADICIONALES\n", "🏦 BONOS MUNDIALES:"]
                for bond in summary['bonds'][:8]:  # Top 8 bonos
                    emoji = "🟢" if bond['change_percent'] > 0 else "🔴"
                    # Para bonos/yields, mostramos el rendimiento
                    message_lines.append(f"{emoji} {bond['name']}: {bond['change_percent']:+.2f}% (Yield: {bond['price']:.2f}%)")
                telegram_msg = "\n".join(message_lines)
                try:
                    self.telegram.send_market_message(telegram_msg)  # Sin imagen específica de bonos
                    logger.info("✅ Resultados de Bonos enviados a Telegram (Bot Markets)")
                except Exception as e:
                    logger.error(f"❌ Error enviando Bonos a Telegram: {e}")
        
        # --- TWITTER (Tweets Separados) ---
        if self.twitter:
            try:
                # Tweet 1: Acciones (solo si hay importantes)
                if summary.get('stocks'):
                    tweet1 = "📊 MERCADOS TRADICIONALES\n\n📈 ACCIONES:\n"
                    tokens_used = len(tweet1)
                    
                    for stock in summary['stocks']:
                        emoji = "🟢" if stock['change_percent'] > 0 else "🔴"
                        line = f"{emoji} {stock['symbol']}: {stock['change_percent']:+.2f}%\n"
                        if tokens_used + len(line) < 270:
                            tweet1 += line
                            tokens_used += len(line)
                        else:
                            break
                    
                    self.twitter.post_tweet(tweet1.strip(), image_path=Config.STOCKS_IMAGE_PATH, category='markets')
                    logger.info("✅ Tweet de Acciones publicado")
                    logger.info("⏳ Esperando 30 segundos para la siguiente publicación...")
                    time.sleep(getattr(Config, "TWITTER_POST_DELAY", 30))
                
                # Tweet 2: Forex (Top 7 aprox para caber)
                if summary.get('forex'):
                    tweet2 = "💱 FOREX (Top Movimientos):\n"
                    tokens_used = len(tweet2)
                    
                    for forex in summary['forex']:
                        emoji = "🟢" if forex['change_percent'] > 0 else "🔴"
                        line = f"{emoji} {forex['pair']}: {forex['change_percent']:+.2f}%\n"
                        if tokens_used + len(line) < 270:
                            tweet2 += line
                            tokens_used += len(line)
                        else:
                            break
                            
                    self.twitter.post_tweet(tweet2.strip(), image_path=Config.FOREX_IMAGE_PATH, category='markets')
                    logger.info("✅ Tweet de Forex publicado")
                    logger.info("⏳ Esperando 30 segundos para la siguiente publicación...")
                    time.sleep(getattr(Config, "TWITTER_POST_DELAY", 30))
                
                # Tweet 3: Commodities
                if summary.get('commodities'):
                    tweet3 = "🛢️ COMMODITIES:\n"
                    for commodity in summary['commodities']:
                        emoji = "🟢" if commodity['change_percent'] > 0 else "🔴"
                        tweet3 += f"{emoji} {commodity['name']}: {commodity['change_percent']:+.2f}%\n"
                    
                    self.twitter.post_tweet(tweet3.strip(), image_path=Config.COMMODITIES_IMAGE_PATH, category='markets')
                    logger.info("✅ Tweet de Commodities publicado")
                    logger.info("⏳ Esperando 30 segundos para la siguiente publicación...")
                    time.sleep(getattr(Config, "TWITTER_POST_DELAY", 30))
                
                # Tweet 4: Bonos (NUEVO)
                if summary.get('bonds') and len(summary['bonds']) >= 3:
                    tweet4 = "🏦 BONOS MUNDIALES:\n"
                    tokens_used = len(tweet4)
                    
                    for bond in summary['bonds']:
                        emoji = "🟢" if bond['change_percent'] > 0 else "🔴"
                        line = f"{emoji} {bond['name'][:20]}: {bond['change_percent']:+.2f}%\n"
                        if tokens_used + len(line) < 270:
                            tweet4 += line
                            tokens_used += len(line)
                        else:
                            break
                    
                    self.twitter.post_tweet(tweet4.strip(), category='markets')
                    logger.info("✅ Tweet de Bonos publicado")
                
            except Exception as e:
                logger.error(f"❌ Error publicando en Twitter: {e}")



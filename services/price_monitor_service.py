"""
Servicio de Monitoreo Continuo de Precios.
Detecta pumps/dumps y nuevos pares en tiempo real.
"""
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional
from utils.logger import logger
from services.binance_service import BinanceService
from services.telegram_service import TelegramService
from services.twitter_service import TwitterService
from database.mysql_manager import MySQLManager


class PriceMonitorService:
    """Servicio para monitoreo continuo de precios y detección de anomalías"""
    
    def __init__(self, db: MySQLManager, telegram: TelegramService, twitter: TwitterService):
        """
        Inicializa el servicio de monitoreo.
        
        Args:
            db: Instancia de MySQLManager
            telegram: Instancia de TelegramService
            twitter: Instancia de TwitterService
        """
        self.db = db
        self.telegram = telegram
        self.twitter = twitter
        self.binance = BinanceService()
        
        # Control de hilos
        self.monitoring_thread = None
        self.stop_event = threading.Event()
        self.is_running = False
        
        # Cache de precios y pares
        self.price_cache: Dict[str, float] = {}
        self.known_pairs: Set[str] = set()
        
        # Configuración
        self.check_interval = 300  # 5 minutos en segundos
        self.pump_dump_threshold = 5.0  # 5% de cambio
        
        logger.info("✅ Servicio de Monitoreo de Precios inicializado")
    
    def start_monitoring(self, duration_hours: float = 2.0):
        """
        Inicia el monitoreo continuo en un hilo separado.
        
        Args:
            duration_hours: Duración del monitoreo en horas (default: 2)
        """
        if self.is_running:
            logger.warning("⚠️ El monitoreo ya está en ejecución")
            return
        
        logger.info(f"🔄 Iniciando monitoreo continuo por {duration_hours} horas...")
        
        # Resetear evento de parada
        self.stop_event.clear()
        
        # Crear y arrancar hilo
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(duration_hours,),
            daemon=True
        )
        self.monitoring_thread.start()
        self.is_running = True
        
        logger.info("✅ Monitoreo continuo iniciado en segundo plano")
    
    def stop_monitoring(self):
        """Detiene el monitoreo continuo"""
        if not self.is_running:
            logger.warning("⚠️ El monitoreo no está en ejecución")
            return
        
        logger.info("🛑 Deteniendo monitoreo continuo...")
        self.stop_event.set()
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=10)
        
        self.is_running = False
        logger.info("✅ Monitoreo continuo detenido")
    
    def _monitoring_loop(self, duration_hours: float):
        """
        Loop principal de monitoreo (ejecutado en hilo separado).
        
        Args:
            duration_hours: Duración del monitoreo
        """
        try:
            start_time = time.time()
            end_time = start_time + (duration_hours * 3600)
            iteration = 0
            
            # Inicializar snapshot de pares conocidos
            self._initialize_known_pairs()
            
            # Inicializar cache de precios
            self._initialize_price_cache()
            
            logger.info(f"📊 Snapshot inicial: {len(self.known_pairs)} pares, {len(self.price_cache)} precios")
            
            while time.time() < end_time and not self.stop_event.is_set():
                iteration += 1
                cycle_start = time.time()
                
                logger.info(f"\n🔍 Ciclo de monitoreo #{iteration} - {datetime.now().strftime('%H:%M:%S')}")
                
                # 1. Detectar pumps y dumps
                self._check_price_movements()
                
                # 2. Detectar nuevos pares
                self._check_new_pairs()
                
                # Calcular tiempo restante
                elapsed = time.time() - start_time
                remaining = (end_time - time.time()) / 60  # en minutos
                
                logger.info(f"⏱  Tiempo transcurrido: {elapsed/60:.1f} min | Restante: {remaining:.1f} min")
                
                # Esperar hasta el próximo ciclo (5 minutos)
                cycle_duration = time.time() - cycle_start
                sleep_time = max(0, self.check_interval - cycle_duration)
                
                if sleep_time > 0 and not self.stop_event.is_set():
                    logger.info(f"💤 Esperando {sleep_time/60:.1f} minutos hasta próximo ciclo...")
                    self.stop_event.wait(timeout=sleep_time)
            
            logger.info(f"\n✅ Monitoreo continuo finalizado después de {iteration} ciclos")
            self.is_running = False
            
        except Exception as e:
            logger.error(f"❌ Error en loop de monitoreo: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.is_running = False
    
    def _initialize_known_pairs(self):
        """Inicializa el set de pares conocidos desde Binance"""
        try:
            markets = self.binance.exchange.load_markets()
            self.known_pairs = set(markets.keys())
            logger.info(f"✅ {len(self.known_pairs)} pares conocidos inicializados")
        except Exception as e:
            logger.error(f"❌ Error inicializando pares conocidos: {e}")
            self.known_pairs = set()
    
    def _initialize_price_cache(self):
        """Inicializa el cache de precios con valores actuales"""
        try:
            # Obtener top 50 por volumen
            tickers = self.binance.exchange.fetch_tickers()
            usdt_pairs = {k: v for k, v in tickers.items() if k.endswith('/USDT')}
            
            # Ordenar por volumen y tomar top 50
            sorted_pairs = sorted(usdt_pairs.items(), key=lambda x: x[1].get('quoteVolume', 0), reverse=True)[:50]
            
            for symbol, ticker in sorted_pairs:
                self.price_cache[symbol] = ticker.get('last', 0)
            
            logger.info(f"✅ Cache de precios inicializado con {len(self.price_cache)} pares")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando cache de precios: {e}")
            self.price_cache = {}
    
    def _check_price_movements(self):
        """Detecta pumps y dumps comparando precios actuales con cache"""
        try:
            alerts = []
            
            # Obtener precios actuales
            tickers = self.binance.exchange.fetch_tickers()
            
            for symbol, old_price in self.price_cache.items():
                if symbol not in tickers:
                    continue
                
                current_price = tickers[symbol].get('last', 0)
                
                if old_price > 0 and current_price > 0:
                    change_percent = ((current_price - old_price) / old_price) * 100
                    
                    if abs(change_percent) >= self.pump_dump_threshold:
                        alert_type = 'pump' if change_percent > 0 else 'dump'
                        
                        alert = {
                            'symbol': symbol,
                            'type': alert_type,
                            'price_before': old_price,
                            'price_after': current_price,
                            'change_percent': change_percent,
                            'timestamp': datetime.now()
                        }
                        
                        alerts.append(alert)
                        
                        # Actualizar cache
                        self.price_cache[symbol] = current_price
                        
                        # Guardar en DB
                        self._save_price_alert(alert)
            
            if alerts:
                logger.info(f"🚨 {len(alerts)} alertas de precio detectadas")
                self._publish_price_alerts(alerts)
            else:
                logger.info("✅ No se detectaron cambios significativos de precio")
            
        except Exception as e:
            logger.error(f"❌ Error verificando movimientos de precio: {e}")
    
    def _check_new_pairs(self):
        """Detecta nuevos pares de trading en Binance"""
        try:
            # Recargar mercados
            markets = self.binance.exchange.load_markets(reload=True)
            current_pairs = set(markets.keys())
            
            # Detectar nuevos pares
            new_pairs = current_pairs - self.known_pairs
            
            if new_pairs:
                logger.info(f"🆕 {len(new_pairs)} nuevos pares detectados!")
                
                for symbol in new_pairs:
                    try:
                        ticker = self.binance.exchange.fetch_ticker(symbol)
                        price = ticker.get('last', 0)
                        
                        # Guardar en DB
                        self._save_new_pair(symbol, price)
                        
                        # Publicar alerta
                        self._publish_new_pair_alert(symbol, price)
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Error obteniendo datos de {symbol}: {e}")
                
                # Actualizar set de pares conocidos
                self.known_pairs = current_pairs
            else:
                logger.info("✅ No se detectaron nuevos pares")
            
        except Exception as e:
            logger.error(f"❌ Error verificando nuevos pares: {e}")
    
    def _save_price_alert(self, alert: Dict):
        """Guarda alerta de precio en la base de datos"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO price_alerts 
                (symbol, alert_type, price_before, price_after, change_percent)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                alert['symbol'],
                alert['type'],
                alert['price_before'],
                alert['price_after'],
                alert['change_percent']
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.warning(f"⚠️ Error guardando alerta en DB: {e}")
    
    def _save_new_pair(self, symbol: str, price: float):
        """Guarda nuevo par detectado en la base de datos"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO new_pairs_detected 
                (symbol, exchange, first_price)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE detected_at = CURRENT_TIMESTAMP
            """, (symbol, 'binance', price))
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.warning(f"⚠️ Error guardando nuevo par en DB: {e}")
    
    def _publish_price_alerts(self, alerts: List[Dict]):
        """Publica alertas de precio en Twitter y Telegram"""
        try:
            # Limitar a las 3 alertas más significativas
            top_alerts = sorted(alerts, key=lambda x: abs(x['change_percent']), reverse=True)[:3]
            
            # Remover publicación en Twitter para señales
            
            # Telegram
            telegram_text = "🚨 <b>ALERTAS DE PRECIO</b>\n\n"
            
            for alert in alerts:
                emoji = "🚀" if alert['type'] == 'pump' else "📉"
                action = "COMPRAR" if alert['type'] == 'pump' else "VENDER"
                
                telegram_text += f"{emoji} <b>{alert['symbol']}</b>\n"
                telegram_text += f"   Cambio: <b>{alert['change_percent']:+.2f}%</b> en 5 min\n"
                telegram_text += f"   Precio: ${alert['price_after']:.8f}\n"
                telegram_text += f"   Acción sugerida: {action}\n\n"
            
            logger.info(f"📱 Enviando alerta a Telegram (Bot Signals)...")
            self.telegram.send_signal_message(telegram_text)
            
        except Exception as e:
            logger.error(f"❌ Error publicando alertas: {e}")
    
    def _publish_new_pair_alert(self, symbol: str, price: float):
        """Publica alerta de nuevo par en Twitter y Telegram"""
        try:
            # Remover publicación en Twitter para señales
            
            # Telegram
            telegram_text = f"🆕 <b>NUEVO PAR DETECTADO EN BINANCE</b>\n\n"
            telegram_text += f"💎 Símbolo: <b>{symbol}</b>\n"
            telegram_text += f"💰 Precio inicial: ${price:.8f}\n"
            telegram_text += f"📊 Exchange: Binance\n"
            telegram_text += f"⏰ Detectado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            telegram_text += f"⚠️ Oportunidad de inversión temprana!"
            
            logger.info(f"📱 Enviando nuevo par a Telegram (Bot Signals)...")
            self.telegram.send_signal_message(telegram_text)
            
        except Exception as e:
            logger.error(f"❌ Error publicando nuevo par: {e}")
    
    def run_monitoring_cycle_once(self):
        """
        Ejecuta un solo ciclo de monitoreo (para usar en el ciclo completo).
        No ejecuta en hilo separado, sino directamente.
        """
        try:
            logger.info("🔍 Ejecutando ciclo único de monitoreo...")
            
            # Inicializar si es necesario
            if not self.known_pairs:
                self._initialize_known_pairs()
            
            if not self.price_cache:
                self._initialize_price_cache()
            
            # Ejecutar checks
            self._check_price_movements()
            self._check_new_pairs()
            
            logger.info("✅ Ciclo de monitoreo completado")
            
        except Exception as e:
            logger.error(f"❌ Error en ciclo de monitoreo: {e}")


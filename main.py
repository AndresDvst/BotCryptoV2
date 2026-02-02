"""
Script principal del bot de criptomonedas.
Refactor: BotManager singleton, menú modular y espera eficiente.
"""
import sys
import os
import time
import schedule
import subprocess
import traceback
from dataclasses import dataclass
from typing import Callable, List, Optional
from datetime import datetime, timedelta

from bot_orchestrator import CryptoBotOrchestrator
from config.config import Config
from utils.logger import logger
from services.telegram_message_tester import TelegramMessageTester

class BotManager:
    """Gestor de instancia única del orquestador"""
    def __init__(self):
        self._bot: Optional[CryptoBotOrchestrator] = None
        self._message_tester: Optional[TelegramMessageTester] = None
    def get_bot(self) -> CryptoBotOrchestrator:
        if self._bot is None:
            self._bot = CryptoBotOrchestrator()
        return self._bot
    def get_message_tester(self) -> TelegramMessageTester:
        if self._message_tester is None:
            self._message_tester = TelegramMessageTester(self.get_bot().telegram)
        return self._message_tester
    def restart(self) -> CryptoBotOrchestrator:
        if self._bot:
            try:
                self._bot.cleanup()
            except Exception:
                pass
        self._bot = CryptoBotOrchestrator()
        self._message_tester = None  # Reset tester on restart
        return self._bot

@dataclass
class MenuOption:
    number: str
    label: str
    icon: str
    handler: Callable[[BotManager], None]

def post_execution_menu(manager: BotManager):
    """
    Menú que se muestra después de completar una tarea.
    Permite volver al menú principal o reiniciar el bot.
    """
    while True:
        print("\n" + "=" * 60)
        print("✅ TAREA COMPLETADA")
        print("=" * 60)
        print("1. 🔙 Volver al menú principal")
        print("2. 🔁 Reiniciar bot")
        print("3. ⏰ Modo Espera Inteligente")
        print("4. 🧪 Prueba de Mensajes Telegram")
        print("0. 👋 Salir")
        print("=" * 60)
        
        choice = input("\nSelecciona una opción: ").strip()
        
        if choice == '1':
            return 'menu'
        elif choice == '2':
            return 'restart'
        elif choice == '3':
            run_smart_wait_mode(manager)
            return 'menu'  # Si sale del modo espera
        elif choice == '4':
            manager.get_message_tester().show_menu()
            continue  # Volver a mostrar el menú post-tarea
        elif choice == '0':
            return 'exit'
        else:
            logger.warning("⚠️  Opción no válida, intenta de nuevo")

def run_complete_cycle(manager: BotManager):
    """
    Ejecuta el ciclo completo: análisis básico + top monedas + mercados tradicionales + 
    noticias + modo continuo.
    """
    logger.info("\n🌟 INICIANDO CICLO COMPLETO DE ANÁLISIS")
    logger.info("=" * 60)
    
    # 1. Análisis grande de crypto (112 monedas con cambios significativos)
    logger.info("\n📊 PASO 1/5: Análisis de criptomonedas con cambios significativos...")
    manager.get_bot().run_analysis_cycle(is_morning=False)
    
    # 2. Análisis exhaustivo de Top Monedas + LTC (mínimo 2 señales)
    logger.info("\n🎯 PASO 2/5: Análisis exhaustivo de Top Monedas + LTC...")
    capital = getattr(Config, 'DEFAULT_CAPITAL', 20)
    risk_percent = getattr(Config, 'DEFAULT_RISK_PERCENT', 25)
    manager.get_bot().technical_analysis.run_technical_analysis(
        capital, risk_percent,
        telegram=manager.get_bot().telegram,
        twitter=manager.get_bot().twitter
    )
    
    # 3. Mercados tradicionales
    logger.info("\n📈 PASO 3/5: Análisis de mercados tradicionales...")
    manager.get_bot().traditional_markets.run_traditional_markets_analysis()
    
    # 4. Scraping de noticias (TradingView)
    logger.info("\n📰 PASO 4/5: Scraping de noticias TradingView...")
    manager.get_bot().tradingview_news.process_and_publish()
    
    # 5. Modo continuo (ejecutar una vez, no infinito)
    logger.info("\n🔄 PASO 5/5: Monitoreo de pumps/dumps...")
    manager.get_bot().price_monitor.run_monitoring_cycle_once()
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ CICLO COMPLETO FINALIZADO")
    logger.info("=" * 60)

def setup_scheduler(manager: BotManager):
    """Configura el programador de tareas"""
    logger.info("📅 Configurando programador de tareas...")
    
    def run_morning_analysis():
        logger.info("\n☀️ Ejecutando reporte matutino...")
        manager.get_bot().run_analysis_cycle(is_morning=True)
    
    def run_regular_analysis():
        logger.info("\n🔄 Ejecutando reporte programado...")
        manager.get_bot().run_analysis_cycle(is_morning=False)
    
    # Programar reporte matutino a las 6 AM
    schedule.every().day.at(Config.MORNING_POST_TIME).do(run_morning_analysis)
    logger.info(f"✅ Reporte matutino programado para las {Config.MORNING_POST_TIME}")
    
    # Programar reportes cada 2 horas
    schedule.every(Config.REPORT_INTERVAL_HOURS).hours.do(run_regular_analysis)
    logger.info(f"✅ Reportes programados cada {Config.REPORT_INTERVAL_HOURS} horas")
    
    logger.info("\n📋 Resumen de tareas programadas:")
    for job in schedule.get_jobs():
        logger.info(f"   - {job}")

def run_smart_wait_mode(manager: BotManager):
    """
    Ejecuta el modo de espera inteligente:
    - Cada 5 min: Monitoreo de pumps/dumps
    - Cada 2 horas: Ciclo completo de análisis
    - Tecla 't': Prueba de mensajes Telegram
    """
    logger.info("\n⏰ INICIANDO MODO ESPERA INTELIGENTE")
    logger.info("=" * 60)
    logger.info("🕒 Ciclo de monitoreo:     5 minutos")
    logger.info("📰 Noticias TradingView:   12 minutos")
    logger.info("🌟 Ciclo completo:         2 horas")
    logger.info("📝 Tecla 't':              Prueba de mensajes")
    logger.info("🛑 Presiona Ctrl+C para detener")
    logger.info("=" * 60)
    
    last_monitor_time = 0.0
    last_news_time = 0.0  # Force first run or wait? Better force first run or wait a bit? 
    # Usually better to run immediately or shortly after start logic if we want immediate feedback.
    # But user asked to behave like monitoring. Monitoring runs immediately because last_monitor_time=0.
    
    last_full_cycle_time = time.time()
    
    # Intervalos en segundos
    MONITOR_INTERVAL = 5 * 60
    NEWS_INTERVAL = 12 * 60
    FULL_CYCLE_INTERVAL = 2 * 60 * 60
    
    try:
        while True:
            current_time = time.time()
            
            # 1. Monitoreo de Pumps/Dumps (Cada 5 min)
            if current_time - last_monitor_time >= MONITOR_INTERVAL:
                logger.info("\n🔄 [AUTO] Ejecutando monitoreo de pumps/dumps...")
                manager.get_bot().price_monitor.run_monitoring_cycle_once()
                last_monitor_time = current_time
                
            # 2. Noticias TradingView (Cada 12 min)
            if current_time - last_news_time >= NEWS_INTERVAL:
                logger.info("\n📰 [AUTO] Buscando noticias en TradingView...")
                try:
                   manager.get_bot().tradingview_news.process_and_publish()
                except Exception as e:
                   logger.error(f"❌ Error en noticias: {e}")
                last_news_time = current_time

            # 3. Ciclo Completo (Cada 2 horas)
            if current_time - last_full_cycle_time >= FULL_CYCLE_INTERVAL:
                logger.info("\n🌟 [AUTO] Ejecutando ciclo completo programado...")
                run_complete_cycle(manager)
                last_full_cycle_time = current_time
            
            # Mostrar status cada minuto
            next_monitor_in = (last_monitor_time + MONITOR_INTERVAL) - current_time
            next_news_in = (last_news_time + NEWS_INTERVAL) - current_time
            next_cycle_in = (last_full_cycle_time + FULL_CYCLE_INTERVAL) - current_time
            
            monitor_wait = max(0, int(next_monitor_in))
            news_wait = max(0, int(next_news_in))
            cycle_wait = max(0, int(next_cycle_in))
            
            monitor_str = f"{monitor_wait//60:02d}:{monitor_wait%60:02d}"
            news_str = f"{news_wait//60:02d}:{news_wait%60:02d}"
            cycle_str = f"{cycle_wait//3600:02d}:{(cycle_wait%3600)//60:02d}:{cycle_wait%60:02d}"
            
            print(f"\r⏳ Monitoreo {monitor_str} | Noticias {news_str} | Ciclo {cycle_str} | [t]=Test", end="")
            
            # Sleep dinámico: despertar cuando toque lo más próximo, pero max 60s para actualizar display
            next_event_in = min(
                next_monitor_in if next_monitor_in > 0 else MONITOR_INTERVAL,
                next_news_in if next_news_in > 0 else NEWS_INTERVAL,
                next_cycle_in if next_cycle_in > 0 else FULL_CYCLE_INTERVAL
            )
            sleep_seconds = max(1, min(60, int(next_event_in)))
            time.sleep(sleep_seconds)
            
    except KeyboardInterrupt:
        logger.info("\n\n⏸️ Modo espera pausado")
        # Mostrar menú de opciones
        while True:
            print("\n" + "=" * 60)
            print("⏸️ MODO ESPERA - PAUSADO")
            print("=" * 60)
            print("1. ▶️  Continuar modo espera")
            print("2. 📝 Prueba de mensajes Telegram")
            print("3. 🔙 Volver al menú principal")
            print("0. 👋 Salir")
            print("=" * 60)
            
            choice = input("\nSelecciona una opción: ").strip()
            
            if choice == '1':
                # Reiniciar modo espera
                run_smart_wait_mode(manager)
                return
            elif choice == '2':
                manager.get_message_tester().show_menu()
                continue
            elif choice == '3':
                return  # Volver al menú principal
            elif choice == '0':
                logger.info("👋 Saliendo...")
                sys.exit(0)
            else:
                print("⚠️ Opción no válida")

def main():
    """Función principal del bot"""
    
    try:
        # Banner de inicio
        logger.info("\n" + "=" * 60)
        logger.info("🚀 CRYPTO BOT - INICIANDO (V2 Enterprise)")
        logger.info("=" * 60)
        logger.info(f"📅 Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60 + "\n")
        
        # Validar configuración
        logger.info("🔍 Validando configuración...")
        Config.validate()
        logger.info("✅ Configuración válida\n")
        
        manager = BotManager()
        
        # Modo automático para Docker (sin menú interactivo)
        if Config.IS_DOCKER or '--auto' in sys.argv:
            logger.info("🐳 Modo Docker/Automático detectado - Iniciando Modo Espera Inteligente")
            run_smart_wait_mode(manager)
            return
        
        # Menú principal mejorado
        while True:
            print("\n" + "=" * 60)
            print("💡 MENÚ PRINCIPAL - CRYPTO BOT V3")
            print("=" * 60)
            options: List[MenuOption] = [
                MenuOption('1', '🌟 Análisis Completo (Todo en un ciclo)', '🌟', lambda m: run_complete_cycle(m)),
                MenuOption('2', '⏰ Programar ejecuciones automáticas (cada 2h + 6 AM)', '⏰', lambda m: setup_scheduler(m)),
                MenuOption('3', '🚀 Análisis Básico (solo crypto)', '🚀', lambda m: m.get_bot().run_analysis_cycle(is_morning=False)),
                MenuOption('4', '📊 Abrir Dashboard Web', '📊', lambda m: subprocess.run([sys.executable, "dashboard/app.py"], cwd=os.getcwd())),
                MenuOption('5', '🧹 Limpiar repositorio (archivos temporales)', '🧹', lambda m: subprocess.run([sys.executable, "cleanup_repo.py"], cwd=os.getcwd())),
                MenuOption('6', '🗑️  Limpiar base de datos (CUIDADO!)', '🗑️', lambda m: m.get_bot().db.clear_database() if m.get_bot().db else None),
                MenuOption('7', '📈 Análisis de Mercados Tradicionales (Stocks/Forex/Commodities)', '📈', lambda m: m.get_bot().traditional_markets.run_traditional_markets_analysis()),
                MenuOption('8', '🎯 Análisis Técnico con Señales de Trading', '🎯', lambda m: m.get_bot().technical_analysis.run_technical_analysis(1000, 2)),
                MenuOption('9', '🔄 Modo Continuo (Monitoreo 5 min)', '🔄', lambda m: m.get_bot().price_monitor.start_monitoring()),
                MenuOption('10', '📰 Scraping de Noticias TradingView', '📰', lambda m: m.get_bot().tradingview_news.process_and_publish()),
                MenuOption('11', '🔁 Reiniciar Bot (útil para pruebas)', '🔁', lambda m: m.restart()),
                MenuOption('12', '⏰ Modo Espera Inteligente (Monitoreo + Noticias + Ciclo 2h)', '⏰', lambda m: run_smart_wait_mode(m)),
                MenuOption('13', '🧪 Backtesting (Probar estrategias con datos históricos)', '🧪', lambda m: m.get_bot().backtest.interactive_backtest() if m.get_bot().backtest else print("❌ Servicio de backtest no disponible")),
                MenuOption('14', '📝 Prueba de Mensajes Telegram (Formato)', '📝', lambda m: m.get_message_tester().show_menu()),
            ]
            for opt in options:
                print(f"{opt.number}. {opt.label}")
            print("0. 👋 Salir")
            print("=" * 60)
            
            choice = input("\nSelecciona una opción: ").strip()
            
            if choice == '0':
                logger.info("👋 Saliendo del bot...")
                break
            
            handled = False
            for opt in options:
                if choice == opt.number:
                    try:
                        logger.info(f"\n{opt.icon} Ejecutando: {opt.label}")
                        opt.handler(manager)
                        action = post_execution_menu(manager)
                        if action == 'exit':
                            return
                        elif action == 'restart':
                            manager.restart()
                    except KeyboardInterrupt:
                        logger.info("\n⚠️ Acción detenida por el usuario")
                    except Exception as e:
                        logger.error(f"❌ Error ejecutando opción {opt.number}: {e}")
                    handled = True
                    break
            if not handled and choice not in [opt.number for opt in options] + ['0']:
                logger.warning("⚠️  Opción no válida, intenta de nuevo")
    
    except KeyboardInterrupt:
        logger.info("\n⚠️ Bot detenido por el usuario (Ctrl+C)")
    except Exception as e:
        logger.error(f"\n❌ Error crítico: {e}")
        traceback.print_exc()
    finally:
        try:
            # Intento de cerrar recursos de manera segura
            pass
        except Exception:
            pass
        logger.info("\n👋 ¡Hasta pronto!")

if __name__ == "__main__":
    main()

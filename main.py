"""
Script principal del bot de criptomonedas.
Maneja el menú interactivo y la ejecución de tareas.
"""
import sys
import os
import time
import schedule
from bot_orchestrator import CryptoBotOrchestrator
from config.config import Config
from utils.logger import logger
from datetime import datetime

# Variable global para el bot
bot = None

def post_execution_menu():
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
        print("0. 👋 Salir")
        print("=" * 60)
        
        choice = input("\nSelecciona una opción: ").strip()
        
        if choice == '1':
            return 'menu'
        elif choice == '2':
            return 'restart'
        elif choice == '3':
            run_smart_wait_mode()
            return 'menu'  # Si sale del modo espera
        elif choice == '0':
            return 'exit'
        else:
            logger.warning("⚠️  Opción no válida, intenta de nuevo")

def run_complete_cycle():
    """
    Ejecuta el ciclo completo: análisis básico + mercados tradicionales + 
    análisis técnico + noticias + modo continuo.
    """
    logger.info("\n🌟 INICIANDO CICLO COMPLETO DE ANÁLISIS")
    logger.info("=" * 60)
    
    # 1. Análisis básico de crypto
    logger.info("\n📊 PASO 1/5: Análisis básico de criptomonedas...")
    bot.run_analysis_cycle(is_morning=False)
    
    # 2. Mercados tradicionales
    logger.info("\n📈 PASO 2/5: Análisis de mercados tradicionales...")
    bot.traditional_markets.run_traditional_markets_analysis()
    
    # 3. Análisis técnico
    logger.info("\n🎯 PASO 3/5: Análisis técnico con señales de trading...")
    capital = 100  # Capital por defecto (usuario solicitó $100)
    risk_percent = 30  # Riesgo por defecto (usuario solicitó 30%)
    bot.technical_analysis.run_technical_analysis(capital, risk_percent)
    
    # 4. Scraping de noticias (TradingView)
    logger.info("\n📰 PASO 4/5: Scraping de noticias TradingView...")
    bot.tradingview_news.process_and_publish()
    
    # 5. Modo continuo (ejecutar una vez, no infinito)
    logger.info("\n🔄 PASO 5/5: Monitoreo de pumps/dumps...")
    bot.price_monitor.run_monitoring_cycle_once()
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ CICLO COMPLETO FINALIZADO")
    logger.info("=" * 60)

def setup_scheduler():
    """Configura el programador de tareas"""
    logger.info("📅 Configurando programador de tareas...")
    
    def run_morning_analysis():
        logger.info("\n☀️ Ejecutando reporte matutino...")
        bot.run_analysis_cycle(is_morning=True)
    
    def run_regular_analysis():
        logger.info("\n🔄 Ejecutando reporte programado...")
        bot.run_analysis_cycle(is_morning=False)
    
    # Programar reporte matutino a las 6 AM
    schedule.every().day.at(Config.MORNING_POST_TIME).do(run_morning_analysis)
    logger.info(f"✅ Reporte matutino programado para las {Config.MORNING_POST_TIME}")
    
    # Programar reportes cada 2 horas
    schedule.every(Config.REPORT_INTERVAL_HOURS).hours.do(run_regular_analysis)
    logger.info(f"✅ Reportes programados cada {Config.REPORT_INTERVAL_HOURS} horas")
    
    logger.info("\n📋 Resumen de tareas programadas:")
    for job in schedule.get_jobs():
        logger.info(f"   - {job}")

def run_smart_wait_mode():
    """
    Ejecuta el modo de espera inteligente:
    - Cada 5 min: Monitoreo de pumps/dumps
    - Cada 8 min: Scraping de noticias TradingView
    - Cada 2 horas: Ciclo completo de análisis
    """
    logger.info("\n⏰ INICIANDO MODO ESPERA INTELIGENTE")
    logger.info("=" * 60)
    logger.info("🕒 Ciclo de monitoreo:     5 minutos")
    logger.info("📰 Ciclo de noticias:      8 minutos")
    logger.info("🌟 Ciclo completo:         2 horas")
    logger.info("🛑 Presiona Ctrl+C para detener")
    logger.info("=" * 60)
    
    last_monitor_time = 0
    last_news_time = 0
    last_full_cycle_time = time.time()  # Asumimos que acabamos de correr el ciclo completo si venimos de ahí
    
    # Intervalos en segundos
    MONITOR_INTERVAL = 5 * 60
    NEWS_INTERVAL = 8 * 60
    FULL_CYCLE_INTERVAL = 2 * 60 * 60
    
    try:
        while True:
            current_time = time.time()
            
            # 1. Monitoreo de Pumps/Dumps (Cada 5 min)
            if current_time - last_monitor_time >= MONITOR_INTERVAL:
                logger.info("\n🔄 [AUTO] Ejecutando monitoreo de pumps/dumps...")
                bot.price_monitor.run_monitoring_cycle_once()
                last_monitor_time = current_time
                
            # 2. Scraping de Noticias (Cada 8 min)
            if current_time - last_news_time >= NEWS_INTERVAL:
                logger.info("\n📰 [AUTO] Buscando noticias en TradingView...")
                bot.tradingview_news.process_and_publish()
                last_news_time = current_time
                
            # 3. Ciclo Completo (Cada 2 horas)
            if current_time - last_full_cycle_time >= FULL_CYCLE_INTERVAL:
                logger.info("\n🌟 [AUTO] Ejecutando ciclo completo programado...")
                run_complete_cycle()
                last_full_cycle_time = current_time
            
            # Mostrar status cada minuto
            time_since_monitor = int(current_time - last_monitor_time)
            time_since_news = int(current_time - last_news_time)
            time_since_cycle = int(current_time - last_full_cycle_time)
            
            monitor_wait = max(0, MONITOR_INTERVAL - time_since_monitor)
            news_wait = max(0, NEWS_INTERVAL - time_since_news)
            cycle_wait = max(0, FULL_CYCLE_INTERVAL - time_since_cycle)
            
            # Formato mm:ss
            monitor_str = f"{monitor_wait//60:02d}:{monitor_wait%60:02d}"
            news_str = f"{news_wait//60:02d}:{news_wait%60:02d}"
            cycle_str = f"{cycle_wait//3600:02d}:{(cycle_wait%3600)//60:02d}:{cycle_wait%60:02d}"
            
            print(f"\r⏳ Próximos: Monitoreo {monitor_str} | Noticias {news_str} | Ciclo {cycle_str}", end="")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("\n\n👋 Modo espera detenido por usuario")

def main():
    """Función principal del bot"""
    global bot
    
    try:
        # Banner de inicio
        logger.info("\n" + "=" * 60)
        logger.info("🚀 CRYPTO BOT - INICIANDO (V2 Enterprise)")
        logger.info("=" * 60)
        logger.info(f"📅 Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60 + "\n")
        
        # Validar configuración
        logger.info("🔍 Validando configuración...")
        try:
            Config.validate()
            logger.info("✅ Configuración válida\n")
        except ValueError as e:
            logger.error(f"❌ Error en configuración: {e}")
            logger.error("\n💡 Solución:")
            logger.error("   1. Copia el archivo .env.example a .env")
            logger.error("   2. Edita .env con tus credenciales")
            logger.error("   3. Completa todas las claves API requeridas")
            logger.error("   4. Revisa la documentación en README.md")
            sys.exit(1)
        
        # Crear instancia del bot
        bot = CryptoBotOrchestrator()
        
        # Menú principal mejorado
        while True:
            print("\n" + "=" * 60)
            print("💡 MENÚ PRINCIPAL - CRYPTO BOT V3")
            print("=" * 60)
            print("1. 🌟 Análisis Completo (Todo en un ciclo)")
            print("2. ⏰ Programar ejecuciones automáticas (cada 2h + 6 AM)")
            print("3. 🚀 Análisis Básico (solo crypto)")
            print("4. 📊 Abrir Dashboard Web")
            print("5. 🧹 Limpiar repositorio (archivos temporales)")
            print("6. 🗑️  Limpiar base de datos (CUIDADO!)")
            print("7. 📈 Análisis de Mercados Tradicionales (Stocks/Forex/Commodities)")
            print("8. 🎯 Análisis Técnico con Señales de Trading (RSI/MACD/Position Sizing)")
            print("9. 🔄 Modo Continuo (Análisis + Monitoreo de Pumps/Dumps cada 5 min)")
            print("10. 📰 Scraping de Noticias (CryptoPanic + Google News con filtro IA)")
            print("11. 🔁 Reiniciar Bot (útil para pruebas)")
            print("12. ⏰ Modo Espera Inteligente (Monitoreo + Noticias + Ciclo 2h)")
            print("0. 👋 Salir")
            print("=" * 60)
            
            choice = input("\nSelecciona una opción: ").strip()
            
            if choice == '0':
                logger.info("👋 Saliendo del bot...")
                break
            
            # Opción 1: Ciclo completo
            elif choice == '1':
                logger.info("\n🌟 Ejecutando ciclo completo...")
                run_complete_cycle()
                action = post_execution_menu()
                if action == 'exit':
                    break
                elif action == 'restart':
                    bot.cleanup()
                    bot = CryptoBotOrchestrator()
                # Si action == 'menu', continúa el loop
            
            # Opción 2: Programar
            elif choice == '2':
                setup_scheduler()
                logger.info("\n" + "=" * 60)
                logger.info("✅ BOT EN EJECUCIÓN")
                logger.info("=" * 60)
                logger.info("⏰ El bot ejecutará análisis automáticamente")
                logger.info("🛑 Presiona Ctrl+C para detener")
                logger.info("=" * 60 + "\n")
                
                try:
                    while True:
                        schedule.run_pending()
                        time.sleep(60)
                except KeyboardInterrupt:
                    logger.info("\n⚠️ Deteniendo programador...")
                    schedule.clear()
                    continue
            
            # Opción 3: Análisis básico
            elif choice == '3':
                logger.info("\n🚀 Ejecutando análisis básico...")
                bot.run_analysis_cycle(is_morning=False)
                action = post_execution_menu()
                if action == 'exit':
                    break
                elif action == 'restart':
                    bot.cleanup()
                    bot = CryptoBotOrchestrator()
            
            # Opción 4: Dashboard
            elif choice == '4':
                logger.info("\n📊 Iniciando Dashboard Web...")
                logger.info("=" * 60)
                logger.info("🌐 Dashboard disponible en: http://localhost:5000")
                logger.info("⚠️  Solo para uso local - No exponer a internet")
                logger.info("🛑 Presiona Ctrl+C para detener el dashboard")
                logger.info("=" * 60 + "\n")
                
                try:
                    import subprocess
                    subprocess.run([sys.executable, "dashboard/app.py"], cwd=os.getcwd())
                except KeyboardInterrupt:
                    logger.info("\n⚠️ Dashboard detenido")
                    continue
            
            # Opción 5: Limpiar repositorio
            elif choice == '5':
                logger.info("\n🧹 Limpiando repositorio...")
                confirm = input("⚠️  ¿Estás seguro? Esto eliminará archivos temporales (s/n): ").strip().lower()
                if confirm == 's':
                    try:
                        import subprocess
                        subprocess.run(
                            [sys.executable, "cleanup_repo.py"],
                            cwd=os.getcwd()
                        )
                        logger.info("✅ Limpieza completada")
                    except Exception as e:
                        logger.error(f"❌ Error en limpieza: {e}")
                else:
                    logger.info("❌ Limpieza cancelada")
            
            # Opción 6: Limpiar base de datos
            elif choice == '6':
                logger.info("\n🗑️  Limpiando base de datos...")
                confirm = input("⚠️  ¿ESTÁS SEGURO? Esto ELIMINARÁ TODOS los datos (s/n): ").strip().lower()
                if confirm == 's':
                    confirm2 = input("⚠️  Escribe 'ELIMINAR' para confirmar: ").strip()
                    if confirm2 == 'ELIMINAR':
                        try:
                            bot.db.clear_database()
                            logger.info("✅ Base de datos limpiada")
                        except Exception as e:
                            logger.error(f"❌ Error al limpiar BD: {e}")
                    else:
                        logger.info("❌ Limpieza cancelada")
                else:
                    logger.info("❌ Limpieza cancelada")
            
            # Opción 7: Mercados tradicionales
            elif choice == '7':
                logger.info("\n📈 Ejecutando análisis de mercados tradicionales...")
                bot.traditional_markets.run_traditional_markets_analysis()
                action = post_execution_menu()
                if action == 'exit':
                    break
                elif action == 'restart':
                    bot.cleanup()
                    bot = CryptoBotOrchestrator()
            
            # Opción 8: Análisis técnico
            elif choice == '8':
                logger.info("\n🎯 Ejecutando análisis técnico con señales de trading...")
                try:
                    capital_input = input("💰 Capital disponible en USD (default 1000): ").strip()
                    capital = float(capital_input) if capital_input else 1000
                    
                    risk_input = input("⚠️ Porcentaje de riesgo por operación (default 2%): ").strip()
                    # Remover el símbolo % si el usuario lo incluyó
                    risk_input = risk_input.replace('%', '')
                    risk_percent = float(risk_input) if risk_input else 2
                    
                    bot.technical_analysis.run_technical_analysis(capital, risk_percent)
                    action = post_execution_menu()
                    if action == 'exit':
                        break
                    elif action == 'restart':
                        bot.cleanup()
                        bot = CryptoBotOrchestrator()
                except ValueError as e:
                    logger.error(f"❌ Error en los valores ingresados: {e}")
            
            # Opción 9: Modo continuo
            elif choice == '9':
                logger.info("\n🔄 Iniciando modo continuo...")
                logger.info("🛑 Presiona Ctrl+C para detener")
                try:
                    bot.price_monitor.start_monitoring()
                except KeyboardInterrupt:
                    logger.info("\n⚠️ Deteniendo modo continuo...")
                    bot.price_monitor.stop_monitoring()
                    continue
            
            # Opción 10: Scraping de noticias TradingView
            elif choice == '10':
                logger.info("\n📰 Ejecutando scraping de noticias TradingView...")
                bot.tradingview_news.process_and_publish()
                action = post_execution_menu()
                if action == 'exit':
                    break
                elif action == 'restart':
                    bot.cleanup()
                    bot = CryptoBotOrchestrator()
            
            # Opción 11: Reiniciar bot
            elif choice == '11':
                logger.info("\n🔁 Reiniciando bot...")
                bot.cleanup()
                logger.info("🔄 Reiniciando servicios...")
                bot = CryptoBotOrchestrator()
                logger.info("✅ Bot reiniciado correctamente\n")
            
            # Opción 12: Modo Espera Inteligente
            elif choice == '12':
                run_smart_wait_mode()
            
            else:
                if choice not in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '0']:
                    logger.warning("⚠️  Opción no válida, intenta de nuevo")
    
    except KeyboardInterrupt:
        logger.info("\n⚠️ Bot detenido por el usuario (Ctrl+C)")
    except Exception as e:
        logger.error(f"\n❌ Error crítico: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if bot:
            bot.cleanup()
        logger.info("\n👋 ¡Hasta pronto!")

if __name__ == "__main__":
    main()

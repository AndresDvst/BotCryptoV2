"""
Script principal para ejecutar el bot de criptomonedas.
Programa las tareas para ejecutarse cada 2 horas y a las 6 AM.
"""
import os
os.environ["WDM_LOG_LEVEL"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import schedule
import time
import datetime
from bot_orchestrator import CryptoBotOrchestrator
from config.config import Config
from utils.logger import logger
import sys

# Crear directorio de logs si no existe
os.makedirs('logs', exist_ok=True)
os.makedirs('images', exist_ok=True)

def run_regular_analysis():
    """Ejecuta el análisis regular (cada 2 horas)"""
    logger.info("⏰ Ejecutando análisis regular...")
    bot.run_analysis_cycle(is_morning=False)

def run_morning_analysis():
    """Ejecuta el análisis matutino (6 AM)"""
    logger.info("☀️ Ejecutando análisis matutino...")
    bot.run_analysis_cycle(is_morning=True)

def setup_scheduler():
    """Configura el programador de tareas"""
    logger.info("📅 Configurando programador de tareas...")
    
    # Reporte matutino a las 6:00 AM
    schedule.every().day.at(Config.MORNING_POST_TIME).do(run_morning_analysis)
    logger.info(f"✅ Reporte matutino programado para las {Config.MORNING_POST_TIME}")
    
    # Reportes cada 2 horas
    schedule.every(Config.REPORT_INTERVAL_HOURS).hours.do(run_regular_analysis)
    logger.info(f"✅ Reportes programados cada {Config.REPORT_INTERVAL_HOURS} horas")
    
    logger.info("\n📋 Resumen de tareas programadas:")
    for job in schedule.jobs:
        logger.info(f"   - {job}")

def main():
    """Función principal"""
    try:
        logger.info("\n" + "=" * 60)
        logger.info("🚀 CRYPTO BOT - INICIANDO")
        logger.info("=" * 60)
        logger.info(
            f"📅 Fecha y hora: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        logger.info("=" * 60 + "\n")
        
        # Validar configuración antes de continuar
        logger.info("🔍 Validando configuración...")
        try:
            Config.validate()
            logger.info("✅ Configuración válida\n")
        except ValueError as e:
            logger.error(f"❌ Error de configuración: {e}")
            logger.error("\n💡 Solución:")
            logger.error("   1. Verifica que el archivo .env exista")
            logger.error("   2. Copia .env.example a .env si no existe")
            logger.error("   3. Completa todas las claves API requeridas")
            logger.error("   4. Revisa la documentación en README.md")
            sys.exit(1)
        
        # Crear instancia del bot
        global bot
        bot = CryptoBotOrchestrator()
        
        # Preguntar si se quiere ejecutar inmediatamente
        print("\n" + "=" * 60)
        print("💡 OPCIONES DE EJECUCIÓN")
        print("=" * 60)
        print("1. Ejecutar análisis ahora (una vez)")
        print("2. Programar ejecuciones automáticas (cada 2h + 6 AM)")
        print("3. Ambas (ejecutar ahora + programar)")
        print("=" * 60)
        
        choice = input("\nSelecciona una opción (1/2/3): ").strip()
        
        if choice in ['1', '3']:
            logger.info("\n🚀 Ejecutando análisis inmediato...")
            bot.run_analysis_cycle(is_morning=False)
            # Si es opción 3, esperar 2 minutos antes de iniciar el programador
            if choice == '3':
                logger.info("⏳ Esperando 2 minutos antes de iniciar el programador para evitar solapamientos...")
                time.sleep(30)
        
        if choice in ['2', '3']:
            # Configurar programador
            setup_scheduler()
            
            logger.info("\n" + "=" * 60)
            logger.info("✅ BOT EN EJECUCIÓN")
            logger.info("=" * 60)
            logger.info("El bot está ejecutándose en segundo plano.")
            
            # Mostrar próxima ejecución
            next_execution = (
                datetime.datetime.now()
                + datetime.timedelta(hours=Config.REPORT_INTERVAL_HOURS)
            )
            logger.info(
                f"⏰ Próxima ejecución: {next_execution.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            logger.info("Presiona Ctrl+C para detener el bot.")
            logger.info("=" * 60 + "\n")
            
            # Loop infinito para ejecutar tareas programadas
            while True:
                schedule.run_pending()
                time.sleep(60)  # Revisar cada minuto
        
        elif choice == '1':
            logger.info("\n✅ Análisis completado. Bot finalizado.")
        
        else:
            logger.error("❌ Opción inválida. Saliendo...")
    
    except KeyboardInterrupt:
        logger.info("\n\n⚠️ Bot detenido por el usuario (Ctrl+C)")
    except Exception as e:
        logger.error(f"\n❌ Error crítico: {e}")
    finally:
        # Limpiar recursos
        if 'bot' in globals():
            bot.cleanup()
        logger.info("\n👋 ¡Hasta pronto!")

if __name__ == "__main__":
    main()

"""
Sistema de logging con colores para facilitar el seguimiento del bot.
Los logs se muestran en la consola con colores para identificar rápidamente
el tipo de mensaje (info, éxito, advertencia, error).
"""
import logging
import colorlog
from datetime import datetime
import sys
import os

# Forzar UTF-8 en la consola de Windows
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    # Redirigir stdout y stderr a UTF-8
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

def setup_logger(name='CryptoBot'):
    """
    Configura y retorna un logger con colores.
    
    Args:
        name: Nombre del logger
        
    Returns:
        Logger configurado con colores
    """
    # Crear el logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Si ya tiene handlers, no agregar más
    if logger.handlers:
        return logger
    
    # Configurar el formato con colores
    formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(levelname)-8s%(reset)s - %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S',
        reset=True,
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    
    # Handler para la consola (con UTF-8 para soportar emojis)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler para archivo (sin colores, UTF-8)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)-8s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    # Asegurar que existe el directorio de logs
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    file_handler = logging.FileHandler(f'{log_dir}/bot_{datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger

# Logger global para usar en todo el proyecto
logger = setup_logger()
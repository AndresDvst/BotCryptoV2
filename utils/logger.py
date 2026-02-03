import logging
import sys
from datetime import datetime

from utils.security import sanitize_log_message

class ColoredFormatter(logging.Formatter):
    """Formateador con colores para terminal"""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


class SecretsRedactionFilter(logging.Filter):
    """Filtro de logging que redacciona secretos sensibles antes de escribir logs"""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            # Reemplazar el mensaje y los argumentos con versiones sanitizadas
            msg = str(record.getMessage())
            record.msg = sanitize_log_message(msg)
            if record.args:
                if isinstance(record.args, tuple):
                    record.args = tuple(sanitize_log_message(str(a)) for a in record.args)
                else:
                    record.args = sanitize_log_message(str(record.args))
        except Exception:
            # Si falla la sanitización, no bloquear el log
            pass
        return True

# Configurar logger
logger = logging.getLogger('CryptoBot')
logger.setLevel(logging.DEBUG)  # Mostrar TODO

# Limpiar handlers existentes para evitar duplicados si se recarga
if logger.hasHandlers():
    logger.handlers.clear()

# Handler para consola con colores
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
console_formatter = ColoredFormatter(
    '%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
console_handler.setFormatter(console_formatter)
console_handler.addFilter(SecretsRedactionFilter())

# Handler para archivo (sin colores)
file_handler = logging.FileHandler('crypto_bot.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter(
    '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)
file_handler.setFormatter(file_formatter)
file_handler.addFilter(SecretsRedactionFilter())

logger.addHandler(console_handler)
logger.addHandler(file_handler)
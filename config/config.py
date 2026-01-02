"""
Configuración centralizada del bot de criptomonedas.
Este archivo carga todas las variables de entorno y las hace disponibles.
"""
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

class Config:
    """Clase que contiene toda la configuración del bot"""
    
    # ========== BINANCE ==========
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
    BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET')
    
    # ========== BYBIT ==========
    BYBIT_API_KEY = os.getenv('BYBIT_API_KEY')
    BYBIT_API_SECRET = os.getenv('BYBIT_API_SECRET')
    
    # ========== TELEGRAM ==========
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    
    # ========== TWITTER ==========
    TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
    TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
    TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
    TWITTER_ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET')
    # Opcionales: credenciales para login con Selenium (no obligatorias)
    TWITTER_USERNAME = os.getenv('TWITTER_USERNAME')
    TWITTER_PASSWORD = os.getenv('TWITTER_PASSWORD')
    # Ejecutar Twitter en modo headless (sin ventana). Por defecto False (ver navegador)
    TWITTER_HEADLESS = os.getenv('TWITTER_HEADLESS', 'False').lower() in ('1', 'true', 'yes')
    # Ruta opcional para reutilizar un perfil de Chrome (útil para evitar challenges en login)
    CHROME_USER_DATA_DIR = os.getenv('CHROME_USER_DATA_DIR')
    
    # ========== GOOGLE GEMINI ==========
    GOOGLE_GEMINI_API_KEY = os.getenv('GOOGLE_GEMINI_API_KEY')
    
    # ========== CONFIGURACIÓN DEL BOT ==========
    MIN_CHANGE_PERCENT = float(os.getenv('MIN_CHANGE_PERCENT', '10'))
    MORNING_IMAGE_PATH = os.getenv('MORNING_IMAGE_PATH', './images/morning_report.png')
    REPORT_IMAGE_PATH = os.getenv('REPORT_IMAGE_PATH', './images/crypto_report.png')
    
    # ========== HORARIOS ==========
    MORNING_POST_TIME = "06:00"  # Hora del reporte matutino
    REPORT_INTERVAL_HOURS = 2     # Intervalo para reportes cada 2 horas
    
    @classmethod
    def validate(cls):
        """Valida que todas las configuraciones necesarias estén presentes"""
        required_vars = [
            'BINANCE_API_KEY', 'BINANCE_API_SECRET',
            'BYBIT_API_KEY', 'BYBIT_API_SECRET',
            'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID',
            'TWITTER_API_KEY', 'TWITTER_API_SECRET',
            'TWITTER_ACCESS_TOKEN', 'TWITTER_ACCESS_SECRET',
            'GOOGLE_GEMINI_API_KEY'
        ]
        
        missing = []
        for var in required_vars:
            if not getattr(cls, var):
                missing.append(var)
        
        if missing:
            raise ValueError(f"Faltan las siguientes variables de entorno: {', '.join(missing)}")
        
        return True
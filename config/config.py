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
    
    # ========== TELEGRAM ==========
    # Tokens para los 3 bots diferentes
    TELEGRAM_BOT_CRYPTO = os.getenv('TELEGRAM_BOT_CRYPTO')
    TELEGRAM_BOT_MARKETS = os.getenv('TELEGRAM_BOT_MARKETS')
    TELEGRAM_BOT_SIGNALS = os.getenv('TELEGRAM_BOT_SIGNALS')
    
    # Mantener compatibilidad temporal (usar Crypto como default)
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', TELEGRAM_BOT_CRYPTO)
    
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    TELEGRAM_CHAT_ID_CRYPTO = os.getenv('TELEGRAM_CHAT_ID_CRYPTO', TELEGRAM_CHAT_ID)
    TELEGRAM_CHAT_ID_MARKETS = os.getenv('TELEGRAM_CHAT_ID_MARKETS', TELEGRAM_CHAT_ID)
    TELEGRAM_CHAT_ID_SIGNALS = os.getenv('TELEGRAM_CHAT_ID_SIGNALS', TELEGRAM_CHAT_ID)

    # ========== TELEGRAM GRUPOS ==========
    TELEGRAM_GROUP_CRYPTO = os.getenv('TELEGRAM_GROUP_CRYPTO') or os.getenv('TELEGRAM_GRUPO_CapitalNewsCrypto')
    TELEGRAM_GROUP_MARKETS = os.getenv('TELEGRAM_GROUP_MARKETS') or os.getenv('TELEGRAM_GRUPO_CapitalNewsMarket')
    TELEGRAM_GROUP_SIGNALS = os.getenv('TELEGRAM_GROUP_SIGNALS') or os.getenv('TELEGRAM_GRUPO_CapitalNewsSignals')
    
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
    # Ruta del driver de Chrome (Forzada para evitar conflictos con variables de entorno antiguas)
    CHROMEDRIVER_PATH = r"I:\Proyectos\BotCryptoV2\utils\chrome-win64\chrome-win\chromedriver.exe"
    
    # ========== GOOGLE GEMINI ==========
    GOOGLE_GEMINI_API_KEY = os.getenv('GOOGLE_GEMINI_API_KEY')
    
    # ========== OPENAI ==========
    # Mapeo de la variable del usuario (GOOGLE_GPT_API_KEY) a OPENAI_API_KEY
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY') or os.getenv('GOOGLE_GPT_API_KEY')
    
    # ========== CONFIGURACIÓN DEL BOT ==========
    MIN_CHANGE_PERCENT = float(os.getenv('MIN_CHANGE_PERCENT', '10'))
    MORNING_IMAGE_PATH = os.getenv('MORNING_IMAGE_PATH', './images/morning_report.png')
    REPORT_IMAGE_PATH = os.getenv('REPORT_IMAGE_PATH', './images/crypto_report.png')
    
    # ========== HORARIOS Y RETRASOS ==========
    MORNING_POST_TIME = "06:00"  # Hora del reporte matutino
    REPORT_INTERVAL_HOURS = 2     # Intervalo para reportes cada 2 horas
    TWITTER_POST_DELAY = 10       # Segundos de espera entre tweets
    
    # ========== BASE DE DATOS ==========
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', os.getenv('DB_PASSWORD', '1234'))
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'crypto_bot')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
    DB_PASSWORD = MYSQL_PASSWORD

    @classmethod
    def validate(cls):
        """Valida que todas las configuraciones necesarias estén presentes"""
        required_vars = [
            'BINANCE_API_KEY', 'BINANCE_API_SECRET',
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

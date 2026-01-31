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
    
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))
    IMAGES_DIR = os.path.join(BASE_DIR, 'images')
    LOGS_DIR = os.path.join(BASE_DIR, 'logs')
    
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

    # ========== PUBLICACIÓN ==========
    STABLE_COINS = [
        os.getenv('STABLE_COIN_1', 'BTC/USDT'),
        os.getenv('STABLE_COIN_2', 'ETH/USDT'),
        os.getenv('STABLE_COIN_3', 'SOL/USDT'),
        os.getenv('STABLE_COIN_4', 'BNB/USDT'),
        os.getenv('STABLE_COIN_5', 'LTC/USDT'),
    ]
    
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
    # Ruta fija para reutilizar perfil de Chrome en Windows
    CHROME_USER_DATA_DIR = r'I:\Proyectos\BotCryptoV2\chrome_profile'
    try:
        os.makedirs(CHROME_USER_DATA_DIR, exist_ok=True)
    except Exception:
        pass
    _project_chrome_binary = os.path.join(BASE_DIR, 'utils', 'chrome-win64', 'chrome-win', 'chrome.exe') if os.name == 'nt' else None
    CHROME_BINARY_PATH = _project_chrome_binary if _project_chrome_binary and os.path.isfile(_project_chrome_binary) else os.getenv('CHROME_BINARY_PATH')
    # Driver portable (Windows/Linux/Docker/Headless)
    CHROMEDRIVER_PATH = os.getenv(
        'CHROMEDRIVER_PATH',
        os.path.join(
            BASE_DIR,
            'utils',
            'chromedriver.exe' if os.name == 'nt' else 'chromedriver'
        )
    )
    
    # ========== GOOGLE GEMINI ==========
    GOOGLE_GEMINI_API_KEY = os.getenv('GOOGLE_GEMINI_API_KEY')
    
    # ========== OPENAI ==========
    # Mapeo de la variable del usuario (GOOGLE_GPT_API_KEY) a OPENAI_API_KEY
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY') or os.getenv('GOOGLE_GPT_API_KEY')
    
    # ========== OPENROUTER ==========
    OPENROUTER_API_KEY = os.getenv('GOOGLE_OPENROUTER_API_KEY') or os.getenv('OPENROUTER_API_KEY')
    
    # ========== CONFIGURACIÓN DEL BOT ==========
    MIN_CHANGE_PERCENT = float(os.getenv('MIN_CHANGE_PERCENT', '10'))
    REPORT_2H_IMAGE_PATH = os.getenv('REPORT_2H_IMAGE_PATH', os.path.join(IMAGES_DIR, 'REPORTE 2H.png'))
    REPORT_24H_IMAGE_PATH = os.getenv('REPORT_24H_IMAGE_PATH', os.path.join(IMAGES_DIR, 'REPORTE 24H.png'))
    STOCKS_IMAGE_PATH = os.getenv('STOCKS_IMAGE_PATH', os.path.join(IMAGES_DIR, 'ACCIONES.png'))
    FOREX_IMAGE_PATH = os.getenv('FOREX_IMAGE_PATH', os.path.join(IMAGES_DIR, 'FOREX.png'))
    COMMODITIES_IMAGE_PATH = os.getenv('COMMODITIES_IMAGE_PATH', os.path.join(IMAGES_DIR, 'MINERALES.png'))
    SIGNALS_IMAGE_PATH = os.getenv('SIGNALS_IMAGE_PATH', os.path.join(IMAGES_DIR, 'SEÑALES.png'))
    MORNING_IMAGE_PATH = os.getenv('MORNING_IMAGE_PATH', REPORT_24H_IMAGE_PATH)
    REPORT_IMAGE_PATH = os.getenv('REPORT_IMAGE_PATH', REPORT_2H_IMAGE_PATH)
    
    # ========== HORARIOS Y RETRASOS ==========
    MORNING_POST_TIME = "06:00"  # Hora del reporte matutino
    REPORT_INTERVAL_HOURS = 2     # Intervalo para reportes cada 2 horas
    TWITTER_POST_DELAY = 10       # Segundos de espera entre tweets
    
    # ========== LISTAS MERCADOS TRADICIONALES ==========
    STOCK_SYMBOLS_DEFAULT = [
        'SPY', 'QQQ', 'DIA', 'IWM', 'VTI', 'EEM', 'XLF', 'XLK', 'XLE', 'XLV'
    ]
    STOCK_SYMBOLS_EXTENDED = [
        'AAPL','MSFT','AMZN','GOOGL','GOOG','META','NVDA','TSLA','JPM','BAC','WMT','UNH','XOM','CVX','COP','SLB','EOG','V','MA','GS',
        'MS','BLK','AXP','SCHW','C','WFC','JNJ','LLY','ABBV','PFE','MRK','BMY','TMO','DHR','PG','KO','PEP','COST','HD','LOW',
        'MCD','SBUX','NKE','DIS','NFLX','ADBE','CRM','ORCL','IBM','INTC','AMD','QCOM','TXN','AVGO','AMAT','LRCX','MU','CSCO','NOW','INTU',
        'ADP','UPS','FDX','CAT','DE','GE','HON','RTX','LMT','NOC',
        'ASML','SAP','SIEGY','NESN.SW','ROG.SW','NOVN.SW','AIR.PA','MC.PA','OR.PA','BN.PA','TTE','SHEL','BP','HSBC','UL','GSK','AZN','RIO','BHP','ENEL.MI',
        'ENI','SAN.PA','BBVA','ING','DB','VOW3.DE','BMW.DE','MBG.DE','BAYN.DE','ALV.DE','IFX.DE','ADS.DE','CRH','FER.MC','IBE.MC',
        'TM','HMC','SONY','NTTYY','MUFG','SMFG','MFG','TOYOF','KDDIY','SBAC','KEY','TAK','FUJHY','CAJ','RYAAY','NMR','IX','SNE','MTU','DCM',
        'BHP','RIO','CSL','WES','WOW','VALE','PBR','ITUB','BBD','BSBR','AMX','WALMEX.MX','FEMSAUBD.MX','EC','YPF'
    ]
    FOREX_PAIRS = [
        'EURUSD=X','GBPUSD=X','USDJPY=X','AUDUSD=X','USDCAD=X','USDCHF=X','NZDUSD=X','EURGBP=X','EURJPY=X','GBPJPY=X',
        'USDMXN=X','USDBRL=X','GBPCHF=X','AUDJPY=X','AUDNZD=X','CADJPY=X','CHFJPY=X','EURAUD=X','EURCAD=X','GBPAUD=X','NZDJPY=X','USDTRY=X'
    ]
    COMMODITIES = {
        'GC=F': 'Oro',
        'SI=F': 'Plata',
        'CL=F': 'Crudo WTI',
        'BZ=F': 'Brent',
        'RB=F': 'Gasolina',
        'HO=F': 'Petróleo para calefacción'
    }
    
    # ========== BASE DE DATOS ==========
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', os.getenv('DB_PASSWORD', '1234'))
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'crypto_bot')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
    DB_PASSWORD = MYSQL_PASSWORD
    
    # ========== TELEGRAM (Estructura consolidada con compatibilidad) ==========
    TELEGRAM_BOTS = {
        'crypto': {
            'token': TELEGRAM_BOT_CRYPTO or TELEGRAM_BOT_TOKEN,
            'chat_id': TELEGRAM_CHAT_ID_CRYPTO or TELEGRAM_CHAT_ID,
            'group': TELEGRAM_GROUP_CRYPTO
        },
        'markets': {
            'token': TELEGRAM_BOT_MARKETS or TELEGRAM_BOT_TOKEN,
            'chat_id': TELEGRAM_CHAT_ID_MARKETS or TELEGRAM_CHAT_ID,
            'group': TELEGRAM_GROUP_MARKETS
        },
        'signals': {
            'token': TELEGRAM_BOT_SIGNALS or TELEGRAM_BOT_TOKEN,
            'chat_id': TELEGRAM_CHAT_ID_SIGNALS or TELEGRAM_CHAT_ID,
            'group': TELEGRAM_GROUP_SIGNALS
        }
    }

    @classmethod
    def validate(cls):
        """
        Validación avanzada de configuración:
        1. Validar API keys obligatorias
        2. Validar paths de imágenes (warning si faltan)
        3. Validar ChromeDriver si Twitter está habilitado
        4. Validar permisos de escritura en directorios
        """
        required_vars = [
            'BINANCE_API_KEY', 'BINANCE_API_SECRET',
            'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID',
            'TWITTER_API_KEY', 'TWITTER_API_SECRET',
            'TWITTER_ACCESS_TOKEN', 'TWITTER_ACCESS_SECRET',
            'GOOGLE_GEMINI_API_KEY'
        ]

        missing = [var for var in required_vars if not getattr(cls, var)]
        if missing:
            raise ValueError(f"Faltan las siguientes variables de entorno: {', '.join(missing)}")

        image_paths = [
            cls.REPORT_2H_IMAGE_PATH, cls.REPORT_24H_IMAGE_PATH,
            cls.STOCKS_IMAGE_PATH, cls.FOREX_IMAGE_PATH,
            cls.COMMODITIES_IMAGE_PATH, cls.SIGNALS_IMAGE_PATH
        ]
        for p in image_paths:
            if not os.path.exists(p):
                try:
                    logger = __import__('utils.logger', fromlist=['logger']).logger
                    logger.warning(f"⚠️ Imagen no encontrada: {p}")
                except Exception:
                    pass

        twitter_active = any([cls.TWITTER_USERNAME, cls.TWITTER_PASSWORD, cls.TWITTER_API_KEY, cls.TWITTER_ACCESS_TOKEN])
        if twitter_active:
            if not os.path.exists(cls.CHROMEDRIVER_PATH):
                raise FileNotFoundError(f"No se encontró ChromeDriver en: {cls.CHROMEDRIVER_PATH}")

        for d in [cls.BASE_DIR, cls.IMAGES_DIR, cls.LOGS_DIR]:
            try:
                os.makedirs(d, exist_ok=True)
            except Exception:
                pass
            if not os.access(d, os.W_OK):
                raise PermissionError(f"Sin permisos de escritura en: {d}")

        return True

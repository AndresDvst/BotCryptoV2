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
    
    # ========== DETECCIÓN DE ENTORNO (Windows/Linux/Docker) ==========
    IS_DOCKER = os.getenv('DOCKER_ENV', 'false').lower() in ('1', 'true', 'yes') or os.path.exists('/.dockerenv')
    IS_LINUX = os.name != 'nt'
    IS_WINDOWS = os.name == 'nt'
    
    # Helper para detectar rutas de Windows (ignorarlas en Linux)
    @staticmethod
    def _is_windows_path(path: str) -> bool:
        """Detecta si una ruta es de Windows (ej: I:\, C:\, etc.)"""
        if not path:
            return False
        return ':\\' in path or path.startswith('\\\\')
    
    # Ruta para perfil de Chrome (sesión persistente)
    # En Linux/Docker: ignorar rutas de Windows del .env
    _env_chrome_user_data = os.getenv('CHROME_USER_DATA_DIR', '')
    if IS_DOCKER:
        CHROME_USER_DATA_DIR = '/app/chrome_profile'
    elif IS_LINUX:
        # Si el .env tiene ruta de Windows, ignorarla
        if _is_windows_path.__func__(_env_chrome_user_data):
            CHROME_USER_DATA_DIR = os.path.join(BASE_DIR, 'chrome_profile')
        else:
            CHROME_USER_DATA_DIR = _env_chrome_user_data or os.path.join(BASE_DIR, 'chrome_profile')
    else:
        # Windows: usar del .env o default
        CHROME_USER_DATA_DIR = _env_chrome_user_data or os.path.join(BASE_DIR, 'chrome_profile')
    
    try:
        os.makedirs(CHROME_USER_DATA_DIR, exist_ok=True)
    except Exception:
        pass
    
    # Binario de Chrome
        _env_chrome_binary = os.getenv('CHROME_BINARY_PATH', '')
        if IS_DOCKER or IS_LINUX:
            # En Docker/Linux: usar el enlace simbólico estándar
            CHROME_BINARY_PATH = '/usr/bin/google-chrome'
        else:
            # En Windows: usar Chrome portable del proyecto
            _project_chrome_binary = os.path.join(BASE_DIR, 'utils', 'chrome-win64', 'chrome-win', 'chrome.exe')
            CHROME_BINARY_PATH = _env_chrome_binary or (_project_chrome_binary if os.path.isfile(_project_chrome_binary) else None)
    
    # Driver de Chrome
    _env_chromedriver = os.getenv('CHROMEDRIVER_PATH', '')
    if IS_DOCKER or IS_LINUX:
        # En Linux/Docker: ignorar rutas de Windows del .env
        if _is_windows_path.__func__(_env_chromedriver):
            CHROMEDRIVER_PATH = '/usr/bin/chromedriver'
        else:
            CHROMEDRIVER_PATH = _env_chromedriver or '/usr/bin/chromedriver'
    else:
        # Windows: usar del .env o default
        CHROMEDRIVER_PATH = _env_chromedriver or os.path.join(BASE_DIR, 'utils', 'chromedriver.exe')
    
    # ========== GOOGLE GEMINI ==========
    GOOGLE_GEMINI_API_KEY = os.getenv('GOOGLE_GEMINI_API_KEY')
    
    # ========== TWELVE DATA ==========
    TWELVEDATA_API_KEY = os.getenv('TWELVEDATA_API_KEY')
    
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
    
    # ========== TWELVE DATA SYMBOLS (DIFERENTES A YAHOO FINANCE) ==========
    # Twelve Data usa formato diferente para forex y commodities
    # NOTA: Algunos pares exóticos (USD/MXN, USD/BRL, USD/TRY) pueden no estar en plan gratuito
    FOREX_PAIRS_TWELVEDATA = [
        'EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD', 'USD/CAD', 'USD/CHF', 'NZD/USD',
        'EUR/GBP', 'EUR/JPY', 'GBP/JPY', 'GBP/CHF', 'AUD/JPY',
        'AUD/NZD', 'CAD/JPY', 'CHF/JPY', 'EUR/AUD', 'EUR/CAD', 'GBP/AUD', 'NZD/JPY'
    ]
    
    # Mapeo Yahoo Finance -> Twelve Data para forex
    # Pares exóticos mapeados a None (se omitirán en análisis Twelve Data)
    FOREX_YAHOO_TO_TWELVE = {
        'EURUSD=X': 'EUR/USD', 'GBPUSD=X': 'GBP/USD', 'USDJPY=X': 'USD/JPY',
        'AUDUSD=X': 'AUD/USD', 'USDCAD=X': 'USD/CAD', 'USDCHF=X': 'USD/CHF',
        'NZDUSD=X': 'NZD/USD', 'EURGBP=X': 'EUR/GBP', 'EURJPY=X': 'EUR/JPY',
        'GBPJPY=X': 'GBP/JPY', 'GBPCHF=X': 'GBP/CHF', 'AUDJPY=X': 'AUD/JPY', 
        'AUDNZD=X': 'AUD/NZD', 'CADJPY=X': 'CAD/JPY', 'CHFJPY=X': 'CHF/JPY', 
        'EURAUD=X': 'EUR/AUD', 'EURCAD=X': 'EUR/CAD', 'GBPAUD=X': 'GBP/AUD', 
        'NZDJPY=X': 'NZD/JPY',
        # Pares exóticos no disponibles en Twelve Data free - usar ETFs como proxy
        'USDMXN=X': None,  # No disponible - omitir
        'USDBRL=X': None,  # No disponible - omitir
        'USDTRY=X': None,  # No disponible - omitir
    }
    
    COMMODITIES_TWELVEDATA = {
        # ETFs de Commodities que funcionan con Twelve Data plan gratuito
        'GLD': 'Oro ETF (SPDR Gold)',
        'SLV': 'Plata ETF (iShares Silver)',
        'USO': 'Crudo WTI ETF',
        'UNG': 'Gas Natural ETF',
        'CPER': 'Cobre ETF'
    }
    
    # Mapeo Yahoo Finance -> Twelve Data para commodities
    # Usar ETFs porque los símbolos forex de commodities (XAU/USD) no están en plan gratuito
    COMMODITIES_YAHOO_TO_TWELVE = {
        'GC=F': 'GLD',   # Oro -> ETF de Oro
        'SI=F': 'SLV',   # Plata -> ETF de Plata
        'CL=F': 'USO',   # Crudo WTI -> ETF de Crudo
        'BZ=F': 'USO',   # Brent -> también usar ETF de Crudo
        'NG=F': 'UNG',   # Gas Natural -> ETF de Gas
        'HG=F': 'CPER',  # Cobre -> ETF de Cobre
    }
    
    # ========== BONOS MUNDIALES ==========
    BONDS = {
        # Bonos de EE.UU.
        '^TNX': {'name': 'US 10Y Treasury', 'country': 'USA', 'type': 'government'},
        '^TYX': {'name': 'US 30Y Treasury', 'country': 'USA', 'type': 'government'},
        '^FVX': {'name': 'US 5Y Treasury', 'country': 'USA', 'type': 'government'},
        '^IRX': {'name': 'US 13W Treasury', 'country': 'USA', 'type': 'government'},
        # ETFs de Bonos
        'TLT': {'name': 'iShares 20+ Year Treasury', 'country': 'USA', 'type': 'etf'},
        'IEF': {'name': 'iShares 7-10 Year Treasury', 'country': 'USA', 'type': 'etf'},
        'SHY': {'name': 'iShares 1-3 Year Treasury', 'country': 'USA', 'type': 'etf'},
        'LQD': {'name': 'iShares Investment Grade Corp Bond', 'country': 'USA', 'type': 'etf'},
        'HYG': {'name': 'iShares High Yield Corp Bond', 'country': 'USA', 'type': 'etf'},
        'EMB': {'name': 'iShares JP Morgan Emerging Markets Bond', 'country': 'Emerging', 'type': 'etf'},
        'AGG': {'name': 'iShares Core US Aggregate Bond', 'country': 'USA', 'type': 'etf'},
        'BND': {'name': 'Vanguard Total Bond Market', 'country': 'USA', 'type': 'etf'},
        # Bonos Internacionales
        'EXX5.DE': {'name': 'iShares German Govt Bond (BUND proxy)', 'country': 'Germany', 'type': 'etf'},
        'IGOV': {'name': 'iShares Intl Treasury Bond', 'country': 'International', 'type': 'etf'},
    }
    
    # ========== HORARIOS DE MERCADOS MUNDIALES ==========
    # Formato: {'open': 'HH:MM', 'close': 'HH:MM', 'timezone': 'UTC offset', 'name': 'nombre'}
    MARKET_HOURS = {
        'NYSE': {
            'name': 'New York Stock Exchange',
            'open': '09:30', 'close': '16:00',
            'timezone': 'America/New_York',
            'utc_offset': -5,
            'weekend_closed': True,
            'symbols_file': 'STOCK_SYMBOLS_EXTENDED'
        },
        'NASDAQ': {
            'name': 'NASDAQ',
            'open': '09:30', 'close': '16:00',
            'timezone': 'America/New_York',
            'utc_offset': -5,
            'weekend_closed': True,
            'symbols_file': 'STOCK_SYMBOLS_EXTENDED'
        },
        'LSE': {
            'name': 'London Stock Exchange',
            'open': '08:00', 'close': '16:30',
            'timezone': 'Europe/London',
            'utc_offset': 0,
            'weekend_closed': True
        },
        'TOKYO': {
            'name': 'Tokyo Stock Exchange',
            'open': '09:00', 'close': '15:00',
            'timezone': 'Asia/Tokyo',
            'utc_offset': 9,
            'weekend_closed': True
        },
        'FRANKFURT': {
            'name': 'Frankfurt Stock Exchange (Xetra)',
            'open': '09:00', 'close': '17:30',
            'timezone': 'Europe/Berlin',
            'utc_offset': 1,
            'weekend_closed': True
        },
        'SHANGHAI': {
            'name': 'Shanghai Stock Exchange',
            'open': '09:30', 'close': '15:00',
            'timezone': 'Asia/Shanghai',
            'utc_offset': 8,
            'weekend_closed': True
        },
        'HONG_KONG': {
            'name': 'Hong Kong Stock Exchange',
            'open': '09:30', 'close': '16:00',
            'timezone': 'Asia/Hong_Kong',
            'utc_offset': 8,
            'weekend_closed': True
        },
        'FOREX': {
            'name': 'Forex Market',
            'open': '00:00', 'close': '23:59',  # 24/5
            'timezone': 'UTC',
            'utc_offset': 0,
            'weekend_closed': True,  # Cierra viernes 17:00 EST hasta domingo 17:00 EST
            'note': 'Abierto 24h de lunes a viernes'
        },
        'CRYPTO': {
            'name': 'Cryptocurrency Markets',
            'open': '00:00', 'close': '23:59',
            'timezone': 'UTC',
            'utc_offset': 0,
            'weekend_closed': False,  # 24/7
            'note': 'Abierto 24/7'
        },
        'CME': {
            'name': 'CME (Commodities)',
            'open': '17:00', 'close': '16:00',  # Domingo 17:00 a Viernes 16:00
            'timezone': 'America/Chicago',
            'utc_offset': -6,
            'weekend_closed': True,
            'note': 'Futuros casi 24h L-V'
        }
    }
    
    # ========== CONFIGURACIÓN DE CAPITAL Y RIESGO ==========
    DEFAULT_CAPITAL = float(os.getenv('DEFAULT_CAPITAL', '20'))  # $20 por defecto
    DEFAULT_RISK_PERCENT = float(os.getenv('DEFAULT_RISK_PERCENT', '25'))  # 25% de riesgo
    
    # ========== BASE DE DATOS ==========
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    # SEGURIDAD: No usar contraseña por defecto - debe configurarse en .env
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD') or os.getenv('DB_PASSWORD')
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

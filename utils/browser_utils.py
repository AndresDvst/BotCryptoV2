import os
import sys
import subprocess
import re
import tempfile
import shutil
from typing import Optional, Tuple
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from config.config import Config
from utils.logger import logger

def get_major_version(path: str) -> Tuple[Optional[int], str]:
    """Obtiene la versión mayor de un ejecutable (Chrome o Driver)"""
    try:
        # En Windows a veces --version no funciona bien con algunos exes, pero intentamos
        result = subprocess.run([path, '--version'], capture_output=True, text=True, check=False)
        text = (result.stdout or '') + (result.stderr or '')
        # Patrón típico: "Google Chrome 114.0.5735.90" o "ChromeDriver 114.0.5735.90"
        m = re.search(r'(\d+)\.', text)
        if m:
            return int(m.group(1)), text.strip()
    except Exception:
        pass
    
    # Fallback para intentar leer propiedades si es windows (mas complejo, skip por ahora)
    return None, ""

class BrowserManager:
    """
    Gestor centralizado para la inicialización del navegador Chrome.
    Asegura el uso de rutas configuradas y perfiles persistentes.
    """

    @staticmethod
    def get_driver(headless: bool = False) -> Optional[webdriver.Chrome]:
        """
        Inicializa y retorna una instancia de Chrome Driver configurada.
        """
        try:
            options = Options()
            
            # --- Detectar si estamos en Docker/Linux ---
            is_docker = os.path.exists('/.dockerenv') or os.environ.get('IS_DOCKER', '').lower() == 'true'
            is_linux = sys.platform.startswith('linux')
            
            # --- Configuración Base ---
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-software-rasterizer')
            
            # --- Opciones adicionales para Docker/Linux ---
            if is_docker or is_linux:
                options.add_argument('--disable-extensions')
                options.add_argument('--disable-background-networking')
                options.add_argument('--disable-default-apps')
                options.add_argument('--disable-sync')
                options.add_argument('--disable-translate')
                options.add_argument('--no-first-run')
                options.add_argument('--no-default-browser-check')
                options.add_argument('--disable-crash-reporter')
                options.add_argument('--disable-infobars')
                options.add_argument('--single-process')  # Importante para Docker
                options.add_argument('--window-size=1920,1080')
                # Remote debugging solo si no estamos en headless
                if not headless:
                    options.add_argument('--remote-debugging-port=9222')
            else:
                options.add_argument('--remote-debugging-port=9222')
            
            # Headless según argumento o Config, pero el argumento tiene precedencia si es True
            config_headless = getattr(Config, 'TWITTER_HEADLESS', False)
            if headless or config_headless:
                options.add_argument('--headless=new')
            else:
                options.add_argument('--start-maximized')

            # --- Flags de Estabilidad y Anti-Detección Básica ---
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # --- Perfil de Usuario ---
            profile_root = getattr(Config, 'CHROME_USER_DATA_DIR', None)
            if not profile_root:
                # Fallback seguro si no está definido
                profile_root = os.path.join(os.getcwd(), 'chrome_profile')
            
            # Asegurar que la ruta es absoluta
            profile_root = os.path.abspath(profile_root)
            
            # En Docker/Linux, verificar si el perfil es de Windows (incompatible)
            # y crear uno nuevo si es necesario
            if is_docker or is_linux:
                local_state_file = os.path.join(profile_root, 'Local State')
                if os.path.exists(local_state_file):
                    try:
                        with open(local_state_file, 'r') as f:
                            content = f.read()
                            # Si contiene rutas de Windows, es un perfil incompatible
                            if 'C:\\\\' in content or 'C:/' in content or '\\\\Users\\\\' in content:
                                logger.warning("⚠️ Perfil de Chrome de Windows detectado en Linux. Creando perfil limpio...")
                                backup_path = profile_root + '_windows_backup'
                                if os.path.exists(backup_path):
                                    shutil.rmtree(backup_path, ignore_errors=True)
                                shutil.move(profile_root, backup_path)
                                os.makedirs(profile_root, exist_ok=True)
                                logger.info("✅ Perfil de Chrome limpio creado")
                    except Exception as e:
                        logger.warning(f"⚠️ Error verificando perfil de Chrome: {e}")
                        # Si hay error, intentar usar perfil temporal
                        profile_root = tempfile.mkdtemp(prefix='chrome_profile_')
                        logger.info(f"📁 Usando perfil temporal: {profile_root}")
            
            if not os.path.exists(profile_root):
                try:
                    os.makedirs(profile_root, exist_ok=True)
                except Exception:
                    pass
            
            options.add_argument(f'--user-data-dir={profile_root}')
            logger.info(f"🔑 Usando perfil de Chrome: {profile_root}")

            # --- Binario de Chrome ---
            chrome_binary = getattr(Config, 'CHROME_BINARY_PATH', None)
            if chrome_binary and os.path.isfile(chrome_binary):
                options.binary_location = chrome_binary
                logger.info(f"🔍 Usando binario Chrome: {chrome_binary}")
            else:
                logger.warning("⚠️ CHROME_BINARY_PATH no definido o no encontrado. Se usará el del sistema.")

            # --- Driver ---
            driver_path = getattr(Config, 'CHROMEDRIVER_PATH', None) or os.getenv('CHROMEDRIVER_PATH')
            
            if driver_path and os.path.isfile(driver_path):
                logger.info(f"🔧 Usando chromedriver desde CONFIG: {driver_path}")
            else:
                logger.warning("⚠️ CHROMEDRIVER_PATH no válido. Intentando descargar con webdriver-manager...")
                try:
                    driver_path = ChromeDriverManager().install()
                    logger.info(f"🔧 Driver descargado en: {driver_path}")
                except Exception as e:
                    logger.error(f"❌ Error descargando driver: {e}")
                    return None

            # --- Servicio ---
            # Suprimir logs basura del driver
            log_path = os.devnull
            service = Service(driver_path, log_path=log_path)
            
            if sys.platform == 'win32':
                # Ocultar ventana de consola del driver
                try:
                    service.creation_flags = subprocess.CREATE_NO_WINDOW
                except Exception:
                    pass

            driver = webdriver.Chrome(service=service, options=options)
            return driver

        except Exception as e:
            logger.error(f"❌ Error CRÍTICO al inicializar Chrome Driver: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

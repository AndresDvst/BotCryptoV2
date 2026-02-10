import os
import sys
import shutil
import time
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from utils.logger import logger

class BrowserManager:
    """
    Gestor simplificado y robusto para VPS Azure (Ubuntu).
    Permite modo Headless (automático) y Gráfico (manual).
    """

    @staticmethod
    def get_driver(headless: bool = True) -> Optional[webdriver.Chrome]:
        """
        Inicializa Chrome.
        Si headless=True -> Modo servidor (invisible, estable).
        Si headless=False -> Modo ventana (visible, requiere NoMachine).
        """
        try:
            # 1. Limpieza preventiva de bloqueos (SingletonLock)
            profile_path = "/home/AndresDvst/BotCryptoV2/chrome_profile"
            lock_file = os.path.join(profile_path, "SingletonLock")
            if os.path.exists(lock_file):
                try:
                    os.remove(lock_file)
                    logger.info("🧹 SingletonLock eliminado correctamente.")
                except Exception as e:
                    logger.warning(f"⚠️ No se pudo borrar SingletonLock: {e}")

            # 2. Configurar Opciones
            options = Options()
            
            # --- RUTAS HARDCODED ---
            options.binary_location = "/opt/google/chrome/google-chrome"
            driver_path = "/usr/bin/chromedriver"

            # --- BANDERAS BASES ---
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--remote-debugging-port=9222')
            
            # --- LÓGICA DE VISIBILIDAD ---
            if headless:
                logger.info("👻 Iniciando Chrome en modo HEADLESS (Oculto)")
                options.add_argument('--headless=new')
            else:
                logger.info("📺 Iniciando Chrome en modo GUI (Visible)")
                options.add_argument('--start-maximized')
                # Importante: Si estás por SSH puro, esto fallará. 
                # Debes configurar el DISPLAY si no lo detecta solo.
                if not os.environ.get('DISPLAY'):
                    os.environ['DISPLAY'] = ':0' 

            # --- PERFIL DE USUARIO ---
            options.add_argument(f'--user-data-dir={profile_path}')

            # --- EXTRAS ANTIDETECCIÓN ---
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

            # 3. Inicializar Servicio
            service = Service(executable_path=driver_path, log_path="chromedriver.log", verbose=True)
            
            driver = webdriver.Chrome(service=service, options=options)

            # 4. Parche CDP para Twitter
            try:
                driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                    "source": """
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        });
                    """
                })
            except Exception:
                pass

            return driver

        except Exception as e:
            logger.error(f"❌ Error al inicializar Chrome Driver: {e}")
            return None


    @staticmethod
    def open_manual_login(*args, **kwargs):
        """
        Abre el navegador en modo gráfico para que el usuario se loguee manualmente.
        """
        logger.info("🔵 Abriendo navegador para inicio de sesión manual...")
        logger.info("⚠️ NOTA: Debes estar viendo el escritorio remoto (NoMachine) para ver la ventana.")
        
        # AQUÍ ESTÁ LA CLAVE: Pedimos headless=False
        driver = BrowserManager.get_driver(headless=False)
        
        if not driver:
            logger.error("❌ No se pudo abrir el navegador. Verifica que estás en un entorno gráfico.")
            return

        try:
            logger.info("🌐 Navegando a Twitter Login...")
            driver.get("https://twitter.com/i/flow/login")
            
            print("\n" + "="*50)
            print("   🟢 EL NAVEGADOR DEBERÍA ESTAR ABIERTO AHORA")
            print("   1. Busca la ventana de Chrome en tu escritorio remoto.")
            print("   2. Inicia sesión manualmente en Twitter.")
            print("   3. Cuando termines y veas tu timeline, vuelve aquí.")
            print("="*50 + "\n")
            
            # Usamos input para pausar el script hasta que tú digas
            input("⌨️ Presiona ENTER aquí cuando hayas terminado de loguearte...")
            
            logger.info("💾 Guardando cookies y cerrando...")
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"❌ Error durante el proceso manual: {e}")
        finally:
            if driver:
                driver.quit()
                logger.info("✅ Navegador cerrado.")
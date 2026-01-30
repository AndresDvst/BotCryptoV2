"""
Servicio para publicar en Twitter/X usando automatización de navegador.
Simula el comportamiento de un usuario real para publicar tweets.
"""
import subprocess
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time
import random
from config.config import Config
from utils.logger import logger
import time
import sys
import os
from datetime import datetime
import json
import hashlib

class TwitterService:
    """Servicio para publicar en Twitter usando Selenium"""
    
    def __init__(self):
        """Inicializa el servicio de Twitter"""
        self.username = None  # Se configurará después
        self.password = None  # Se configurará después
        self.driver = None
        logger.info("✅ Servicio de Twitter inicializado")
    
    def _init_driver(self):
        """Inicializa el driver de Chrome"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--remote-debugging-port=9222')
            # Configuración de visibilidad: usar headless según configuración
            if getattr(Config, 'TWITTER_HEADLESS', False):
                # Selenium 4+ recomienda '--headless=new' en algunos entornos
                chrome_options.add_argument('--headless=new')

            # Flags para reducir mensajes de media y estabilizar ejecución en entornos automatizados
            chrome_options.add_argument('--log-level=3')
            chrome_options.add_argument('--silent')
            chrome_options.add_argument('--disable-logging')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-gpu-compositing')
            chrome_options.add_argument('--mute-audio')
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument('--disable-accelerated-video-decode')
            chrome_options.add_argument('--disable-accelerated-2d-canvas')
            chrome_options.add_argument('--disable-accelerated-jpeg-decoding')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            chrome_options.add_argument('--disable-features=AudioServiceOutOfProcess')
            chrome_options.add_argument('--disable-dev-tools')
            chrome_options.add_argument('--disable-breakpad')
            chrome_options.add_argument('--disable-component-update')
            chrome_options.add_argument('--disable-background-networking')
            chrome_options.add_argument('--disable-sync')
            chrome_options.add_argument('--metrics-recording-only')
            chrome_options.add_argument('--disable-default-apps')
            chrome_options.add_argument('--no-first-run')
            chrome_options.add_argument('--disable-extensions')


            # Configurar perfil de Chrome persistente para mantener sesión de Twitter
            user_data_dir = getattr(Config, 'CHROME_USER_DATA_DIR', None)
            
            # Si no hay configuración, crear perfil automático en el proyecto
            if not user_data_dir:
                user_data_dir = os.path.join(os.getcwd(), 'chrome_profile')
                # Crear directorio si no existe
                os.makedirs(user_data_dir, exist_ok=True)
                logger.info(f"📁 Creando perfil de Chrome automático: {user_data_dir}")
            
            # Usar el perfil (existente o nuevo)
            if os.path.exists(user_data_dir):
                chrome_options.add_argument(f'--user-data-dir={user_data_dir}')
                chrome_options.add_argument('--profile-directory=Default')
                logger.info(f"🔑 Usando perfil de Chrome persistente: {user_data_dir}")
            else:
                logger.warning(f"⚠️ No se pudo crear perfil de Chrome: {user_data_dir}")


            # Simular un navegador real y abrir ventana maximizada para ver acciones
            chrome_options.add_argument('--start-maximized')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            # Preparar archivo de log para chromedriver - usar os.devnull para eliminar spam
            try:
                os.makedirs('utils', exist_ok=True)
            except Exception:
                pass

            # En Windows, redirigir stdout/stderr a NUL para suprimir mensajes de GPU/GCM
            devnull = None
            if sys.platform == 'win32':
                devnull = open(os.devnull, 'w')

            # Priorizar driver desde configuración
            driver_path = Config.CHROMEDRIVER_PATH
            if driver_path and os.path.isfile(driver_path):
                 logger.info(f"🔧 Usando chromedriver desde CONFIG: {driver_path}")
            else:
                 driver_path = os.getenv('CHROMEDRIVER_PATH')
            
            if driver_path:
                if not os.path.isfile(driver_path):
                    logger.error(f"❌ CHROMEDRIVER_PATH establecido pero no existe: {driver_path}")
                    if devnull:
                        devnull.close()
                    return False
                logger.info(f"🔧 Usando chromedriver: {driver_path}")
                # Crear servicio silenciando completamente stdout/stderr
                service = Service(driver_path, log_path=os.devnull)
                service.stdout = subprocess.DEVNULL
                service.stderr = subprocess.DEVNULL
                if sys.platform == 'win32':
                    try:
                        service.creationflags = subprocess.CREATE_NO_WINDOW
                    except Exception:
                        pass
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                # Intentar obtener la ruta del driver desde webdriver-manager
                try:
                    driver_path = ChromeDriverManager().install()
                except Exception as e:
                    logger.error(f"❌ webdriver-manager falló al descargar/instalar chromedriver: {e}")
                    logger.error("👉 Solución: ejecuta el bot desde PowerShell o descarga chromedriver manualmente y define CHROMEDRIVER_PATH.")
                    if devnull:
                        devnull.close()
                    return False

                if not driver_path:
                    logger.error("❌ ChromeDriverManager no devolvió una ruta válida.")
                    if devnull:
                        devnull.close()
                    return False

                service = Service(driver_path, log_path=os.devnull)
                service.stdout = subprocess.DEVNULL
                service.stderr = subprocess.DEVNULL
                if sys.platform == 'win32':
                    try:
                        service.creationflags = subprocess.CREATE_NO_WINDOW
                    except Exception:
                        pass
                self.driver = webdriver.Chrome(service=service, options=chrome_options)

            logger.info(f"✅ Driver iniciado (headless={getattr(Config, 'TWITTER_HEADLESS', False)})")
            
            logger.info("✅ Driver de Chrome inicializado")
            return True
        except Exception as e:
            logger.error(f"❌ Error al inicializar driver: {e}")
            return False
    
    def _human_type(self, element, text: str):
        """Simula escritura humana con delays aleatorios"""
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))
    
    def _human_delay(self, min_seconds: float = 1, max_seconds: float = 3):
        """Pausa con tiempo aleatorio para simular comportamiento humano"""
        time.sleep(random.uniform(min_seconds, max_seconds))
    
    def login_twitter(self, username: str, password: str) -> bool:
        """
        Inicia sesión en Twitter.
        
        Args:
            username: Nombre de usuario o email de Twitter
            password: Contraseña de Twitter
            
        Returns:
            True si el login fue exitoso
        """
        try:
            if not self.driver:
                ok = self._init_driver()
                if not ok:
                    logger.error("❌ Driver no inicializado. Abortando login de Twitter.")
                    return False
            
            logger.info("🔐 Iniciando sesión en Twitter...")

            # Ir a la página principal y comprobar si ya hay sesión iniciada
            self.driver.get("https://x.com/home")
            self._human_delay(2, 4)
            try:
                # Si estamos logueados normalmente existe el área de composición del tweet
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="tweetTextarea_0"]'))
                )
                logger.info("✅ Sesión de Twitter/X ya iniciada (perfil reutilizado)")
                return True
            except Exception:
                # No hay sesión, proceder al flujo de login
                logger.info("ℹ️ No hay sesión activa, navegando al flujo de login...")
                self.driver.get("https://x.com/i/flow/login")
                self._human_delay(3, 5)
            
            # Esperar y llenar el campo de usuario
            username_input = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[autocomplete="username"]'))
            )
            self._human_type(username_input, username)
            self._human_delay(0.5, 1)
            
            # Siguiente
            next_button = self.driver.find_element(By.XPATH, '//span[text()="Next" or text()="Siguiente"]')
            next_button.click()
            self._human_delay(2, 3)
            
            # Llenar contraseña
            password_input = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="password"]'))
            )
            self._human_type(password_input, password)
            self._human_delay(0.5, 1)
            
            # Login
            login_button = self.driver.find_element(By.XPATH, '//span[text()="Log in" or text()="Iniciar sesión"]')
            login_button.click()
            self._human_delay(3, 5)
            
            logger.info("✅ Login exitoso en Twitter")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al hacer login en Twitter: {e}")
            try:
                # Guardar artefactos para depuración
                os.makedirs('utils', exist_ok=True)
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                if self.driver:
                    screenshot_path = os.path.join('utils', f'twitter_login_error_{ts}.png')
                    html_path = os.path.join('utils', f'twitter_login_error_{ts}.html')
                    try:
                        self.driver.save_screenshot(screenshot_path)
                        with open(html_path, 'w', encoding='utf-8') as f:
                            f.write(self.driver.page_source)
                        logger.error(f"📎 Captura guardada: {screenshot_path}")
                        logger.error(f"📄 HTML guardado: {html_path}")
                    except Exception as save_err:
                        logger.error(f"❌ Error guardando captura/HTML: {save_err}")
            except Exception:
                pass
            return False
    
    def _history_path(self) -> str:
        return os.path.join(os.getcwd(), 'tweet_history.json')
    
    def _load_history(self) -> list:
        try:
            path = self._history_path()
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return []
    
    def _save_history(self, history: list):
        try:
            if len(history) > 1000:
                history = history[-1000:]
            with open(self._history_path(), 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(text.strip().encode('utf-8')).hexdigest()
    
    def _is_duplicate_recent(self, text: str, hours: float = 2.0) -> bool:
        try:
            h = self._hash_text(text)
            cutoff = time.time() - (hours * 3600)
            for item in self._load_history():
                if item.get('hash') == h and item.get('timestamp', 0) >= cutoff:
                    return True
        except Exception:
            return False
        return False
    
    def _register_tweet(self, text: str, category: str):
        try:
            history = self._load_history()
            history.append({
                'hash': self._hash_text(text),
                'timestamp': time.time(),
                'category': category
            })
            self._save_history(history)
        except Exception:
            pass
    
    def _mutate_crypto_text(self, text: str) -> str:
        try:
            import re
            symbols = re.findall(r'\b[A-Z0-9]{2,6}\b', text)
            if symbols:
                target = symbols[-1]
                mutated = text.replace(target, '2ND ANUNCIO', 1)
                if mutated.strip() != text.strip():
                    return mutated
            return (text.strip() + "\n2ND ANUNCIO").strip()
        except Exception:
            return (text.strip() + "\n2ND ANUNCIO").strip()
    
    def post_tweet(self, text: str, image_path: str = None, category: str = 'crypto') -> bool:
        """
        Publica un tweet con texto y opcionalmente una imagen.
        
        Args:
            text: Texto del tweet (máximo 280 caracteres)
            image_path: Ruta de la imagen a adjuntar (opcional)
            category: Categoría de publicación ('crypto', 'markets', 'news', 'signals', 'crypto_stable')
            
        Returns:
            True si se publicó correctamente
        """
        try:
            if not self.driver:
                logger.error("❌ Driver no inicializado. Ejecuta login_twitter primero.")
                return False
            
            if self._is_duplicate_recent(text, hours=2.0):
                if category in ('markets', 'news', 'crypto_stable'):
                    logger.info("⏭️ Tweet duplicado en las últimas 2h, saltando publicación")
                    return False
                else:
                    logger.info("♻️ Tweet duplicado detectado (crypto). Ajustando contenido con '2ND ANUNCIO'")
                    text = self._mutate_crypto_text(text)
            
            logger.info("📝 Publicando tweet...")
            
            # Ir a la página principal
            self.driver.get("https://x.com/home")
            self._human_delay(2, 3)
            
            # Encontrar el área de texto del tweet
            tweet_box = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="tweetTextarea_0"]'))
            )
            
            # Hacer clic en el área de texto
            tweet_box.click()
            self._human_delay(0.5, 1)
            
            # Usar clipboard para pegar el texto (soporta emojis y caracteres especiales)
            import pyperclip
            pyperclip.copy(text)
            self.driver.find_element(By.CSS_SELECTOR, 'div[data-testid="tweetTextarea_0"]').send_keys(Keys.CONTROL, 'v')
            self._human_delay(1, 2)
            
            # Si hay imagen, adjuntarla
            if image_path and os.path.exists(image_path):
                try:
                    # Encontrar el input de archivo (está oculto)
                    file_input = self.driver.find_element(By.CSS_SELECTOR, 'input[type="file"]')
                    file_input.send_keys(os.path.abspath(image_path))
                    logger.info(f"📎 Imagen adjuntada: {image_path}")
                    self._human_delay(2, 3)
                except Exception as img_error:
                    logger.warning(f"⚠️ No se pudo adjuntar imagen: {img_error}")
            
            # Presionar el botón Publicar automáticamente
            try:
                self._human_delay(1, 2)
                
                # Estrategia 1: Buscar por CSS selector
                try:
                    post_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-testid="Tweet_Button"]'))
                    )
                    logger.info("✅ Botón encontrado por CSS selector")
                    post_button.click()
                    self._human_delay(3, 4)  # Esperar más tiempo para que se procese
                    
                    # Verificar que el tweet fue publicado esperando a que desaparezca el textarea
                    try:
                        WebDriverWait(self.driver, 5).until(
                            EC.invisibility_of_element_located((By.CSS_SELECTOR, 'div[data-testid="tweetTextarea_0"]'))
                        )
                        logger.info("✅ Tweet publicado exitosamente")
                        try:
                            self._register_tweet(text, category)
                        except Exception:
                            pass
                        self._human_delay(2, 3)
                        return True
                    except:
                        logger.info("⚠️ Tweet probablemente publicado (textarea no desapareció)")
                        return True
                except:
                    pass
                
                # Estrategia 2: Buscar por aria-label
                try:
                    buttons = self.driver.find_elements(By.TAG_NAME, "button")
                    for button in buttons:
                        aria_label = button.get_attribute("aria-label") or ""
                        if "Post" in aria_label or "Tweet" in aria_label or "Publicar" in aria_label:
                            if button.is_displayed():
                                logger.info(f"✅ Botón encontrado por aria-label: {aria_label}")
                                self._human_delay(0.5, 1)
                                button.click()
                                self._human_delay(3, 4)
                                
                                # Verificar que se publicó
                                try:
                                    WebDriverWait(self.driver, 5).until(
                                        EC.invisibility_of_element_located((By.CSS_SELECTOR, 'div[data-testid="tweetTextarea_0"]'))
                                    )
                                except:
                                    pass
                                
                                logger.info("✅ Tweet publicado exitosamente")
                                try:
                                    self._register_tweet(text, category)
                                except Exception:
                                    pass
                                return True
                except:
                    pass
                
                # Estrategia 3: Buscar por JavaScript (más confiable)
                try:
                    logger.info("🔍 Buscando botón con JavaScript...")
                    script = """
                    var buttons = document.querySelectorAll('button');
                    for (var i = 0; i < buttons.length; i++) {
                        var btn = buttons[i];
                        var text = btn.textContent || btn.innerText;
                        var ariaLabel = btn.getAttribute('aria-label') || '';
                        if (text.includes('Post') || text.includes('Tweet') || text.includes('Publicar') ||
                            ariaLabel.includes('Post') || ariaLabel.includes('Tweet') || ariaLabel.includes('Publicar')) {
                            return btn;
                        }
                    }
                    return null;
                    """
                    post_button = self.driver.execute_script(script)
                    if post_button:
                        logger.info("✅ Botón encontrado con JavaScript")
                        self.driver.execute_script("arguments[0].click();", post_button)
                        self._human_delay(3, 4)
                        
                        # Verificar que se publicó
                        try:
                            WebDriverWait(self.driver, 5).until(
                                EC.invisibility_of_element_located((By.CSS_SELECTOR, 'div[data-testid="tweetTextarea_0"]'))
                            )
                        except:
                            pass
                        
                        logger.info("✅ Tweet publicado exitosamente")
                        try:
                            self._register_tweet(text, category)
                        except Exception:
                            pass
                        return True
                except Exception as js_error:
                    logger.warning(f"⚠️ Error con JavaScript: {js_error}")
                
                # Estrategia 4: Última opción - buscar visible button cerca del textarea
                try:
                    logger.info("🔍 Buscando botón visible cerca del textarea...")
                    textarea = self.driver.find_element(By.CSS_SELECTOR, 'div[data-testid="tweetTextarea_0"]')
                    parent = textarea.find_element(By.XPATH, '../../..')
                    buttons = parent.find_elements(By.TAG_NAME, "button")
                    
                    # Encontrar el botón más visible/enabled
                    for button in buttons:
                        if button.is_displayed() and button.is_enabled():
                            button.click()
                            self._human_delay(3, 4)
                            
                            # Verificar que se publicó
                            try:
                                WebDriverWait(self.driver, 5).until(
                                    EC.invisibility_of_element_located((By.CSS_SELECTOR, 'div[data-testid="tweetTextarea_0"]'))
                                )
                            except:
                                pass
                            
                            logger.info("✅ Tweet publicado exitosamente")
                            try:
                                self._register_tweet(text, category)
                            except Exception:
                                pass
                            return True
                except Exception as parent_error:
                    logger.warning(f"⚠️ Error buscando en parent: {parent_error}")
                
                logger.error("❌ No se encontró el botón Publicar con ninguna estrategia")
                return False
                    
            except Exception as post_error:
                logger.error(f"❌ Error al presionar botón Publicar: {post_error}")
                return False
            
        except Exception as e:
            logger.error(f"❌ Error al publicar tweet: {e}")
            return False
    
    def close(self):
        """Cierra el navegador"""
        if self.driver:
            self.driver.quit()
            logger.info("🔒 Navegador cerrado")

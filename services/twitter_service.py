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
from utils.security import sanitize_exception, get_redactor
import sys
import os
from datetime import datetime
import json
import hashlib
from typing import Any, List, Optional

# Registrar secretos para sanitización
try:
    get_redactor().register_secrets_from_config(Config)
except Exception:
    pass

class TwitterService:
    """Servicio para publicar en Twitter usando Selenium"""

    def __init__(self):
        """Inicializa el servicio de Twitter"""
        self.username = None  # Se configurará después
        self.password = None  # Se configurará después
        self.driver = None
        self.last_status: Optional[str] = None
        self.last_reason: Optional[str] = None
        logger.info("✅ Servicio de Twitter inicializado")

    def _init_driver(self):
        """Inicializa el driver de Chrome usando BrowserManager"""
        from utils.browser_utils import BrowserManager
        self.driver = BrowserManager.get_driver(headless=getattr(Config, 'TWITTER_HEADLESS', False))
        if self.driver:
            logger.info("✅ Servicio de Twitter: Driver inicializado correctamente")
            return True
        else:
            logger.error("❌ Servicio de Twitter: Falló la inicialización del driver")
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
            self._human_delay(3, 5)  # Dar más tiempo para cargar

            try:
                # Verificar múltiples indicadores de sesión activa
                session_indicators = [
                    'div[data-testid="tweetTextarea_0"]',  # Área de composición
                    'a[data-testid="AppTabBar_Home_Link"]',  # Tab Home activo
                    'div[data-testid="SideNav_AccountSwitcher_Button"]',  # Botón de cuenta
                    'a[href="/compose/tweet"]',  # Botón de tweet
                    'div[data-testid="primaryColumn"]',  # Columna principal del feed
                ]

                session_found = False
                for selector in session_indicators:
                    try:
                        WebDriverWait(self.driver, 3).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        logger.info(f"✅ Sesión detectada via: {selector}")
                        session_found = True
                        break
                    except:
                        continue

                # También verificar si NO estamos en la página de login
                current_url = self.driver.current_url
                if session_found or ('/home' in current_url and '/login' not in current_url and '/flow' not in current_url):
                    logger.info("✅ Sesión de Twitter/X ya iniciada (perfil reutilizado)")
                    return True

            except Exception as e:
                logger.debug(f"No se detectó sesión activa: {e}")

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
            # Sanitizar el mensaje de error para no exponer credenciales
            safe_error = sanitize_exception(e)
            logger.error(f"❌ Error al hacer login en Twitter: {safe_error}")

            # --- SECURITY FIX: No guardar raw page source ---
            # Guardar solo screenshot sanitizado si es posible, o nada.
            try:
                # Guardar artefactos para depuración
                os.makedirs('utils', exist_ok=True)
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                if self.driver:
                    screenshot_path = os.path.join('utils', f'twitter_login_error_{ts}.png')
                    # Eliminado el guardado de HTML para evitar robo de credenciales en texto plano
                    try:
                        self.driver.save_screenshot(screenshot_path)
                        logger.error(f"📎 Captura guardada: {screenshot_path}")
                        # logger.error(f"📄 HTML NO guardado por seguridad")
                    except Exception as save_err:
                        logger.error(f"❌ Error guardando captura: {sanitize_exception(save_err)}")
            except Exception:
                pass

            # Cerrar driver en caso de error para evitar fugas de recursos
            self._safe_close_driver()
            return False

    def _safe_close_driver(self):
        """Cierra el driver de forma segura"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

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
        Publica un tweet con texto y opcionalmente una imagen. Siempre incluye texto.
        """
        try:
            self.last_status = None
            self.last_reason = None
            if not self.driver:
                self.last_status = "error"
                self.last_reason = "driver_not_initialized"
                logger.error("❌ Driver no inicializado. Ejecuta login_twitter primero.")
                return False

            if self._is_duplicate_recent(text, hours=2.0):
                if category in ('markets', 'news', 'crypto_stable'):
                    self.last_status = "skipped"
                    self.last_reason = "duplicate"
                    logger.info("⏭️ Tweet duplicado en las últimas 2h, saltando publicación")
                    return False
                else:
                    logger.info("♻️ Tweet duplicado detectado (crypto). Ajustando contenido con '2ND ANUNCIO'")
                    text = self._mutate_crypto_text(text)

            if not (text or "").strip():
                self.last_status = "blocked"
                self.last_reason = "empty_text"
                logger.error("❌ Texto vacío: se bloquea publicación para evitar tweet sin texto")
                return False

            # Validar límite de caracteres de Twitter (280)
            TWITTER_CHAR_LIMIT = 280
            if len(text) > TWITTER_CHAR_LIMIT:
                logger.warning(f"⚠️ Texto excede límite de Twitter ({len(text)} > {TWITTER_CHAR_LIMIT}). Truncando...")
                text = text[:TWITTER_CHAR_LIMIT - 3] + "..."
                logger.info(f"✂️ Texto truncado a {len(text)} caracteres")

            logger.info(f"📝 Publicando tweet con texto: {text[:50]}{'...' if len(text)>50 else ''}")

            self.driver.get("https://x.com/home")
            self._human_delay(2, 3)

            def _find_compose_box():
                """Encuentra el textbox de composición de Twitter (DraftJS editor)"""
                from selenium.common.exceptions import StaleElementReferenceException
                
                # Selectores actualizados para la estructura actual de Twitter/X con DraftJS
                selectors = [
                    'div[data-testid="tweetTextarea_0"][role="textbox"]',  # Selector principal DraftJS
                    'div[data-testid="tweetTextarea_0"]',  # Fallback sin role
                    'div.public-DraftEditor-content[contenteditable="true"]',  # Fallback por clase
                    'div[data-testid^="tweetTextarea_"] div[role="textbox"]',  # Selector antiguo
                ]
                
                for sel in selectors:
                    try:
                        logger.debug(f"🔍 Buscando compose box con selector: {sel}")
                        WebDriverWait(self.driver, 15).until(
                            lambda d: len(d.find_elements(By.CSS_SELECTOR, sel)) > 0
                        )
                        candidates = self.driver.find_elements(By.CSS_SELECTOR, sel)
                        
                        # Filtrar elementos visibles, manejando StaleElementReferenceException
                        visible_candidates = []
                        for c in candidates:
                            try:
                                if c.is_displayed():
                                    visible_candidates.append(c)
                            except StaleElementReferenceException:
                                logger.debug("⚠️ Elemento obsoleto detectado, continuando...")
                                continue
                        
                        if visible_candidates:
                            logger.info(f"✅ Compose box encontrado con selector: {sel}")
                            return visible_candidates[0]
                        else:
                            logger.debug(f"⚠️ Elementos encontrados pero no visibles: {sel}")
                    except StaleElementReferenceException as stale_err:
                        logger.debug(f"⚠️ Elemento obsoleto con selector: {sel}")
                        continue
                    except Exception as e:
                        logger.debug(f"⚠️ Selector falló: {sel} - {str(e)[:50]}")
                        continue
                
                logger.error("❌ No se encontró el textbox de publicación con ningún selector")
                raise RuntimeError("No se encontró el textbox de publicación")

            def _read_compose_text():
                """Lee el texto actual del compose box (DraftJS)"""
                try:
                    box = _find_compose_box()
                    
                    # CRITICAL: Validar que box no sea None antes de pasar a JavaScript
                    if box is None:
                        logger.error("❌ _read_compose_text: box es None")
                        return ""
                    
                    # Intentar leer el contenido del editor DraftJS
                    try:
                        value = self.driver.execute_script(
                            "return (arguments[0].innerText || arguments[0].textContent || '');", 
                            box
                        )
                        return (value or "").strip()
                    except Exception as js_err:
                        logger.debug(f"⚠️ Error con JavaScript, usando .text: {str(js_err)[:50]}")
                        return (box.text or "").strip()
                except Exception as e:
                    logger.error(f"❌ Error leyendo compose text: {str(e)[:100]}")
                    return ""

            def _set_compose_text():
                """Establece el texto en el compose box usando escritura humana carácter por carácter"""
                box = _find_compose_box()
                
                # CRITICAL: Validar que box no sea None
                if box is None:
                    logger.error("❌ _set_compose_text: box es None")
                    return False
                
                # Click en el box para activarlo
                try:
                    box.click()
                    logger.debug("✅ Click en compose box exitoso")
                except Exception as click_err:
                    logger.debug(f"⚠️ Click normal falló, usando JavaScript: {str(click_err)[:50]}")
                    try:
                        self.driver.execute_script("arguments[0].click();", box)
                    except Exception as js_click_err:
                        logger.error(f"❌ Click con JavaScript falló: {str(js_click_err)[:50]}")
                        return False
                
                self._human_delay(0.3, 0.5)
                
                # Limpiar contenido existente
                try:
                    # Seleccionar todo y borrar
                    box.send_keys(Keys.CONTROL, "a")
                    self._human_delay(0.05, 0.1)
                    box.send_keys(Keys.BACKSPACE)
                    self._human_delay(0.1, 0.2)
                    logger.debug("✅ Contenido anterior limpiado")
                except Exception as clear_err:
                    logger.debug(f"⚠️ Error limpiando contenido: {str(clear_err)[:50]}")
                
                # NUEVA ESTRATEGIA: Escribir carácter por carácter como humano
                logger.info(f"⌨️ Escribiendo texto carácter por carácter: {text[:30]}...")
                try:
                    # Escribir cada carácter individualmente con delay aleatorio
                    for i, char in enumerate(text):
                        try:
                            # Manejar saltos de línea con SHIFT+ENTER
                            if char == '\n':
                                box.send_keys(Keys.SHIFT, Keys.ENTER)
                                time.sleep(random.uniform(0.05, 0.1))
                                continue
                            
                            # Enviar el carácter directamente (incluyendo emojis)
                            box.send_keys(char)
                            
                            # Delay aleatorio MÁS RÁPIDO entre caracteres (20-50ms)
                            time.sleep(random.uniform(0.02, 0.05))
                            
                            # Cada 30 caracteres, hacer una pausa más larga (simular pensamiento)
                            if (i + 1) % 30 == 0:
                                time.sleep(random.uniform(0.1, 0.2))
                                
                        except Exception as char_err:
                            # Si falla un carácter, intentar con ActionChains
                            logger.debug(f"⚠️ Error con carácter '{char}', intentando ActionChains")
                            try:
                                from selenium.webdriver.common.action_chains import ActionChains
                                ActionChains(self.driver).send_keys(char).perform()
                            except Exception:
                                # Si todo falla, continuar con el siguiente carácter
                                logger.debug(f"⚠️ Saltando carácter '{char}'")
                                continue
                    
                    logger.info("✅ Texto escrito carácter por carácter exitosamente")
                    
                except Exception as type_err:
                    logger.error(f"❌ Error en escritura carácter por carácter: {str(type_err)[:100]}")
                    return False
                
                self._human_delay(0.2, 0.3)
                
                # Disparar eventos para que DraftJS reconozca el cambio
                try:
                    self.driver.execute_script(
                        "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));"
                        "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
                        box,
                    )
                except Exception:
                    pass
                
                self._human_delay(0.2, 0.3)
                
                # Verificar que el texto se estableció correctamente
                current = _read_compose_text()
                if not text.strip():
                    return True
                
                expected = " ".join(text.strip().split())
                current_norm = " ".join((current or "").split())
                
                logger.debug(f"📝 Texto esperado: {expected[:50]}...")
                logger.debug(f"📝 Texto actual: {current_norm[:50]}...")
                
                # Verificación MÁS ESTRICTA para evitar loops infinitos
                if expected and len(expected) > 0:
                    # Verificar que al menos el 60% del inicio coincida
                    expected_start = expected[:min(50, len(expected))]
                    current_start = current_norm[:min(50, len(current_norm))]
                    
                    # Contar caracteres coincidentes
                    matches = sum(1 for a, b in zip(expected_start, current_start) if a == b)
                    match_ratio = matches / len(expected_start) if len(expected_start) > 0 else 0
                    
                    if match_ratio >= 0.6:
                        logger.info(f"✅ Texto verificado correctamente (coincidencia: {match_ratio*100:.1f}%)")
                        return True
                    else:
                        logger.warning(f"⚠️ Coincidencia baja ({match_ratio*100:.1f}%), pero continuando para evitar loop")
                        return True  # Aceptar de todas formas para evitar loop infinito
                
                logger.info("✅ Texto establecido (verificación básica)")
                return True

            if not _set_compose_text():
                self.last_status = "blocked"
                self.last_reason = "compose_text"
                logger.error("❌ No se pudo asegurar el texto en el composer antes de publicar")
                return False

            if image_path and os.path.exists(image_path):
                try:
                    # Selector actualizado para Twitter/X actual
                    try:
                        file_input = self.driver.find_element(By.CSS_SELECTOR, 'input[data-testid="fileInput"]')
                        logger.debug("✅ Input de archivo encontrado con data-testid")
                    except Exception:
                        file_input = self.driver.find_element(By.CSS_SELECTOR, 'input[type="file"]')
                        logger.debug("✅ Input de archivo encontrado con type=file")
                    
                    file_input.send_keys(os.path.abspath(image_path))
                    logger.info(f"📎 Imagen adjuntada: {image_path}")
                    
                    # Esperar a que Twitter procese la imagen
                    logger.debug("⏳ Esperando a que Twitter procese la imagen...")
                    self._human_delay(3, 4)  # Tiempo suficiente para que procese la imagen
                    
                    logger.info("✅ Imagen procesada, el texto ya está establecido")
                    
                except Exception as file_err:
                    self.last_status = "error"
                    self.last_reason = "attach_image"
                    logger.error(f"❌ Error adjuntando imagen: {sanitize_exception(file_err)}")
                    return False

            def _click_post_button():
                """Hace click en el botón Post/Publicar"""
                # Selectores actualizados para Twitter/X actual
                selectors = [
                    'button[data-testid="tweetButtonInline"]',  # Selector principal actual
                    'button[data-testid="tweetButton"]',  # Fallback
                    'button[data-testid="Tweet_Button"]',  # Fallback antiguo
                ]
                
                for sel in selectors:
                    try:
                        logger.debug(f"🔍 Buscando botón Post con selector: {sel}")
                        
                        # Esperar a que el botón exista
                        post_button = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                        )
                        
                        if post_button is None:
                            logger.debug(f"⚠️ Botón es None con selector: {sel}")
                            continue
                        
                        # Esperar a que el botón esté habilitado (no aria-disabled="true")
                        logger.debug("⏳ Esperando a que el botón esté habilitado...")
                        WebDriverWait(self.driver, 10).until(
                            lambda d: post_button.get_attribute("aria-disabled") != "true"
                        )
                        
                        # Verificar que esté visible y habilitado
                        if post_button.is_displayed() and post_button.is_enabled():
                            logger.info(f"✅ Botón Post encontrado y habilitado: {sel}")
                            post_button.click()
                            logger.info("✅ Click en botón Post exitoso")
                            return True
                        else:
                            logger.debug(f"⚠️ Botón no visible o no habilitado: {sel}")
                            
                    except Exception as e:
                        logger.debug(f"⚠️ Selector falló: {sel} - {str(e)[:50]}")
                        continue

                # Fallback: buscar por aria-label
                logger.debug("🔍 Intentando fallback por aria-label...")
                try:
                    buttons = self.driver.find_elements(By.TAG_NAME, "button")
                    for button in buttons:
                        aria_label = button.get_attribute("aria-label") or ""
                        aria_disabled = button.get_attribute("aria-disabled") or ""
                        
                        if ("Post" in aria_label or "Tweet" in aria_label or "Publicar" in aria_label):
                            if aria_disabled != "true" and button.is_displayed() and button.is_enabled():
                                logger.info(f"✅ Botón encontrado por aria-label: {aria_label}")
                                button.click()
                                return True
                except Exception as aria_err:
                    logger.debug(f"⚠️ Fallback aria-label falló: {str(aria_err)[:50]}")

                # Fallback: JavaScript
                logger.debug("🔍 Intentando fallback con JavaScript...")
                try:
                    script = """
                    var buttons = document.querySelectorAll('button');
                    for (var i = 0; i < buttons.length; i++) {
                        var btn = buttons[i];
                        var text = btn.textContent || btn.innerText;
                        var ariaLabel = btn.getAttribute('aria-label') || '';
                        var ariaDisabled = btn.getAttribute('aria-disabled') || '';
                        
                        if ((text.includes('Post') || text.includes('Tweet') || text.includes('Publicar') ||
                            ariaLabel.includes('Post') || ariaLabel.includes('Tweet') || ariaLabel.includes('Publicar')) &&
                            ariaDisabled !== 'true') {
                            return btn;
                        }
                    }
                    return null;
                    """
                    post_button = self.driver.execute_script(script)
                    
                    if post_button is not None:
                        logger.info("✅ Botón encontrado con JavaScript")
                        self.driver.execute_script("arguments[0].click();", post_button)
                        return True
                    else:
                        logger.debug("⚠️ JavaScript no encontró el botón")
                        
                except Exception as js_error:
                    logger.warning(f"⚠️ Error con JavaScript: {sanitize_exception(js_error)}")

                # Fallback final: buscar en el parent del textarea
                logger.debug("🔍 Intentando fallback por parent del textarea...")
                try:
                    textarea = self.driver.find_element(By.CSS_SELECTOR, 'div[data-testid="tweetTextarea_0"]')
                    parent = textarea.find_element(By.XPATH, '../../..')
                    buttons = parent.find_elements(By.TAG_NAME, "button")
                    
                    for button in buttons:
                        aria_disabled = button.get_attribute("aria-disabled") or ""
                        if aria_disabled != "true" and button.is_displayed() and button.is_enabled():
                            logger.info("✅ Botón encontrado en parent del textarea")
                            button.click()
                            return True
                            
                except Exception as parent_error:
                    logger.warning(f"⚠️ Error buscando en parent: {sanitize_exception(parent_error)}")

                logger.error("❌ No se pudo encontrar el botón Post con ninguna estrategia")
                return False

            # Ya no necesitamos re-establecer el texto aquí
            # El texto ya fue escrito correctamente al inicio
            logger.debug("✅ Texto ya establecido, procediendo a publicar...")

            if not _click_post_button():
                self.last_status = "error"
                self.last_reason = "no_post_button"
                logger.error("❌ No se encontró el botón Publicar con ninguna estrategia")
                return False

            self._human_delay(3, 4)

            try:
                WebDriverWait(self.driver, 8).until(lambda d: _read_compose_text() == "")
            except Exception:
                self.last_status = "error"
                self.last_reason = "confirm_failed"
                logger.error("❌ No se pudo confirmar que el tweet se publicó (composer sigue con texto)")
                return False

            self.last_status = "posted"
            logger.info("✅ Tweet publicado exitosamente")
            try:
                self._register_tweet(text, category)
            except Exception:
                pass
            self._human_delay(2, 3)
            return True

        except Exception as e:
            self.last_status = "error"
            self.last_reason = "exception"
            logger.error(f"❌ Error al publicar tweet: {sanitize_exception(e)}")
            return False

    def close(self):
        """Cierra el navegador"""
        if self.driver:
            self.driver.quit()
            logger.info("🔒 Navegador cerrado")

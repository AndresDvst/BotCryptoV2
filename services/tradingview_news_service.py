"""
Servicio para scrapear noticias de TradingView y filtrarlas con IA.
"""
import time
import json
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils.logger import logger
from config.config import Config
from services.ai_analyzer_service import AIAnalyzerService
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from typing import List, Dict

class TradingViewNewsService:
    """Servicio para obtener noticias de TradingView News"""
    
    NEWS_URL = "https://www.tradingview.com/news/"
    HISTORY_FILE = "news_history.json"
    
    def __init__(self, telegram=None, twitter=None, ai_analyzer: AIAnalyzerService = None):
        """
        Inicializa el servicio
        
        Args:
            telegram: Servicio de Telegram
            twitter: Servicio de Twitter
            ai_analyzer: Servicio de análisis con IA
        """
        self.telegram = telegram
        self.twitter = twitter
        self.ai_analyzer = ai_analyzer
        logger.info("✅ Servicio de Noticias TradingView inicializado")
        
    def _get_driver(self):
        """Inicializa el driver de Selenium"""
        try:
            options = Options()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--remote-debugging-port=9222')
            options.add_argument('--window-size=1920,1080')
            if getattr(Config, 'TWITTER_HEADLESS', False):
                options.add_argument('--headless=new')
            # Usar el mismo perfil que Twitter para compartir sesión/configuración
            user_data_dir = getattr(Config, 'CHROME_USER_DATA_DIR', None) or os.path.join(os.getcwd(), 'chrome_profile')
            os.makedirs(user_data_dir, exist_ok=True)
            options.add_argument(f'--user-data-dir={user_data_dir}')
            options.add_argument('--profile-directory=Default')
            # Resolver versión de chromedriver
            driver_path = getattr(Config, 'CHROMEDRIVER_PATH', None) or os.getenv('CHROMEDRIVER_PATH', None)
            if driver_path and os.path.isfile(driver_path):
                service = Service(driver_path)
                driver = webdriver.Chrome(service=service, options=options)
            else:
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options)
            return driver
        except Exception as e:
            logger.error(f"❌ Error al iniciar Chrome Driver: {e}")
            return None

    def _load_history(self) -> List[str]:
        """Carga el historial de noticias procesadas"""
        if os.path.exists(self.HISTORY_FILE):
            try:
                with open(self.HISTORY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"⚠️ Error cargando historial de noticias: {e}")
        return []

    def _save_history(self, history: List[str]):
        """Guarda el historial de noticias procesadas"""
        try:
            # Mantener solo los últimos 1000 IDs
            if len(history) > 1000:
                history = history[-1000:]
            
            with open(self.HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌ Error guardando historial de noticias: {e}")

    def scrape_news(self) -> List[Dict]:
        """
        Scrapea las noticias de TradingView reutilizando el navegador si es posible.
        """
        logger.info(f"📰 Scraping noticias de {self.NEWS_URL}...")
        
        driver = None
        is_shared_driver = False
        
        # Intentar reusar el driver de Twitter si existe y está vivo
        if self.twitter and self.twitter.driver:
            try:
                # Verificar si el driver sigue respondiendo
                self.twitter.driver.title 
                driver = self.twitter.driver
                is_shared_driver = True
                logger.info("♻️ Reutilizando driver de Twitter")
            except Exception:
                logger.warning("⚠️ Driver de Twitter no responde, se creará uno nuevo")
                driver = None

        # Si no hay driver compartido, crear uno nuevo temporal
        if not driver:
            driver = self._get_driver()
            if not driver:
                return []
        
        news_items = []
        original_window = None
        
        try:
            if is_shared_driver:
                # Guardar handle de la ventana original (Twitter)
                original_window = driver.current_window_handle
                # Abrir nueva pestaña
                driver.switch_to.new_window('tab')
                logger.info("📑 Abierta nueva pestaña para noticias")
            
            driver.get(self.NEWS_URL)
            time.sleep(5)  # Esperar a que cargue
            
            # --- LOGICA DE SCRAPING EXISTENTE ---
            processed_titles = self._load_history()
            articles = driver.find_elements(By.TAG_NAME, "article")
            
            for article in articles:
                try:
                    title_element = article.find_element(By.TAG_NAME, "h3")
                    link_element =  article.find_element(By.TAG_NAME, "a")
                    
                    if title_element and link_element:
                        title = title_element.text.strip()
                        link = link_element.get_attribute("href")
                        
                        if title and link and title not in processed_titles:
                            news_items.append({
                                'title': title,
                                'url': link,
                                'source': 'TradingView'
                            })
                            processed_titles.append(title)
                except Exception:
                    continue
            
            # Fallback scraping
            if not news_items:
                 links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/news/']")
                 for link_elem in links:
                     try:
                         title = link_elem.text.strip()
                         link = link_elem.get_attribute("href")
                         if title and len(title) > 20 and title not in processed_titles:
                             news_items.append({
                                'title': title,
                                'url': link,
                                'source': 'TradingView'
                            })
                             processed_titles.append(title)
                     except:
                         continue

            logger.info(f"✅ Se obtuvieron {len(news_items)} noticias nuevas")
            self._save_history(processed_titles)
            
        except Exception as e:
            logger.error(f"❌ Error scraping TradingView: {e}")
        finally:
            if is_shared_driver:
                # Cerrar SOLO la pestaña de noticias
                try:
                    driver.close() # Cierra pestaña actual
                    driver.switch_to.window(original_window) # Vuelve a Twitter
                    logger.info("📑 Pestaña de noticias cerrada, volviendo a Twitter")
                except Exception as e:
                    logger.error(f"❌ Error cerrando pestaña: {e}")
            else:
                # Si el driver es propio, cerrarlo completo
                driver.quit()
                logger.info("🔒 Driver temporal cerrado")
            
        return news_items

    def process_and_publish(self):
        """
        Ejecuta el ciclo completo: Scraping -> Análisis IA (Lote) -> Publicación
        """
        if not self.ai_analyzer:
            logger.error("❌ AIAnalyzer no configurado")
            return
            
        # 1. Scrapear
        news_list = self.scrape_news()
        if not news_list:
            logger.info("📰 No hay noticias nuevas para procesar")
            return
            
        logger.info(f"🧠 Analizando {len(news_list)} noticias con IA (Modo Batch)...")
        
        # 2. Analizar con IA (LOTE)
        news_titles = [n['title'] for n in news_list]
        analyzed_results = self.ai_analyzer.analyze_news_batch(news_titles)
        
        important_news = []
        
        for item in analyzed_results:
            idx = item.get('original_index')
            if idx is not None and 0 <= idx < len(news_list):
                original_news = news_list[idx]
                # Enriquecer con datos del análisis
                original_news['analysis'] = {
                    'score': item.get('score', 0),
                    'summary': item.get('summary', 'Sin resumen'),
                    'category': item.get('category', 'crypto')
                }
                important_news.append(original_news)
                logger.info(f"🔥 Noticia Importante ({item.get('score')}/10): {original_news['title']}")

        # Ordenar por relevancia
        important_news.sort(key=lambda x: x['analysis']['score'], reverse=True)
        
        # Top 5
        top_news = important_news[:5]
        
        # 3. Publicar
        if top_news:
            self._publish_news(top_news)
        else:
            logger.info("✅ Ninguna noticia superó el umbral de relevancia (7/10)")

    def _publish_news(self, news_list: List[Dict]):
        """Publica las noticias filtradas"""
        
        for news in news_list:
            title = news['title']
            url = news['url']
            score = news['analysis']['score']
            summary = news['analysis']['summary']
            # Obtener categoría del análisis batch, o default a crypto
            category = news['analysis'].get('category', 'crypto')
            
            # Mensaje
            message = f"🔥 NOTICIA IMPORTANTE\n\n"
            message += f"{title}\n\n"
            message += f"📊 Relevancia: {score}/10\n"
            message += f"📝 {summary}\n"
            message += f"🔗 {url}"
            
            # Telegram con clasificación IA -> bot correcto
            if self.telegram:
                # Usar la categoría que ya nos dio el análisis batch
                if category == 'markets':
                    self.telegram.send_message(message, bot_type='markets')
                elif category == 'signals':
                    self.telegram.send_message(message, bot_type='signals')
                else:
                    self.telegram.send_message(message, bot_type='crypto')
                time.sleep(2)
                
            # Twitter
            if self.twitter:
                self.twitter.post_tweet(message, category='news')
                time.sleep(10) # Evitar flood
                
            logger.info(f"✅ Publicada noticia: {title} ({category})")
            
        logger.info(f"✅ Total publicadas: {len(news_list)}")

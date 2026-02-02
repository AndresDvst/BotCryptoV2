"""
Servicio para scrapear noticias de TradingView y filtrarlas con IA.
Refactorado para producción con separación de responsabilidades, retries y modo degradado.
"""
import json
import os
import time
import subprocess
import shutil
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar
import tempfile
import requests

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
import re

T = TypeVar("T")

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
        self._default_wait_seconds = 10
        self._max_publish_per_cycle = 5
        self._score_threshold = 7
        self._retry_attempts = 3
        self._retry_base_delay = 1.0
        self._retry_max_delay = 6.0
        logger.info("✅ Servicio de Noticias TradingView inicializado")
        
    def _retry(self, func: Callable[[], T], attempts: int = None, base_delay: float = None, max_delay: float = None) -> Optional[T]:
        attempts = attempts or self._retry_attempts
        base_delay = base_delay or self._retry_base_delay
        max_delay = max_delay or self._retry_max_delay
        last_error: Optional[Exception] = None
        for i in range(attempts):
            try:
                return func()
            except Exception as e:
                last_error = e
                delay = min(max_delay, base_delay * (2 ** i))
                logger.warning(f"⚠️ Retry intento {i+1}/{attempts}: {e} (esperando {delay:.1f}s)")
                time.sleep(delay)
        if last_error:
            logger.error(f"❌ Falló tras {attempts} intentos: {last_error}")
        return None

    def _get_driver(self) -> Optional[webdriver.Chrome]:
        """Inicializa el driver de Selenium usando BrowserManager"""
        from utils.browser_utils import BrowserManager
        return BrowserManager.get_driver()

    def _load_history(self) -> List[str]:
        """Carga el historial de noticias procesadas"""
        if os.path.exists(self.HISTORY_FILE):
            try:
                with open(self.HISTORY_FILE, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:
                        logger.debug("📰 Historial de noticias vacío, iniciando nuevo")
                        return []
                    return json.loads(content)
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Historial de noticias corrupto, reiniciando: {e}")
                return []
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

    def _wait_for_articles(self, driver: webdriver.Chrome) -> List[Any]:
        try:
            WebDriverWait(driver, self._default_wait_seconds).until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "article"))
            )
            return driver.find_elements(By.TAG_NAME, "article")
        except Exception as e:
            logger.warning(f"⚠️ Timeout esperando artículos: {e}")
            return []

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
            driver = self._retry(self._get_driver)
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
            articles = self._wait_for_articles(driver)
            
            # --- LOGICA DE SCRAPING EXISTENTE ---
            processed_titles = self._load_history()
            
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

    def process_and_publish(self, dry_run: bool = False):
        """
        Ejecuta el ciclo completo: Scraping -> Análisis IA (Lote) -> Publicación.
        Modo degradado: fallos de IA o Twitter no detienen el ciclo.
        
        Args:
            dry_run: Si True, no publica; solo registra resultados.
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
        analyzed_results: List[Dict] = []
        try:
            news_titles = [n['title'] for n in news_list]
            analyzed_results = self._retry(lambda: self.ai_analyzer.analyze_news_batch(news_titles)) or []
        except Exception as e:
            logger.error(f"❌ Falló análisis batch IA: {e}")
            analyzed_results = []
        
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
                if original_news['analysis']['score'] >= self._score_threshold:
                    important_news.append(original_news)
                    logger.info(f"🔥 Noticia ({item.get('score')}/10): {original_news['title']}")

        # Ordenar por relevancia
        important_news.sort(key=lambda x: x['analysis']['score'], reverse=True)
        
        top_news = important_news[: self._max_publish_per_cycle]
        
        # 3. Publicar
        if top_news:
            self._publish_news(top_news, dry_run=dry_run)
        else:
            logger.info("✅ Ninguna noticia superó el umbral de relevancia (7/10)")

    def _extract_keywords(self, title: str) -> list:
        """Extrae símbolos/tickers del título"""
        tickers = re.findall(r'\b[A-Z]{2,5}\b', title)
        return tickers[:3]

    def _fetch_yahoo_finance_image(self, title: str, summary: str) -> Optional[str]:
        """Busca imagen en Yahoo Finance"""
        try:
            keywords = self._extract_keywords(title)
            search_url = f"https://finance.yahoo.com/quote/{keywords[0]}" if keywords else None
            
            if search_url:
                response = requests.get(search_url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
                if response.status_code == 200:
                    match = re.search(r'<meta property="og:image" content="([^"]+)"', response.text)
                    if match:
                        return match.group(1)
            return None
        except Exception:
            return None

    def _format_professional_news_message(self, news_item: dict, has_image: bool) -> str:
        """Formatea mensaje profesional"""
        category = news_item.get('analysis', {}).get('category', 'crypto')
        title = news_item.get('title', '')
        summary = news_item.get('analysis', {}).get('summary', '')
        score = news_item.get('analysis', {}).get('score', 0)
        
        emoji_map = {'crypto': '🪙', 'markets': '📈', 'signals': '🎯'}
        emoji = emoji_map.get(category, '📰')
        relevance = "⭐" * min(score, 10)
        
        return f"""{emoji} **NOTICIA {category.upper()}**

📌 **{title}**

{summary}

{'📊 Relevancia: ' + relevance + f' ({score}/10)' if score > 0 else ''}

🔗 Fuente: TradingView"""

    def _publish_news(self, news_list: List[Dict], dry_run: bool = False):
        """Publica las noticias filtradas"""
        
        for news in news_list:
            title = news['title']
            # Obtener categoría del análisis batch
            category = news['analysis'].get('category', 'crypto').lower()
            
            # Buscar imagen
            image_url = self._fetch_yahoo_finance_image(title, news['analysis'].get('summary', ''))
            
            # Mensaje profesional
            message = self._format_professional_news_message(news, bool(image_url))
            
            if self.telegram and not dry_run:
                try:
                    # Determinar grupo destino usando Config
                    target_group = None
                    if category == 'signals':
                        target_group = Config.TELEGRAM_GROUP_SIGNALS
                    elif category == 'markets':
                        target_group = Config.TELEGRAM_GROUP_MARKETS
                    else:
                        target_group = Config.TELEGRAM_GROUP_CRYPTO
                        
                    def send_telegram():
                        if target_group:
                            self.telegram.send_to_specific_group(message, target_group, image_url=image_url)
                        else:
                            # Fallback
                            if category == 'markets':
                                self.telegram.send_market_message(message, image_url=image_url)
                            elif category == 'signals':
                                self.telegram.send_signal_message(message, image_url=image_url)
                            else:
                                self.telegram.send_crypto_message(message, image_url=image_url)
                                
                    self._retry(send_telegram)
                except Exception as e:
                    logger.error(f"❌ Error enviando a Telegram: {e}")
                
            # Twitter
            if self.twitter and not dry_run:
                try:
                    tweet_text = f"{'🪙' if category=='crypto' else '📈'} {title[:100]}...\n\n"
                    tweet_text += f"{news['analysis'].get('summary', '')[:100]}...\n\n"
                    tweet_text += f"🔗 {news['url']}\n"
                    tweet_text += f"#Trading #News #{category}"
                    
                    self._retry(lambda: self.twitter.post_tweet(tweet_text[:280], image_path=image_url))
                except Exception as e:
                    logger.error(f"❌ Error publicando en Twitter: {e}")
                
            logger.info(f"✅ Publicada noticia: {title} ({category})")
            
        logger.info(f"✅ Total publicadas: {len(news_list)}")

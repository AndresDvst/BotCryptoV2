"""
Servicio de Scraping de Noticias en Tiempo Real.
Integra CryptoPanic API y Google News RSS con filtro de relevancia por IA.
"""
import time
import feedparser
import hashlib
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
from utils.logger import logger
from services.ai_analyzer_service import AIAnalyzerService
from services.telegram_service import TelegramService
from services.twitter_service import TwitterService
from database.mysql_manager import MySQLManager
from config.config import Config
import re
import os


class NewsService:
    """Servicio para scraping y filtrado de noticias de crypto y mercados"""
    
    # Archivo de historial local (fallback cuando DB no disponible)
    NEWS_HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'news_history.json')
    
    def __init__(self, db: MySQLManager, telegram: TelegramService, twitter: TwitterService, ai_analyzer: AIAnalyzerService):
        """
        Inicializa el servicio de noticias.
        
        Args:
            db: Instancia de MySQLManager
            telegram: Instancia de TelegramService
            twitter: Instancia de TwitterService
            ai_analyzer: Instancia de AIAnalyzerService para filtrado
        """
        self.db = db
        self.telegram = telegram
        self.twitter = twitter
        self.ai_analyzer = ai_analyzer
        
        # URLs de fuentes
        self.cryptopanic_url = "https://cryptopanic.com/api/v1/posts/"
        self.cryptopanic_token = "free"  # Token gratuito (limitado)
        
        # Google News RSS feeds
        self.google_news_feeds = [
            "https://news.google.com/rss/search?q=cryptocurrency&hl=es&gl=US&ceid=US:es",
            "https://news.google.com/rss/search?q=bitcoin&hl=es&gl=US&ceid=US:es",
            "https://news.google.com/rss/search?q=ethereum&hl=es&gl=US&ceid=US:es",
            "https://news.google.com/rss/search?q=stock+market&hl=es&gl=US&ceid=US:es",
            "https://news.google.com/rss/search?q=forex&hl=es&gl=US&ceid=US:es"
        ]
        
        # Configuración
        self.min_relevance_score = 7  # Publicar solo noticias con score >= 7
        self.check_interval = 420  # 7 minutos en segundos
        self.max_ai_calls_per_cycle = 10
        self._ai_cache_ttl = 3600
        self._ai_cache: Dict[str, Tuple[Dict[str, Any], float]] = {}
        
        logger.info("✅ Servicio de Noticias inicializado")
    
    def get_news_hash(self, title: str, url: str) -> str:
        """
        Genera hash único para una noticia (para deduplicación).
        
        Args:
            title: Título de la noticia
            url: URL de la noticia
            
        Returns:
            Hash MD5 de la noticia
        """
        content = f"{title}|{url}".encode('utf-8')
        return hashlib.md5(content).hexdigest()
    
    def is_news_published(self, news_hash: str) -> bool:
        """
        Verifica si una noticia ya fue publicada.
        Usa DB si disponible, sino archivo local.
        
        Args:
            news_hash: Hash de la noticia
            
        Returns:
            True si ya fue publicada
        """
        # Intentar DB primero
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) FROM news_history 
                WHERE news_hash = %s
            """, (news_hash,))
            
            count = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            return count > 0
            
        except Exception as e:
            # Fallback a archivo local
            return self._is_news_published_local(news_hash)
    
    def _is_news_published_local(self, news_hash: str) -> bool:
        """Verifica en archivo local si la noticia fue publicada"""
        try:
            import json
            if os.path.exists(self.NEWS_HISTORY_FILE):
                with open(self.NEWS_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return news_hash in data.get('published_hashes', [])
        except Exception:
            pass
        return False
    
    def _save_news_local(self, news: Dict):
        """Guarda noticia en archivo local (fallback)"""
        try:
            import json
            data = {'published_hashes': [], 'news': []}
            if os.path.exists(self.NEWS_HISTORY_FILE):
                with open(self.NEWS_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            if 'published_hashes' not in data:
                data['published_hashes'] = []
            if 'news' not in data:
                data['news'] = []
            
            if news['hash'] not in data['published_hashes']:
                data['published_hashes'].append(news['hash'])
                data['news'].append({
                    'hash': news['hash'],
                    'title': news['title'][:100],
                    'timestamp': datetime.now().isoformat()
                })
                # Mantener solo últimas 500 noticias
                data['published_hashes'] = data['published_hashes'][-500:]
                data['news'] = data['news'][-500:]
                
                with open(self.NEWS_HISTORY_FILE, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"⚠️ Error guardando noticia localmente: {e}")
    
    def save_news(self, news: Dict):
        """
        Guarda noticia en la base de datos, con fallback a archivo local.
        
        Args:
            news: Diccionario con datos de la noticia
        """
        saved_to_db = False
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO news_history 
                (news_hash, title, url, source, category, relevance_score, published_twitter, published_telegram)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                news['hash'],
                news['title'],
                news['url'],
                news['source'],
                news.get('category', 'general'),
                news.get('relevance_score', 0),
                news.get('published_twitter', False),
                news.get('published_telegram', False)
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            saved_to_db = True
            
        except Exception as e:
            logger.debug(f"⚠️ Error guardando noticia en DB: {e}")
        
        # Siempre guardar en archivo local como respaldo
        self._save_news_local(news['hash'], news)
    
    def fetch_cryptopanic_news(self) -> List[Dict]:
        """
        Obtiene noticias de CryptoPanic API.
        
        Returns:
            Lista de noticias
        """
        if not self.cryptopanic_token:
            logger.debug("⏭️ CryptoPanic deshabilitado (sin token)")
            return []
            
        try:
            logger.info("📰 Obteniendo noticias de CryptoPanic...")
            
            params = {
                'auth_token': self.cryptopanic_token,
                'public': 'true',
                'kind': 'news',
                'filter': 'important'  # Solo noticias importantes
            }
            
            response = requests.get(self.cryptopanic_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                news_list = []
                for item in results[:10]:  # Limitar a 10 noticias
                    news = {
                        'title': item.get('title', ''),
                        'url': item.get('url', ''),
                        'source': 'CryptoPanic',
                        'category': 'crypto',
                        'published_at': item.get('published_at', '')
                    }
                    news['hash'] = self.get_news_hash(news['title'], news['url'])
                    news_list.append(news)
                
                logger.info(f"✅ Obtenidas {len(news_list)} noticias de CryptoPanic")
                return news_list
            elif response.status_code == 404:
                logger.debug("⏭️ CryptoPanic API no disponible (404)")
                return []
            else:
                logger.debug(f"⏭️ CryptoPanic API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.debug(f"⏭️ Error obteniendo noticias de CryptoPanic: {e}")
            return []
    
    def fetch_google_news(self) -> List[Dict]:
        """
        Obtiene noticias de Google News RSS.
        
        Returns:
            Lista de noticias
        """
        try:
            logger.info("📰 Obteniendo noticias de Google News...")
            all_news: List[Dict] = []

            def parse_feed(feed_url: str) -> List[Dict]:
                items: List[Dict] = []
                try:
                    feed = feedparser.parse(feed_url)
                    for entry in feed.entries[:5]:
                        news = {
                            "title": entry.get("title", ""),
                            "url": entry.get("link", ""),
                            "source": "Google News",
                            "category": self._categorize_from_url(feed_url),
                            "published_at": entry.get("published", ""),
                        }
                        news["hash"] = self.get_news_hash(news["title"], news["url"])
                        items.append(news)
                except Exception as e:
                    logger.warning(f"⚠️ Error con feed {feed_url}: {e}")
                return items

            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(parse_feed, url): url for url in self.google_news_feeds}
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        all_news.extend(result)

            logger.info(f"✅ Obtenidas {len(all_news)} noticias de Google News")
            return all_news
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo noticias de Google News: {e}")
            return []
    
    def _categorize_from_url(self, url: str) -> str:
        """Categoriza noticia basándose en la URL del feed"""
        if 'bitcoin' in url:
            return 'bitcoin'
        elif 'ethereum' in url:
            return 'ethereum'
        elif 'cryptocurrency' in url:
            return 'crypto'
        elif 'stock' in url:
            return 'stocks'
        elif 'forex' in url:
            return 'forex'
        else:
            return 'general'
    
    def _get_ai_cached(self, key: str) -> Optional[Dict[str, Any]]:
        now = time.time()
        if key in self._ai_cache:
            value, expires_at = self._ai_cache[key]
            if expires_at > now:
                return value
        return None

    def _set_ai_cached(self, key: str, value: Dict[str, Any], ttl_seconds: int) -> None:
        self._ai_cache[key] = (value, time.time() + ttl_seconds)

    def filter_news_by_relevance(self, news: Dict) -> Optional[Dict]:
        """
        Filtra noticia por relevancia usando IA.
        
        Args:
            news: Diccionario con datos de la noticia
            
        Returns:
            Noticia con score de relevancia o None si no es relevante
        """
        try:
            cached = self._get_ai_cached(news['hash'])
            if cached:
                news['relevance_score'] = int(cached.get('score', 5))
                news['summary'] = str(cached.get('summary', news['title'][:100]))
                return news if news['relevance_score'] >= self.min_relevance_score else None

            analysis = self.ai_analyzer.analyze_text(news['title'])
            score = int(analysis.get('score', 5))
            summary = str(analysis.get('summary', news['title'][:100]))
            score = max(1, min(10, score))

            news['relevance_score'] = score
            news['summary'] = summary
            self._set_ai_cached(news['hash'], {'score': score, 'summary': summary}, self._ai_cache_ttl)

            logger.info(f"📊 Relevancia: {score}/10 - {news['title'][:50]}...")
            return news if score >= self.min_relevance_score else None
            
        except Exception as e:
            logger.warning(f"⚠️ Error filtrando noticia: {e}")
            return None
            
    def _extract_keywords(self, title: str) -> list:
        """Extrae símbolos/tickers del título"""
        # Buscar tickers: BTC, ETH, AAPL, etc.
        tickers = re.findall(r'\b[A-Z]{2,5}\b', title)
        return tickers[:3]  # Max 3

    def _fetch_yahoo_finance_image(self, title: str, summary: str) -> Optional[str]:
        """
        Busca imagen relacionada con la noticia en Yahoo Finance.
        Si no encuentra, retorna None.
        """
        try:
            # Extraer símbolos/keywords del título
            keywords = self._extract_keywords(title)
            
            # Buscar en Yahoo Finance
            search_url = f"https://finance.yahoo.com/quote/{keywords[0]}" if keywords else None
            
            if search_url:
                response = requests.get(search_url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
                if response.status_code == 200:
                    # Búsqueda simple de og:image en el HTML
                    # No usamos BeautifulSoup completo para evitar dependencia pesada si no está,
                    # pero si está disponible mejor. Aquí usaremos regex simple.
                    match = re.search(r'<meta property="og:image" content="([^"]+)"', response.text)
                    if match:
                        img_url = match.group(1)
                        logger.info(f"✅ Imagen encontrada en Yahoo Finance: {keywords[0]}")
                        return img_url
            
            logger.info("ℹ️ No se encontró imagen en Yahoo Finance")
            return None
            
        except Exception as e:
            logger.debug(f"⚠️ Error buscando imagen: {e}")
            return None

    def _download_yahoo_finance_image(self, image_url: str, title: str) -> Optional[str]:
        """Descarga la imagen de alta calidad"""
        try:
            if not image_url:
                return None
                
            response = requests.get(image_url, stream=True, timeout=10)
            if response.status_code == 200:
                # Sanitizar nombre
                safe_title = re.sub(r'[^a-zA-Z0-9]', '_', title)[:50]
                hash_name = hashlib.md5(title.encode()).hexdigest()[:8]
                filename = f"news_img_{safe_title}_{hash_name}.jpg"
                path = os.path.join(Config.TEMP_DIR or "temp", filename)
                
                os.makedirs(os.path.dirname(path), exist_ok=True)
                
                with open(path, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                
                logger.info(f"✅ Imagen descargada: {path}")
                return path
            return None
        except Exception as e:
            logger.warning(f"⚠️ Error descargando imagen: {e}")
            return None

    def _fetch_yahoo_finance_image_enhanced(self, title: str) -> Optional[str]:
        """Wrapper que busca y descarga la imagen"""
        img_url = self._fetch_yahoo_finance_image(title, "") # Reuse existing logic
        if img_url:
             # Yahoo a veces da miniaturas, intentar obtener versión HQ si es posible
             # Por ahora descargamos lo que hay
             return self._download_yahoo_finance_image(img_url, title)
        return None

    def _format_professional_news_message(self, news: dict, has_image: bool) -> str:
        """Formatea mensaje de noticia de forma profesional y atractiva"""
        category = news.get('category', 'crypto')
        title = news.get('title', '')
        summary = news.get('summary', '')
        score = news.get('relevance_score', 0)
        
        # Emoji según categoría
        if category == 'crypto':
            emoji_header = "🪙"
        elif category == 'markets':
            emoji_header = "📈"
        elif category == 'signals':
            emoji_header = "🎯"
        else:
            emoji_header = "📰"
        
        # Relevancia visual
        relevance_stars = "⭐" * min(score, 10)
        
        # Mapeo de fuente
        source = news.get('source', 'Web')
        if source == 'Google News':
             source = 'Google News / ' + news.get('url', '')[:20] + '...'
        
        message = f"""{emoji_header} **NOTICIA {category.upper()}**

📌 **{title}**

{summary}

{'📊 Relevancia: ' + relevance_stars + f' ({score}/10)' if score > 0 else ''}

🔗 Fuente: {source}"""
        
        return message.strip()

    def _format_twitter_news(self, news: dict) -> str:
        """Formatea para Twitter (max 280 chars) de forma atractiva"""
        category = news.get('category', 'crypto')
        title = news.get('title', '')
        score = news.get('relevance_score', 0)
        
        emoji = "🪙" if category == 'crypto' else "📈" if category == 'markets' else "📰"
        
        # Título truncado inteligente
        max_title = 200
        if len(title) > max_title:
            title = title[:max_title] + "..."
        
        tweet = f"{emoji} {title}\n\n"
        
        # Relevancia
        if score >= 8:
            tweet += "⚡ Alta relevancia\n"
        
        tweet += f"📍 Fuente: {news.get('source', 'Web')}"
        
        return tweet[:280]

    def publish_news(self, news: Dict):
        """
        Publica noticia en Twitter y Telegram.
        
        Args:
            news: Diccionario con datos de la noticia
        """
        try:
            # 0. Buscar imagen (Enhanced)
            image_path = self._fetch_yahoo_finance_image_enhanced(news['title'])
            
            # 1. Publicar en Twitter (usando path local)
            if self.twitter:
                logger.info("📝 Publicando en Twitter...")
                tweet_text = self._format_twitter_news(news)
                ok = self.twitter.post_tweet(tweet_text, image_path=image_path, category='news')
                news['published_twitter'] = bool(ok)
                if not ok:
                    if getattr(self.twitter, "last_reason", None) == "duplicate":
                        logger.info("⏭️ Noticia duplicada en Twitter, saltando publicación")
                    else:
                        logger.error("❌ Falló la publicación en Twitter para esta noticia")
            
            # 2. Publicar en Telegram con routing
            if self.telegram:
                # Clasificar categoría si no viene definida
                if news.get('category') == 'general' or not news.get('category'):
                    classification = self.ai_analyzer.classify_news_category(news['title'], news.get('summary', ''))
                    category = classification.get('category', 'crypto').lower()
                    news['category'] = category
                    logger.info(f"� Clasificación IA: {category} (confianza {classification.get('confidence', 0)}/10)")
                
                category = news.get('category', 'crypto').lower()
                
                # Definir grupo destino
                target_group = None
                if category == 'signals':
                    target_group = Config.TELEGRAM_GROUP_SIGNALS
                elif category == 'markets' or category == 'stocks' or category == 'forex':
                     target_group = Config.TELEGRAM_GROUP_MARKETS
                else: # crypto, bitcoin, ethereum
                     target_group = Config.TELEGRAM_GROUP_CRYPTO
                
                # Mensaje profesional
                telegram_text = self._format_professional_news_message(news, has_image=bool(image_path))
                
                # Enviar
                if target_group:
                    self.telegram.send_to_specific_group(telegram_text, target_group, image_path=image_path)
                else:
                    # Fallback a lógica antigua si no hay grupo específico
                    if category == 'markets':
                        self.telegram.send_market_message(telegram_text, image_path=image_path)
                    elif category == 'signals':
                        self.telegram.send_signal_message(telegram_text, image_path=image_path)
                    else:
                        self.telegram.send_crypto_message(telegram_text, image_path=image_path)
                
                news['published_telegram'] = True
            
            # Guardar en DB
            self.save_news(news)
            
            logger.info(f"✅ Noticia publicada: {news['title'][:50]}...")
            
        except Exception as e:
            logger.error(f"❌ Error publicando noticia: {e}")
    
    def run_news_scraping_cycle(self) -> int:
        """
        Ejecuta un ciclo completo de scraping de noticias.
        
        Returns:
            Número de noticias publicadas
        """
        try:
            start_time = time.time()
            logger.info("\n" + "=" * 60)
            logger.info(f"📰 SCRAPING DE NOTICIAS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 60 + "\n")
            
            all_news = []
            all_news.extend(self.fetch_cryptopanic_news())
            all_news.extend(self.fetch_google_news())
            
            logger.info(f"📊 Total de noticias obtenidas: {len(all_news)}")
            
            unique_news: List[Dict] = []
            seen_hashes = set()
            for news in all_news:
                h = news['hash']
                if h in seen_hashes:
                    continue
                if self.is_news_published(h):
                    continue
                unique_news.append(news)
                seen_hashes.add(h)
            
            logger.info(f"📊 Noticias únicas (no publicadas): {len(unique_news)}")
            
            relevant_news: List[Dict] = []
            ai_calls = 0
            for news in unique_news:
                if ai_calls >= self.max_ai_calls_per_cycle:
                    break
                filtered = self.filter_news_by_relevance(news)
                if filtered:
                    relevant_news.append(filtered)
                ai_calls += 1
                time.sleep(1)
            
            logger.info(f"📊 Noticias relevantes (score ≥{self.min_relevance_score}): {len(relevant_news)}")
            
            # 4. Publicar noticias relevantes
            published_count = 0
            
            for news in relevant_news[:3]:  # Máximo 3 noticias por ciclo
                self.publish_news(news)
                published_count += 1
                time.sleep(20)
            
            elapsed_time = time.time() - start_time
            logger.info("\n" + "=" * 60)
            logger.info("✅ SCRAPING DE NOTICIAS COMPLETADO")
            logger.info(f"⏱  Tiempo total: {elapsed_time:.2f} segundos")
            logger.info(f"📰 Noticias publicadas: {published_count}")
            logger.info("=" * 60 + "\n")
            
            return published_count
            
        except Exception as e:
            logger.error(f"❌ Error en ciclo de scraping: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return 0

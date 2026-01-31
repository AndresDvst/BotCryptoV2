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


class NewsService:
    """Servicio para scraping y filtrado de noticias de crypto y mercados"""
    
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
        
        Args:
            news_hash: Hash de la noticia
            
        Returns:
            True si ya fue publicada
        """
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
            logger.warning(f"⚠️ Error verificando noticia en DB: {e}")
            return False
    
    def save_news(self, news: Dict):
        """
        Guarda noticia en la base de datos.
        
        Args:
            news: Diccionario con datos de la noticia
        """
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
            
        except Exception as e:
            logger.warning(f"⚠️ Error guardando noticia en DB: {e}")
    
    def fetch_cryptopanic_news(self) -> List[Dict]:
        """
        Obtiene noticias de CryptoPanic API.
        
        Returns:
            Lista de noticias
        """
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
            else:
                logger.warning(f"⚠️ CryptoPanic API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo noticias de CryptoPanic: {e}")
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
    
    def publish_news(self, news: Dict):
        """
        Publica noticia en Twitter y Telegram.
        
        Args:
            news: Diccionario con datos de la noticia
        """
        try:
            # Emojis por categoría
            emoji_map = {
                'crypto': '🪙',
                'bitcoin': '₿',
                'ethereum': '⟠',
                'stocks': '📈',
                'forex': '💱',
                'general': '📰'
            }
            
            emoji = emoji_map.get(news['category'], '📰')
            score = news.get('relevance_score', 0)
            
            # Tweet
            tweet_text = f"{emoji} NOTICIA IMPORTANTE\n\n"
            tweet_text += f"{news['title']}\n\n"
            
            # Acortar URL si es muy larga
            url = news['url']
            if len(url) > 100:
                url = url[:100] + "..."
            
            tweet_text += f"🔗 {url}\n\n"
            tweet_text += f"⭐ Relevancia: {score}/10\n"
            tweet_text += f"#Crypto #News #{news['category'].capitalize()}"
            
            # Limitar a 280 caracteres
            if len(tweet_text) > 280:
                tweet_text = tweet_text[:277] + "..."
            
            logger.info("📝 Publicando en Twitter...")
            self.twitter.post_tweet(tweet_text)
            news['published_twitter'] = True
            
            # Telegram con enrutamiento por categoría usando IA
            telegram_text = f"{emoji} <b>NOTICIA IMPORTANTE</b>\n\n"
            telegram_text += f"<b>{news['title']}</b>\n\n"
            telegram_text += f"🔗 <a href='{news['url']}'>Leer más</a>\n\n"
            telegram_text += f"⭐ Relevancia: {score}/10\n"
            telegram_text += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            classification = self.ai_analyzer.classify_news_category(news['title'], news.get('summary', ''))
            category = classification.get('category', news.get('category', 'crypto'))
            logger.info(f"📬 Clasificación IA: {category} (confianza {classification.get('confidence', 0)}/10)")
            
            if category == 'markets':
                self.telegram.send_market_message(telegram_text)
            elif category == 'signals':
                self.telegram.send_signal_message(telegram_text)
            else:
                self.telegram.send_crypto_message(telegram_text)
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

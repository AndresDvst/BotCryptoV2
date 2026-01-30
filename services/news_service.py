"""
Servicio de Scraping de Noticias en Tiempo Real.
Integra CryptoPanic API y Google News RSS con filtro de relevancia por IA.
"""
import feedparser
import hashlib
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from utils.logger import logger
from services.ai_analyzer_service import AIAnalyzerService
from services.telegram_service import TelegramService
from services.twitter_service import TwitterService
from database.mysql_manager import MySQLManager
import time


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
            
            all_news = []
            
            for feed_url in self.google_news_feeds:
                try:
                    feed = feedparser.parse(feed_url)
                    
                    for entry in feed.entries[:5]:  # 5 noticias por feed
                        news = {
                            'title': entry.get('title', ''),
                            'url': entry.get('link', ''),
                            'source': 'Google News',
                            'category': self._categorize_from_url(feed_url),
                            'published_at': entry.get('published', '')
                        }
                        news['hash'] = self.get_news_hash(news['title'], news['url'])
                        all_news.append(news)
                    
                    time.sleep(1)  # Evitar rate limits
                    
                except Exception as e:
                    logger.warning(f"⚠️ Error con feed {feed_url}: {e}")
                    continue
            
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
    
    def filter_news_by_relevance(self, news: Dict) -> Optional[Dict]:
        """
        Filtra noticia por relevancia usando IA.
        
        Args:
            news: Diccionario con datos de la noticia
            
        Returns:
            Noticia con score de relevancia o None si no es relevante
        """
        try:
            # Crear prompt para Gemini
            prompt = f"""
Analiza la siguiente noticia y asigna un score de relevancia del 1 al 10.

Criterios:
- 10: Noticia extremadamente importante (crash, regulación mayor, hack grande)
- 7-9: Noticia muy relevante (movimientos significativos, anuncios importantes)
- 4-6: Noticia moderadamente relevante
- 1-3: Noticia poco relevante o clickbait

Título: {news['title']}
Categoría: {news['category']}

Responde SOLO con un número del 1 al 10, sin explicación.
"""
            
            # Obtener score de Gemini
            response = self.ai_analyzer.analyze_text(prompt)
            
            # Extraer número
            try:
                score = int(response.strip())
                score = max(1, min(10, score))  # Limitar entre 1-10
            except:
                score = 5  # Score por defecto si falla el parsing
            
            news['relevance_score'] = score
            
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
            
            classification = self.ai_analyzer.classify_news_category(news['title'], summary)
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
            
            # 1. Obtener noticias de todas las fuentes
            all_news = []
            all_news.extend(self.fetch_cryptopanic_news())
            all_news.extend(self.fetch_google_news())
            
            logger.info(f"📊 Total de noticias obtenidas: {len(all_news)}")
            
            # 2. Filtrar duplicados
            unique_news = []
            seen_hashes = set()
            
            for news in all_news:
                if news['hash'] not in seen_hashes and not self.is_news_published(news['hash']):
                    unique_news.append(news)
                    seen_hashes.add(news['hash'])
            
            logger.info(f"📊 Noticias únicas (no publicadas): {len(unique_news)}")
            
            # 3. Filtrar por relevancia con IA
            relevant_news = []
            
            for news in unique_news[:10]:  # Limitar a 10 para no saturar IA
                filtered = self.filter_news_by_relevance(news)
                if filtered:
                    relevant_news.append(filtered)
                time.sleep(2)  # Evitar rate limits de Gemini
            
            logger.info(f"📊 Noticias relevantes (score ≥{self.min_relevance_score}): {len(relevant_news)}")
            
            # 4. Publicar noticias relevantes
            published_count = 0
            
            for news in relevant_news[:3]:  # Máximo 3 noticias por ciclo
                self.publish_news(news)
                published_count += 1
                time.sleep(30)  # Esperar entre publicaciones
            
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

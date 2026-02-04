#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Twitter Engagement Service - Enhanced Version
Handles automated engagement (likes and AI-powered comments) on Twitter feed
with advanced anti-detection, rate limiting, and human-like behavior
"""

import time
import random
import re
from typing import List, Dict, Optional, Tuple
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

from utils.logger import logger
from utils.security import sanitize_exception
from config.config import Config
from config.twitter_comments import FALLBACK_COMMENTS_SPANISH, FALLBACK_COMMENTS_ENGLISH


class TwitterEngagementService:
    """Service for automated Twitter engagement (likes and comments)"""
    
    def __init__(self, driver, ai_service=None, db=None):
        """
        Initialize Twitter Engagement Service
        
        Args:
            driver: Selenium WebDriver instance (already logged in)
            ai_service: AI service for generating comments
            db: Database instance for tracking engagement
        """
        self.driver = driver
        self.ai_service = ai_service
        self.db = db
        self.engaged_tweets = set()  # Track tweets we've already engaged with
        
        # Rate limiting
        self.inicio_sesion = time.time()
        self.likes_dados_sesion = 0
        self.comments_dados_sesion = 0
        self.max_likes_per_hour = Config.TWITTER_MAX_LIKES * 6  # 10 likes * 6 = 60/hora
        self.max_comments_per_hour = Config.TWITTER_MAX_COMMENTS * 6  # 5 comments * 6 = 30/hora
        
        # Anti-detección CDP
        self._setup_anti_detection()
        
        logger.info("✅ TwitterEngagementService inicializado con anti-detección")
        
    def _setup_anti_detection(self):
        """Configura anti-detección avanzada con CDP"""
        try:
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                '''
            })
            logger.debug("✅ Anti-detección CDP configurada")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo configurar anti-detección CDP: {e}")
    
    def _human_delay(self, min_seconds: float = 1, max_seconds: float = 3):
        """
        Pausa con distribución gaussiana para simular comportamiento humano
        
        Args:
            min_seconds: Tiempo mínimo de pausa
            max_seconds: Tiempo máximo de pausa
        """
        # Distribución normal (más humano que uniform)
        media = (min_seconds + max_seconds) / 2
        std_dev = (max_seconds - min_seconds) / 4
        
        pausa = random.gauss(media, std_dev)
        pausa = max(min_seconds, min(max_seconds, pausa))  # Clamp
        
        time.sleep(pausa)
    
    def _verificar_rate_limit_likes(self) -> bool:
        """Verifica si se alcanzó el límite de likes por hora"""
        tiempo_transcurrido = time.time() - self.inicio_sesion
        horas_transcurridas = tiempo_transcurrido / 3600
        
        if horas_transcurridas > 0:
            likes_por_hora = self.likes_dados_sesion / horas_transcurridas
            
            if likes_por_hora > self.max_likes_per_hour:
                logger.warning(
                    f"⚠️ Rate limit de LIKES alcanzado: {likes_por_hora:.1f} likes/hora "
                    f"(máximo: {self.max_likes_per_hour})"
                )
                return True
        
        return False
    
    def _verificar_rate_limit_comments(self) -> bool:
        """Verifica si se alcanzó el límite de comentarios por hora"""
        tiempo_transcurrido = time.time() - self.inicio_sesion
        horas_transcurridas = tiempo_transcurrido / 3600
        
        if horas_transcurridas > 0:
            comments_por_hora = self.comments_dados_sesion / horas_transcurridas
            
            if comments_por_hora > self.max_comments_per_hour:
                logger.warning(
                    f"⚠️ Rate limit de COMENTARIOS alcanzado: {comments_por_hora:.1f} comments/hora "
                    f"(máximo: {self.max_comments_per_hour})"
                )
                return True
        
        return False
    
    def scroll_feed(self, num_scrolls: int = 3) -> bool:
        """
        Scroll through Twitter feed to load more tweets with variable distance
        
        Args:
            num_scrolls: Number of times to scroll
            
        Returns:
            True if successful
        """
        try:
            logger.info(f"📜 Haciendo scroll en el feed ({num_scrolls} veces)...")
            
            for i in range(num_scrolls):
                # Scroll con distancia variable (más humano)
                distancia = random.randint(600, 1000)
                self.driver.execute_script(f"window.scrollBy(0, {distancia});")
                
                # Pausa gaussiana
                self._human_delay(1, 2)
                
                logger.debug(f"✅ Scroll {i+1}/{num_scrolls} ({distancia}px)")
            
            logger.info("✅ Scroll completado")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error haciendo scroll: {sanitize_exception(e)}")
            return False
    
    def find_tweets_in_viewport(self) -> List:
        """
        Find all tweet elements currently visible in viewport
        
        Returns:
            List of tweet elements
        """
        try:
            # Selector para artículos de tweets
            tweets = self.driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="tweet"]')
            
            # Filtrar solo tweets visibles
            visible_tweets = []
            for tweet in tweets:
                try:
                    if tweet.is_displayed():
                        visible_tweets.append(tweet)
                except StaleElementReferenceException:
                    continue
            
            logger.debug(f"🔍 Encontrados {len(visible_tweets)} tweets visibles")
            return visible_tweets
            
        except Exception as e:
            logger.error(f"❌ Error buscando tweets: {sanitize_exception(e)}")
            return []
    
    def get_tweet_id(self, tweet_element) -> Optional[str]:
        """
        Extract tweet ID from tweet element
        
        Args:
            tweet_element: Selenium WebElement of tweet
            
        Returns:
            Tweet ID or None
        """
        try:
            # Intentar obtener el ID del link del tweet
            link = tweet_element.find_element(By.CSS_SELECTOR, 'a[href*="/status/"]')
            href = link.get_attribute('href')
            
            # Extraer ID del URL (formato: /username/status/1234567890)
            match = re.search(r'/status/(\d+)', href)
            if match:
                return match.group(1)
            
            return None
            
        except Exception:
            return None
    
    def is_already_engaged(self, tweet_id: str) -> bool:
        """
        Check if we've already engaged with this tweet
        
        Args:
            tweet_id: Tweet ID
            
        Returns:
            True if already engaged
        """
        if tweet_id in self.engaged_tweets:
            return True
        
        # Check database if available
        if self.db:
            try:
                result = self.db.execute_query(
                    "SELECT COUNT(*) FROM twitter_engagement WHERE tweet_id = ?",
                    (tweet_id,)
                )
                if result and result[0][0] > 0:
                    return True
            except Exception:
                pass
        
        return False
    
    def like_tweet(self, tweet_element) -> bool:
        """
        Like a tweet
        
        Args:
            tweet_element: Selenium WebElement of tweet
            
        Returns:
            True if successful
        """
        try:
            # Buscar botón de like
            like_button = tweet_element.find_element(By.CSS_SELECTOR, 'button[data-testid="like"]')
            
            # Verificar si ya está likeado (aria-label contiene "Unlike")
            aria_label = like_button.get_attribute('aria-label') or ''
            if 'Unlike' in aria_label or 'Quitar me gusta' in aria_label:
                logger.debug("⏭️ Tweet ya tiene like, saltando...")
                return False
            
            # Click en like
            like_button.click()
            logger.debug("👍 Like dado exitosamente")
            
            return True
            
        except NoSuchElementException:
            logger.debug("⚠️ Botón de like no encontrado")
            return False
        except Exception as e:
            logger.debug(f"⚠️ Error dando like: {str(e)[:50]}")
            return False
    
    def extract_tweet_content(self, tweet_element) -> Optional[str]:
        """
        Extract text content from tweet
        
        Args:
            tweet_element: Selenium WebElement of tweet
            
        Returns:
            Tweet text or None
        """
        try:
            # Buscar el texto del tweet
            text_element = tweet_element.find_element(By.CSS_SELECTOR, 'div[data-testid="tweetText"]')
            text = text_element.text.strip()
            
            return text if text else None
            
        except NoSuchElementException:
            logger.debug("⚠️ Texto del tweet no encontrado")
            return None
        except Exception as e:
            logger.debug(f"⚠️ Error extrayendo texto: {str(e)[:50]}")
            return None
    
    def detect_language(self, text: str) -> str:
        """
        Detect if text is in English or Spanish
        
        Args:
            text: Text to analyze
            
        Returns:
            'english' or 'spanish'
        """
        # Palabras comunes en español
        spanish_words = ['el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'ser', 'se', 'no', 'haber', 'por', 'con', 'su', 'para', 'como', 'estar', 'tener', 'le', 'lo', 'todo', 'pero', 'más', 'hacer', 'o', 'poder', 'decir', 'este', 'ir', 'otro', 'ese', 'la', 'si', 'me', 'ya', 'ver', 'porque', 'dar', 'cuando', 'él', 'muy', 'sin', 'vez', 'mucho', 'saber', 'qué', 'sobre', 'mi', 'alguno', 'mismo', 'yo', 'también', 'hasta', 'año', 'dos', 'querer', 'entre', 'así', 'primero', 'desde', 'grande', 'eso', 'ni', 'nos', 'llegar', 'pasar', 'tiempo', 'ella', 'sí', 'día', 'uno', 'bien', 'poco', 'deber', 'entonces', 'poner', 'cosa', 'tanto', 'hombre', 'parecer', 'nuestro', 'tan', 'donde', 'ahora', 'parte', 'después', 'vida', 'quedar', 'siempre', 'creer', 'hablar', 'llevar', 'dejar', 'nada', 'cada', 'seguir', 'menos', 'nuevo', 'encontrar', 'algo', 'solo', 'decir', 'mundo', 'país', 'contra', 'aquí', 'casa', 'último', 'salir', 'público', 'llegar', 'mayor', 'tal', 'cual', 'sea', 'trabajar', 'niño', 'siguiente', 'durante', 'siglo', 'volver', 'mano', 'incluso', 'fin', 'conseguir', 'sistema', 'tres', 'cómo', 'antes', 'propio', 'tarde', 'mejor', 'nuevo', 'tener', 'puerta', 'ejemplo', 'buscar', 'momento', 'manera', 'propia', 'gente', 'punto', 'gobierno', 'caso', 'número', 'agua', 'hacerse', 'segundo', 'cierto', 'vez', 'verdad', 'problema', 'mí', 'cuerpo', 'conocer', 'igual', 'realizar', 'muerte', 'producir', 'sentir', 'cuatro', 'dentro', 'nadie', 'historia', 'medio', 'mil', 'afirmar', 'tratar', 'teoría', 'mano', 'ciudad', 'calle', 'leer', 'presidente', 'sólo', 'tal', 'mayor', 'éste', 'tipo', 'obra', 'aunque', 'hacia', 'largo', 'siempre', 'proceso', 'hijo', 'cuenta', 'nombre', 'dado', 'grupo', 'través', 'bajo', 'ley', 'nivel', 'tiempo', 'condición', 'programa', 'presentar', 'crear', 'saber', 'fuerza', 'educación', 'lejos', 'llegar', 'utilizar', 'tierra', 'padre', 'entrar', 'médico', 'unidad', 'exigir', 'viejo', 'tomar', 'tema', 'orden', 'comprender', 'falta', 'propio', 'mismo', 'hecho', 'mujer', 'venir', 'razón', 'esperar', 'miembro', 'además', 'poder', 'policía', 'importante', 'pregunta', 'realizar', 'árbol', 'madre', 'los', 'las', 'del', 'al', 'esta', 'estos', 'estas']
        
        text_lower = text.lower()
        words = text_lower.split()
        
        # Contar palabras en español
        spanish_count = sum(1 for word in words if word in spanish_words)
        
        # Si más del 20% son palabras en español, es español
        if len(words) > 0 and (spanish_count / len(words)) > 0.2:
            return 'spanish'
        
        return 'english'
    
    def generate_comment(self, tweet_text: str, language: str) -> Optional[str]:
        """
        Generate AI-powered contextual comment
        
        Args:
            tweet_text: Text of the tweet to comment on
            language: 'english' or 'spanish'
            
        Returns:
            Generated comment or None
        """
        if not self.ai_service:
            logger.warning("⚠️ AI service no disponible, usando comentarios predefinidos")
            # Usar comentarios predefinidos importados
            return random.choice(FALLBACK_COMMENTS_SPANISH if language == 'spanish' else FALLBACK_COMMENTS_ENGLISH)
        
        try:
            # Crear prompt para la IA
            lang_name = "español" if language == 'spanish' else "English"
            
            prompt = f"""Analiza este tweet y genera un comentario breve y atractivo.

Tweet: "{tweet_text}"

Requisitos:
- Sé amigable y profesional
- Máximo 80 caracteres
- Responde en {lang_name}
- Evita temas controversiales
- Sé relevante al contenido
- Usa 1 emoji apropiado al final
- NO uses hashtags
- NO hagas preguntas

Genera SOLO el comentario, sin explicaciones adicionales."""

            # Llamar a la IA (usa fallback automático: Gemini -> OpenRouter)
            response = self.ai_service._generate_content(prompt, max_tokens=150)
            
            # Verificar si la respuesta es válida (no es un error)
            if response and len(response.strip()) > 0 and "Error:" not in response and "fallaron" not in response:
                comment = response.strip()
                
                # Limitar a 100 caracteres por seguridad
                if len(comment) > 100:
                    comment = comment[:97] + "..."
                
                logger.debug(f"✅ Comentario generado con IA: {comment[:30]}...")
                return comment
            else:
                # Si la IA falló, usar comentarios predefinidos
                logger.warning("⚠️ IA no disponible o devolvió error, usando comentarios predefinidos")
                fallback = random.choice(FALLBACK_COMMENTS_SPANISH if language == 'spanish' else FALLBACK_COMMENTS_ENGLISH)
                logger.debug(f"💬 Comentario predefinido: {fallback}")
                return fallback
            
        except Exception as e:
            logger.error(f"❌ Error generando comentario con IA: {sanitize_exception(e)}")
            logger.info("💬 Usando comentario predefinido como respaldo")
            return random.choice(FALLBACK_COMMENTS_SPANISH if language == 'spanish' else FALLBACK_COMMENTS_ENGLISH)
    
    def comment_on_tweet(self, tweet_element, comment_text: str) -> bool:
        """
        Post a comment on a tweet
        
        Args:
            tweet_element: Selenium WebElement of tweet
            comment_text: Text to comment
            
        Returns:
            True if successful
        """
        try:
            # Click en botón de comentar
            reply_button = tweet_element.find_element(By.CSS_SELECTOR, 'button[data-testid="reply"]')
            reply_button.click()
            
            logger.debug("💬 Abriendo diálogo de comentario...")
            self._human_delay(1, 2)
            
            # Esperar a que aparezca el cuadro de texto
            try:
                comment_box = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="tweetTextarea_0"]'))
                )
            except TimeoutException:
                logger.warning("⚠️ Cuadro de comentario no apareció")
                return False
            
            # Escribir comentario carácter por carácter (como en post_tweet)
            logger.debug(f"⌨️ Escribiendo comentario: {comment_text[:30]}...")
            
            for char in comment_text:
                try:
                    if char == '\n':
                        comment_box.send_keys(Keys.SHIFT, Keys.ENTER)
                    else:
                        comment_box.send_keys(char)
                    time.sleep(random.uniform(0.02, 0.05))
                except Exception:
                    continue
            
            self._human_delay(0.5, 1)
            
            # Buscar y hacer click en botón "Reply"
            try:
                post_button = self.driver.find_element(By.CSS_SELECTOR, 'button[data-testid="tweetButton"]')
                post_button.click()
                
                logger.debug("✅ Comentario publicado exitosamente")
                self._human_delay(2, 3)
                
                return True
                
            except NoSuchElementException:
                logger.warning("⚠️ Botón de publicar comentario no encontrado")
                # Intentar cerrar el diálogo con ESC
                comment_box.send_keys(Keys.ESCAPE)
                return False
            
        except NoSuchElementException:
            logger.debug("⚠️ Botón de comentar no encontrado")
            return False
        except Exception as e:
            logger.debug(f"⚠️ Error comentando: {str(e)[:50]}")
            return False
    
    def engage_with_feed(self, max_likes: int = 10, max_comments: int = 5) -> Dict:
        """
        Main engagement function - like and comment on tweets with advanced features
        
        Args:
            max_likes: Maximum number of tweets to like
            max_comments: Maximum number of tweets to comment on
            
        Returns:
            Dictionary with engagement statistics
        """
        logger.info("🐦 Iniciando engagement en Twitter feed...")
        logger.info(f"   📊 Objetivo: {max_likes} likes, {max_comments} comentarios")
        
        stats = {
            'likes_given': 0,
            'comments_posted': 0,
            'tweets_processed': 0,
            'tweets_skipped': 0,
            'errors': 0
        }
        
        try:
            # Ir al feed de inicio
            logger.info("🏠 Navegando a feed de inicio...")
            self.driver.get("https://x.com/home")
            self._human_delay(3, 5)
            
            # Hacer scroll para cargar tweets
            self.scroll_feed(num_scrolls=3)
            
            # Obtener tweets visibles
            tweets = self.find_tweets_in_viewport()
            logger.info(f"✅ Encontrados {len(tweets)} tweets para procesar")
            
            tweet_index = 0
            
            while (stats['likes_given'] < max_likes or stats['comments_posted'] < max_comments) and tweet_index < len(tweets):
                try:
                    # Verificar rate limits
                    if stats['likes_given'] < max_likes and self._verificar_rate_limit_likes():
                        logger.warning("⏸️ Pausando likes por rate limit (60s)...")
                        time.sleep(60)
                    
                    if stats['comments_posted'] < max_comments and self._verificar_rate_limit_comments():
                        logger.warning("⏸️ Pausando comentarios por rate limit (60s)...")
                        time.sleep(60)
                    
                    tweet = tweets[tweet_index]
                    stats['tweets_processed'] += 1
                    
                    # Scroll suave hacia el tweet
                    try:
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", 
                            tweet
                        )
                        self._human_delay(1.0, 2.0)
                    except:
                        pass
                    
                    # Obtener ID del tweet
                    tweet_id = self.get_tweet_id(tweet)
                    if not tweet_id:
                        logger.debug("⏭️ No se pudo obtener ID del tweet, saltando...")
                        tweet_index += 1
                        continue
                    
                    # Verificar si ya interactuamos con este tweet
                    if self.is_already_engaged(tweet_id):
                        logger.debug(f"⏭️ Tweet {tweet_id} ya procesado, saltando...")
                        tweet_index += 1
                        continue
                    
                    # Dar like si aún no alcanzamos el máximo
                    if stats['likes_given'] < max_likes:
                        if self.like_tweet(tweet):
                            stats['likes_given'] += 1
                            self.likes_dados_sesion += 1
                            self.engaged_tweets.add(tweet_id)
                            
                            # Guardar en base de datos
                            if self.db:
                                try:
                                    self.db.execute_query(
                                        "INSERT OR IGNORE INTO twitter_engagement (tweet_id, action) VALUES (?, ?)",
                                        (tweet_id, 'like')
                                    )
                                except Exception:
                                    pass
                            
                            logger.info(f"👍 Like {stats['likes_given']}/{max_likes} dado")
                            
                            # Delay post-like con distribución gaussiana
                            self._human_delay(
                                Config.TWITTER_ENGAGEMENT_DELAY_MIN, 
                                Config.TWITTER_ENGAGEMENT_DELAY_MAX
                            )
                            
                            # SALTO DE PUBLICACIONES (comportamiento humano)
                            saltos = random.randint(2, 5)
                            logger.debug(f"⏭️ Saltando {saltos} publicaciones...")
                            stats['tweets_skipped'] += saltos
                            tweet_index += saltos
                            continue
                    
                    # Comentar si aún no alcanzamos el máximo
                    if stats['comments_posted'] < max_comments:
                        # Extraer texto del tweet
                        tweet_text = self.extract_tweet_content(tweet)
                        
                        if tweet_text:
                            # Detectar idioma
                            language = self.detect_language(tweet_text)
                            logger.debug(f"🌐 Idioma detectado: {language}")
                            
                            # Generar comentario con IA
                            comment = self.generate_comment(tweet_text, language)
                            
                            if comment:
                                if self.comment_on_tweet(tweet, comment):
                                    stats['comments_posted'] += 1
                                    self.comments_dados_sesion += 1
                                    
                                    # Guardar en base de datos
                                    if self.db:
                                        try:
                                            self.db.execute_query(
                                                "INSERT OR IGNORE INTO twitter_engagement (tweet_id, action, comment_text) VALUES (?, ?, ?)",
                                                (tweet_id, 'comment', comment)
                                            )
                                        except Exception:
                                            pass
                                    
                                    logger.info(f"💬 Comentario {stats['comments_posted']}/{max_comments} publicado: {comment[:50]}...")
                                    
                                    # Delay post-comment más largo
                                    self._human_delay(
                                        Config.TWITTER_COMMENT_DELAY_MIN, 
                                        Config.TWITTER_COMMENT_DELAY_MAX
                                    )
                                    
                                    # SALTO DE PUBLICACIONES después de comentar
                                    saltos = random.randint(3, 7)
                                    logger.debug(f"⏭️ Saltando {saltos} publicaciones...")
                                    stats['tweets_skipped'] += saltos
                                    tweet_index += saltos
                                    continue
                    
                    # Avanzar al siguiente tweet
                    tweet_index += 1
                    
                except StaleElementReferenceException:
                    logger.debug("⚠️ Elemento obsoleto, continuando...")
                    tweet_index += 1
                    continue
                except Exception as e:
                    stats['errors'] += 1
                    logger.debug(f"⚠️ Error procesando tweet: {str(e)[:50]}")
                    tweet_index += 1
                    continue
            
            # Resumen final
            logger.info("\n" + "="*60)
            logger.info("📊 RESUMEN DE ENGAGEMENT")
            logger.info("="*60)
            logger.info(f"👍 Likes dados: {stats['likes_given']}/{max_likes}")
            logger.info(f"💬 Comentarios publicados: {stats['comments_posted']}/{max_comments}")
            logger.info(f"📝 Tweets procesados: {stats['tweets_processed']}")
            logger.info(f"⏭️ Tweets saltados: {stats['tweets_skipped']}")
            logger.info(f"❌ Errores: {stats['errors']}")
            logger.info(f"⏱️ Likes/hora actual: {(self.likes_dados_sesion / ((time.time() - self.inicio_sesion) / 3600)):.1f}")
            logger.info(f"⏱️ Comments/hora actual: {(self.comments_dados_sesion / ((time.time() - self.inicio_sesion) / 3600)):.1f}")
            logger.info("="*60)
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error en engagement: {sanitize_exception(e)}")
            stats['errors'] += 1
            return stats

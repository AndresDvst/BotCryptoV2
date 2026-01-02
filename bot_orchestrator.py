"""
Orquestador principal del bot de criptomonedas.
Coordina todos los servicios y ejecuta el flujo completo del análisis.
"""
from services.binance_service import BinanceService
from services.bybit_service import BybitService
from services.market_sentiment_service import MarketSentimentService
from services.ai_analyzer_service import AIAnalyzerService
from services.telegram_service import TelegramService
from services.twitter_service import TwitterService
from config.config import Config
from utils.logger import logger
from datetime import datetime, timedelta
import time

class CryptoBotOrchestrator:
    """Orquestador principal que coordina todos los servicios"""
    
    def __init__(self):
        """Inicializa todos los servicios necesarios"""
        logger.info("=" * 60)
        logger.info("🤖 INICIANDO CRYPTO BOT")
        logger.info("=" * 60)
        
        try:
            # Validar configuración
            Config.validate()
            
            # Inicializar servicios
            self.binance = BinanceService()
            self.bybit = BybitService()
            self.market_sentiment = MarketSentimentService()
            self.ai_analyzer = AIAnalyzerService()
            self.telegram = TelegramService()
            self.twitter = TwitterService()

            # Intentar login automático en Twitter si hay credenciales en la configuración
            if getattr(Config, 'TWITTER_USERNAME', None) and getattr(Config, 'TWITTER_PASSWORD', None):
                try:
                    login_ok = self.twitter.login_twitter(Config.TWITTER_USERNAME, Config.TWITTER_PASSWORD)
                    if login_ok:
                        logger.info("✅ Twitter: login automático completado")
                    else:
                        logger.warning("⚠️ Twitter: login automático falló")
                except Exception as e:
                    logger.error(f"❌ Error en login automático de Twitter: {e}")
            
            logger.info("✅ Todos los servicios inicializados correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error crítico al inicializar servicios: {e}")
            raise
    
    def run_analysis_cycle(self, is_morning: bool = False) -> bool:
        """
        Ejecuta un ciclo completo de análisis.
        
        Args:
            is_morning: True si es el reporte matutino de las 6 AM
            
        Returns:
            True si el ciclo se completó exitosamente
        """
        try:
            start_time = time.time()
            logger.info("\n" + "=" * 60)
            logger.info(f"🚀 INICIANDO CICLO DE ANÁLISIS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 60 + "\n")
            
            # PASO 1: Consultar Binance y filtrar monedas
            logger.info("📊 PASO 1: Consultando Binance...")
            significant_coins = self.binance.filter_significant_changes()
            if not significant_coins:
                logger.warning("⚠️ No se encontraron monedas con cambios significativos")
                return False

            # PASO 2: Separar monedas que existen en ambos exchanges
            logger.info("\n📊 PASO 2: Comparando monedas en Binance y Bybit...")
            binance_symbols = set([coin['symbol'] for coin in significant_coins])
            try:
                bybit_markets = self.bybit.exchange.load_markets()
                bybit_symbols = set(bybit_markets.keys())
            except Exception as e:
                logger.error(f"❌ Error al cargar mercados de Bybit: {e}")
                bybit_symbols = set()

            coins_both = [coin for coin in significant_coins if coin['symbol'] in bybit_symbols]
            coins_only_binance = [coin for coin in significant_coins if coin['symbol'] not in bybit_symbols]

            # PASO 3: Consultar Bybit para cambios de 2 horas solo en las que existen en ambos
            logger.info("\n📊 PASO 3: Consultando cambios de 2h en Bybit solo para monedas que existen en ambos exchanges...")
            coins_both_enriched = self.bybit.get_2hour_change(coins_both)

            # PASO 4: Analizar sentimiento del mercado
            logger.info("\n📊 PASO 4: Analizando sentimiento del mercado...")
            market_data = self.market_sentiment.analyze_market_sentiment()

            # PASO 5: Análisis con IA
            logger.info("\n🤖 PASO 5: Analizando con IA...")
            ai_analysis = self.ai_analyzer.analyze_and_recommend(
                coins_both_enriched,
                market_data
            )

            # PASO 6: Generar resúmenes para Twitter (4 tweets: 24h y 2h)
            logger.info("\n📝 PASO 6: Generando resúmenes para Twitter (4 tweets)...")
            twitter_summaries = self.ai_analyzer.generate_twitter_4_summaries(
                market_data,
                coins_only_binance,
                coins_both_enriched,
                max_chars=280
            )

            # PASO 7: Enviar a Telegram
            logger.info("\n📱 PASO 7: Enviando reporte a Telegram...")
            telegram_success = self.telegram.send_report(
                ai_analysis,
                market_data,
                coins_only_binance,
                coins_both_enriched
            )

            # PASO 8: Publicar en Twitter (cuatro tweets)
            logger.info("\n🐦 PASO 8: Publicando en Twitter...")
            if is_morning:
                image_path = Config.MORNING_IMAGE_PATH
                logger.info("☀️ Usando imagen de reporte matutino")
            else:
                image_path = Config.REPORT_IMAGE_PATH
            logger.info("📊 Usando imagen de reporte regular")


            import time as _time
            twitter_success_up_24h = self.twitter.post_tweet(twitter_summaries["up_24h"], image_path)
            logger.info("⏳ Esperando 30 segundos para la siguiente publicación...")
            _time.sleep(30)
            twitter_success_down_24h = self.twitter.post_tweet(twitter_summaries["down_24h"], image_path)
            logger.info("⏳ Esperando 30 segundos para la siguiente publicación...")
            _time.sleep(30)
            twitter_success_up_2h = self.twitter.post_tweet(twitter_summaries["up_2h"], image_path)
            logger.info("⏳ Esperando 30 segundos para la siguiente publicación...")
            _time.sleep(30)
            twitter_success_down_2h = self.twitter.post_tweet(twitter_summaries["down_2h"], image_path)

            logger.info(f"\n📝 RESUMEN SUBIDAS 24H ({len(twitter_summaries['up_24h'])} caracteres):")
            logger.info("-" * 60)
            logger.info(twitter_summaries["up_24h"])
            logger.info("-" * 60)
            logger.info(f"\n📝 RESUMEN BAJADAS 24H ({len(twitter_summaries['down_24h'])} caracteres):")
            logger.info("-" * 60)
            logger.info(twitter_summaries["down_24h"])
            logger.info("-" * 60)
            logger.info(f"\n📝 RESUMEN SUBIDAS 2H ({len(twitter_summaries['up_2h'])} caracteres):")
            logger.info("-" * 60)
            logger.info(twitter_summaries["up_2h"])
            logger.info("-" * 60)
            logger.info(f"\n📝 RESUMEN BAJADAS 2H ({len(twitter_summaries['down_2h'])} caracteres):")
            logger.info("-" * 60)
            logger.info(twitter_summaries["down_2h"])
            logger.info("-" * 60)

            # Estadísticas finales
            elapsed_time = time.time() - start_time
            logger.info("\n" + "=" * 60)
            logger.info("✅ CICLO COMPLETADO EXITOSAMENTE")
            logger.info(f"⏱ Tiempo total: {elapsed_time:.2f} segundos")
            logger.info(f"📊 Monedas analizadas: {len(coins_both_enriched)}")
            logger.info(f"📱 Telegram: {'✅ Enviado' if telegram_success else '❌ Error'}")
            logger.info(f"🐦 Twitter: {'✅ Publicado' if twitter_success_up_24h and twitter_success_down_24h and twitter_success_up_2h and twitter_success_down_2h else '⚠️ Error'}")

            # Mostrar próxima ejecución
            next_execution = datetime.now() + timedelta(hours=Config.REPORT_INTERVAL_HOURS)
            logger.info(f"⏰ Próxima ejecución: {next_execution.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 60 + "\n")

            return True
            
            # Estadísticas finales
            elapsed_time = time.time() - start_time
            logger.info("\n" + "=" * 60)
            logger.info("✅ CICLO COMPLETADO EXITOSAMENTE")
            logger.info(f"⏱ Tiempo total: {elapsed_time:.2f} segundos")
            logger.info(f"📊 Monedas analizadas: {len(coins_both_enriched)}")
            logger.info(f"📱 Telegram: {'✅ Enviado' if telegram_success else '❌ Error'}")
            logger.info(f"🐦 Twitter: {'✅ Publicado' if twitter_success_up and twitter_success_down else '⚠️ Error'}")
            
            # Mostrar próxima ejecución
            next_execution = datetime.now() + timedelta(hours=Config.REPORT_INTERVAL_HOURS)
            logger.info(f"⏰ Próxima ejecución: {next_execution.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 60 + "\n")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en el ciclo de análisis: {e}")
            # Mostrar próxima ejecución incluso si hay error
            try:
                next_execution = datetime.now() + timedelta(hours=Config.REPORT_INTERVAL_HOURS)
                logger.info(f"⏰ Próxima ejecución programada: {next_execution.strftime('%Y-%m-%d %H:%M:%S')}")
            except:
                pass
            return False
    
    def setup_twitter_login(self, username: str, password: str):
        """
        Configura el login de Twitter (se hace una sola vez).
        
        Args:
            username: Usuario de Twitter
            password: Contraseña de Twitter
        """
        try:
            logger.info("🐦 Configurando login de Twitter...")
            success = self.twitter.login_twitter(username, password)
            
            if success:
                logger.info("✅ Twitter configurado correctamente")
            else:
                logger.error("❌ Error al configurar Twitter")
            
            return success
        except Exception as e:
            logger.error(f"❌ Error al configurar Twitter: {e}")
            return False
    
    def cleanup(self):
        """Limpia recursos y cierra conexiones"""
        logger.info("🧹 Limpiando recursos...")
        try:
            self.twitter.close()
            logger.info("✅ Recursos liberados")
        except Exception as e:
            logger.warning(f"⚠️ Error al limpiar recursos: {e}")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test module for Twitter Engagement Service
Allows testing likes and comments without running full bot cycle
"""

import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from services.twitter_service import TwitterService
from services.twitter_engagement_service import TwitterEngagementService
from services.ai_analyzer_service import AIAnalyzerService
from database.db_manager import DatabaseManager
from utils.logger import logger
from config.config import Config


def test_likes_only():
    """Test liking tweets without commenting"""
    print("\n" + "="*60)
    print("🧪 TEST: Likes Only (10 tweets)")
    print("="*60)
    
    # Inicializar servicios
    twitter = TwitterService()
    
    if not twitter.login_twitter(Config.TWITTER_USERNAME, Config.TWITTER_PASSWORD):
        print("❌ Error: No se pudo iniciar sesión en Twitter")
        return False
    
    # Crear servicio de engagement
    db = DatabaseManager()
    engagement = TwitterEngagementService(twitter.driver, ai_service=None, db=db)
    
    # Ejecutar engagement (solo likes)
    stats = engagement.engage_with_feed(max_likes=10, max_comments=0)
    
    print("\n📊 Resultados:")
    print(f"   👍 Likes: {stats['likes_given']}/10")
    print(f"   💬 Comentarios: {stats['comments_posted']}/0")
    print(f"   📝 Tweets procesados: {stats['tweets_processed']}")
    
    return stats['likes_given'] > 0


def test_comments_only():
    """Test commenting on tweets without liking"""
    print("\n" + "="*60)
    print("🧪 TEST: Comments Only (5 tweets)")
    print("="*60)
    
    # Inicializar servicios
    twitter = TwitterService()
    
    if not twitter.login_twitter(Config.TWITTER_USERNAME, Config.TWITTER_PASSWORD):
        print("❌ Error: No se pudo iniciar sesión en Twitter")
        return False
    
    # Crear servicio de engagement con IA
    db = DatabaseManager()
    ai_service = AIAnalyzerService()
    engagement = TwitterEngagementService(twitter.driver, ai_service=ai_service, db=db)
    
    # Ejecutar engagement (solo comentarios)
    stats = engagement.engage_with_feed(max_likes=0, max_comments=5)
    
    print("\n📊 Resultados:")
    print(f"   👍 Likes: {stats['likes_given']}/0")
    print(f"   💬 Comentarios: {stats['comments_posted']}/5")
    print(f"   📝 Tweets procesados: {stats['tweets_processed']}")
    
    return stats['comments_posted'] > 0


def test_full_engagement():
    """Test full engagement (likes + comments)"""
    print("\n" + "="*60)
    print("🧪 TEST: Full Engagement (10 likes + 5 comments)")
    print("="*60)
    
    # Inicializar servicios
    twitter = TwitterService()
    
    if not twitter.login_twitter(Config.TWITTER_USERNAME, Config.TWITTER_PASSWORD):
        print("❌ Error: No se pudo iniciar sesión en Twitter")
        return False
    
    # Crear servicio de engagement con IA
    db = DatabaseManager()
    ai_service = AIAnalyzerService()
    engagement = TwitterEngagementService(twitter.driver, ai_service=ai_service, db=db)
    
    # Ejecutar engagement completo
    stats = engagement.engage_with_feed(max_likes=10, max_comments=5)
    
    print("\n📊 Resultados:")
    print(f"   👍 Likes: {stats['likes_given']}/10")
    print(f"   💬 Comentarios: {stats['comments_posted']}/5")
    print(f"   📝 Tweets procesados: {stats['tweets_processed']}")
    print(f"   ❌ Errores: {stats['errors']}")
    
    return stats['likes_given'] > 0 or stats['comments_posted'] > 0


def test_ai_comment_generation():
    """Test AI comment generation with sample tweets"""
    print("\n" + "="*60)
    print("🧪 TEST: AI Comment Generation")
    print("="*60)
    
    # Tweets de ejemplo
    sample_tweets = [
        ("Bitcoin just hit a new all-time high! 🚀", "english"),
        ("El mercado de criptomonedas está en alza 📈", "spanish"),
        ("Just launched my new NFT collection! Check it out 🎨", "english"),
        ("La tecnología blockchain va a revolucionar el mundo 🌍", "spanish"),
    ]
    
    # Inicializar IA
    ai_service = AIAnalyzerService()
    engagement = TwitterEngagementService(driver=None, ai_service=ai_service, db=None)
    
    print("\n🤖 Generando comentarios con IA...\n")
    
    for tweet_text, expected_lang in sample_tweets:
        print(f"📝 Tweet: {tweet_text}")
        
        # Detectar idioma
        detected_lang = engagement.detect_language(tweet_text)
        print(f"   🌐 Idioma detectado: {detected_lang} (esperado: {expected_lang})")
        
        # Generar comentario
        comment = engagement.generate_comment(tweet_text, detected_lang)
        print(f"   💬 Comentario generado: {comment}")
        print()
    
    return True


def view_engagement_stats():
    """View engagement statistics from database"""
    print("\n" + "="*60)
    print("📊 ESTADÍSTICAS DE ENGAGEMENT")
    print("="*60)
    
    db = DatabaseManager()
    
    try:
        # Total de likes
        likes = db.execute_query(
            "SELECT COUNT(*) FROM twitter_engagement WHERE action = 'like'"
        )
        
        # Total de comentarios
        comments = db.execute_query(
            "SELECT COUNT(*) FROM twitter_engagement WHERE action = 'comment'"
        )
        
        # Últimos 10 engagement
        recent = db.execute_query(
            "SELECT tweet_id, action, comment_text, timestamp FROM twitter_engagement ORDER BY timestamp DESC LIMIT 10"
        )
        
        print(f"\n📈 Total de likes: {likes[0][0] if likes else 0}")
        print(f"💬 Total de comentarios: {comments[0][0] if comments else 0}")
        
        if recent:
            print("\n🕒 Últimos 10 engagement:")
            for row in recent:
                tweet_id, action, comment_text, timestamp = row
                if action == 'like':
                    print(f"   👍 Like en tweet {tweet_id} - {timestamp}")
                else:
                    comment_preview = comment_text[:50] + "..." if len(comment_text) > 50 else comment_text
                    print(f"   💬 Comentario en tweet {tweet_id}: {comment_preview} - {timestamp}")
        
    except Exception as e:
        print(f"❌ Error obteniendo estadísticas: {e}")
    
    return True


def main():
    """Main test menu"""
    print("\n" + "="*60)
    print("🐦 TWITTER ENGAGEMENT - MÓDULO DE PRUEBA")
    print("="*60)
    print("\nEste módulo permite probar el engagement en Twitter")
    print("sin ejecutar todo el ciclo del bot.\n")
    
    # Verificar configuración
    if not Config.TWITTER_USERNAME or not Config.TWITTER_PASSWORD:
        print("❌ Error: Credenciales de Twitter no configuradas")
        print("   Configura TWITTER_USERNAME y TWITTER_PASSWORD en .env")
        return
    
    print("✅ Credenciales de Twitter configuradas")
    print(f"   Usuario: {Config.TWITTER_USERNAME}")
    
    # Menú de pruebas
    while True:
        print("\n" + "="*60)
        print("MENÚ DE PRUEBAS")
        print("="*60)
        print("1. 👍 Test Likes (10 tweets)")
        print("2. 💬 Test Comments (5 tweets)")
        print("3. 🔄 Full Engagement (10 likes + 5 comments)")
        print("4. 🤖 Test AI Comment Generation")
        print("5. 📊 View Engagement Stats")
        print("0. 👋 Salir")
        print("="*60)
        
        try:
            choice = input("\nSelecciona una opción: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n👋 Saliendo...")
            break
        
        if choice == "0":
            print("\n👋 ¡Hasta pronto!")
            break
        elif choice == "1":
            test_likes_only()
        elif choice == "2":
            test_comments_only()
        elif choice == "3":
            test_full_engagement()
        elif choice == "4":
            test_ai_comment_generation()
        elif choice == "5":
            view_engagement_stats()
        else:
            print("❌ Opción inválida")
        
        input("\n⏸️  Presiona ENTER para continuar...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Prueba interrumpida por el usuario")
        print("👋 ¡Hasta pronto!")
    except Exception as e:
        logger.error(f"❌ Error en módulo de prueba: {e}")
        import traceback
        traceback.print_exc()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de prueba para Twitter Service
Permite probar la publicación de tweets sin ejecutar todo el bot
"""

import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from services.twitter_service import TwitterService
from utils.logger import logger
from config.config import Config


def test_simple_tweet():
    """Prueba un tweet simple sin imagen"""
    print("\n" + "="*60)
    print("🧪 TEST 1: Tweet Simple (Sin Imagen)")
    print("="*60)
    
    text = """🚀 PRUEBA BOT CRYPTO

📊 Este es un tweet de prueba
✅ Sin imagen
⏰ Timestamp: Ahora mismo

#CryptoBot #Test"""
    
    twitter = TwitterService()
    
    # IMPORTANTE: Inicializar sesión de Twitter
    if not twitter.login_twitter(Config.TWITTER_USERNAME, Config.TWITTER_PASSWORD):
        print("❌ Error: No se pudo iniciar sesión en Twitter")
        return False
    
    success = twitter.post_tweet(text=text, category='crypto')
    
    if success:
        print("✅ Tweet simple publicado exitosamente")
    else:
        print("❌ Error publicando tweet simple")
    
    return success


def test_tweet_with_image():
    """Prueba un tweet con imagen"""
    print("\n" + "="*60)
    print("🧪 TEST 2: Tweet con Imagen")
    print("="*60)
    
    text = """💱 FOREX (Top Movimientos):

🟢 AUDJPY: +1.51%
🟢 CHFJPY: +1.06%
🟢 AUDUSD: +0.99%
🔴 EURAUD: -0.66%
🔴 USDMXN: -0.92%

#Forex #Trading"""
    
    # Buscar una imagen de prueba
    image_path = Config.FOREX_IMAGE_PATH or Config.REPORT_24H_IMAGE_PATH
    
    if not image_path or not os.path.exists(image_path):
        print(f"⚠️ No se encontró imagen en: {image_path}")
        print("⚠️ Publicando sin imagen...")
        image_path = None
    else:
        print(f"📎 Usando imagen: {image_path}")
    
    twitter = TwitterService()
    
    # IMPORTANTE: Inicializar sesión de Twitter
    if not twitter.login_twitter(Config.TWITTER_USERNAME, Config.TWITTER_PASSWORD):
        print("❌ Error: No se pudo iniciar sesión en Twitter")
        return False
    
    success = twitter.post_tweet(text=text, image_path=image_path, category='markets')
    
    if success:
        print("✅ Tweet con imagen publicado exitosamente")
    else:
        print("❌ Error publicando tweet con imagen")
    
    return success


def test_multiline_tweet():
    """Prueba un tweet con múltiples líneas y emojis"""
    print("\n" + "="*60)
    print("🧪 TEST 3: Tweet Multilínea con Emojis")
    print("="*60)
    
    text = """📈 REPORTE CRIPTO

😱 Sentimiento: Miedo Extremo
📊 Fear & Greed: 14/100

🟢 TOP SUBIDAS:
• CREAM: +65.35%
• PNT: +45.23%
• CHESS: +24.96%

🔴 TOP BAJADAS:
• BETA: -64.00%
• VIB: -63.26%

#Crypto #Bitcoin"""
    
    twitter = TwitterService()
    
    # IMPORTANTE: Inicializar sesión de Twitter
    if not twitter.login_twitter(Config.TWITTER_USERNAME, Config.TWITTER_PASSWORD):
        print("❌ Error: No se pudo iniciar sesión en Twitter")
        return False
    
    success = twitter.post_tweet(text=text, category='crypto')
    
    if success:
        print("✅ Tweet multilínea publicado exitosamente")
    else:
        print("❌ Error publicando tweet multilínea")
    
    return success


def test_long_tweet():
    """Prueba un tweet que excede el límite de caracteres"""
    print("\n" + "="*60)
    print("🧪 TEST 4: Tweet Largo (>280 caracteres)")
    print("="*60)
    
    text = """🚀 REPORTE COMPLETO DE MERCADOS

📊 Sentimiento: Miedo Extremo
📉 Fear & Greed Index: 14/100

🟢 TOP SUBIDAS 24H:
• CREAM: +65.35% ($2.1000)
• PNT: +45.23% ($0.0350)
• CHESS: +24.96% ($0.0265)
• G: +17.78% ($0.0046)
• KDA: +17.65% ($0.0060)

🔴 TOP BAJADAS 24H:
• BETA: -64.00% ($0.0004)
• VIB: -63.26% ($0.0022)
• WTC: -56.54% ($0.0103)

⏱️ MOVIMIENTOS 2H:
🟢 ETH: +1.26%
🟢 BTC: +0.68%

#Crypto #Trading #Bitcoin #Markets"""
    
    print(f"📏 Longitud del texto: {len(text)} caracteres")
    
    twitter = TwitterService()
    
    # IMPORTANTE: Inicializar sesión de Twitter
    if not twitter.login_twitter(Config.TWITTER_USERNAME, Config.TWITTER_PASSWORD):
        print("❌ Error: No se pudo iniciar sesión en Twitter")
        return False
    
    success = twitter.post_tweet(text=text, category='crypto')
    
    if success:
        print("✅ Tweet largo publicado exitosamente (truncado automáticamente)")
    else:
        print("❌ Error publicando tweet largo")
    
    return success


def main():
    """Función principal del módulo de prueba"""
    print("\n" + "="*60)
    print("🐦 MÓDULO DE PRUEBA - TWITTER SERVICE")
    print("="*60)
    print("\nEste módulo permite probar la publicación de tweets")
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
        print("1. 📝 Tweet simple (sin imagen)")
        print("2. 🖼️  Tweet con imagen")
        print("3. 📋 Tweet multilínea con emojis")
        print("4. 📏 Tweet largo (>280 caracteres)")
        print("5. 🔄 Ejecutar todas las pruebas")
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
            test_simple_tweet()
        elif choice == "2":
            test_tweet_with_image()
        elif choice == "3":
            test_multiline_tweet()
        elif choice == "4":
            test_long_tweet()
        elif choice == "5":
            print("\n🔄 Ejecutando todas las pruebas...\n")
            results = []
            results.append(("Tweet Simple", test_simple_tweet()))
            input("\n⏸️  Presiona ENTER para continuar con la siguiente prueba...")
            results.append(("Tweet con Imagen", test_tweet_with_image()))
            input("\n⏸️  Presiona ENTER para continuar con la siguiente prueba...")
            results.append(("Tweet Multilínea", test_multiline_tweet()))
            input("\n⏸️  Presiona ENTER para continuar con la siguiente prueba...")
            results.append(("Tweet Largo", test_long_tweet()))
            
            # Resumen
            print("\n" + "="*60)
            print("📊 RESUMEN DE PRUEBAS")
            print("="*60)
            for name, success in results:
                status = "✅" if success else "❌"
                print(f"{status} {name}")
            print("="*60)
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

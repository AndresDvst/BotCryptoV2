"""
Script para verificar que todo esté configurado correctamente.
Ejecuta esto antes de iniciar el bot para detectar problemas.
"""
import os
import sys

def check_python_version():
    """Verifica la versión de Python"""
    print("🐍 Verificando versión de Python...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor}.{version.micro} - Se requiere 3.8+")
        return False

def check_dependencies():
    """Verifica que las dependencias estén instaladas"""
    print("\n📦 Verificando dependencias...")
    
    required_packages = [
        'ccxt',
        'requests',
        'pandas',
        'numpy',
        'telegram',
        'selenium',
        'google.generativeai',
        'tweepy',
        'schedule',
        'dotenv',
        'colorlog'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package}")
            missing.append(package)
    
    if missing:
        print(f"\n   ⚠️ Faltan paquetes: {', '.join(missing)}")
        print("   💡 Ejecuta: pip install -r requirements.txt")
        return False
    
    return True

def check_env_file():
    """Verifica que el archivo .env exista"""
    print("\n📄 Verificando archivo .env...")
    
    if not os.path.exists('.env'):
        print("   ❌ Archivo .env no encontrado")
        print("   💡 Copia .env.example a .env y configura tus claves")
        return False
    
    print("   ✅ Archivo .env encontrado")
    return True

def check_env_variables():
    """Verifica las variables de entorno"""
    print("\n🔑 Verificando variables de entorno...")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = {
        'BINANCE_API_KEY': 'Binance API Key',
        'BINANCE_API_SECRET': 'Binance Secret',
        'BYBIT_API_KEY': 'Bybit API Key',
        'BYBIT_API_SECRET': 'Bybit Secret',
        'TELEGRAM_BOT_TOKEN': 'Telegram Bot Token',
        'TELEGRAM_CHAT_ID': 'Telegram Chat ID',
        'TWITTER_API_KEY': 'Twitter API Key',
        'TWITTER_API_SECRET': 'Twitter API Secret',
        'TWITTER_ACCESS_TOKEN': 'Twitter Access Token',
        'TWITTER_ACCESS_SECRET': 'Twitter Access Secret',
        'ANTHROPIC_API_KEY': 'Anthropic API Key',
    }
    
    missing = []
    for var, name in required_vars.items():
        value = os.getenv(var)
        if value and value != f'tu_{var.lower().split("_")[0]}_api_key_aqui' and value != 'tu_telegram_bot_token_aqui' and value != 'tu_telegram_chat_id_aqui':
            print(f"   ✅ {name}")
        else:
            print(f"   ❌ {name} - No configurada o usa valor de ejemplo")
            missing.append(name)
    
    if missing:
        print(f"\n   ⚠️ Variables faltantes o sin configurar:")
        for var in missing:
            print(f"      - {var}")
        return False
    
    return True

def check_directories():
    """Verifica que existan los directorios necesarios"""
    print("\n📁 Verificando directorios...")
    
    directories = ['logs', 'images', 'config', 'services', 'utils']
    
    for directory in directories:
        if os.path.exists(directory):
            print(f"   ✅ {directory}/")
        else:
            print(f"   ⚠️ {directory}/ - Creando...")
            os.makedirs(directory, exist_ok=True)
    
    return True

def check_images():
    """Verifica que existan las imágenes"""
    print("\n🖼️ Verificando imágenes...")
    
    images = [
        'images/morning_report.png',
        'images/crypto_report.png'
    ]
    
    missing = []
    for image in images:
        if os.path.exists(image):
            print(f"   ✅ {image}")
        else:
            print(f"   ⚠️ {image} - No encontrada")
            missing.append(image)
    
    if missing:
        print("\n   💡 Crea estas imágenes (1200x675 px) y colócalas en images/")
        print("      Puedes usar imágenes temporales por ahora.")
        return False
    
    return True

def test_api_connection():
    """Prueba la conexión con las APIs"""
    print("\n🔌 Probando conexión con APIs...")
    print("   (Esto puede tardar unos segundos...)\n")
    
    try:
        from config.config import Config
        from services.binance_service import BinanceService
        
        Config.validate()
        print("   ✅ Configuración validada")
        
        binance = BinanceService()
        print("   ✅ Conexión con Binance establecida")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    """Función principal"""
    print("=" * 60)
    print("🔍 VERIFICADOR DE CONFIGURACIÓN - CRYPTO BOT")
    print("=" * 60)
    
    checks = [
        ("Python", check_python_version),
        ("Dependencias", check_dependencies),
        ("Archivo .env", check_env_file),
        ("Variables de entorno", check_env_variables),
        ("Directorios", check_directories),
        ("Imágenes", check_images),
        ("Conexión APIs", test_api_connection),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n   ❌ Error inesperado: {e}")
            results.append((name, False))
    
    # Resumen final
    print("\n" + "=" * 60)
    print("📊 RESUMEN")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅" if passed else "❌"
        print(f"{status} {name}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 ¡Todo está configurado correctamente!")
        print("💡 Puedes ejecutar: python main.py")
    else:
        print("\n⚠️ Hay problemas que debes resolver antes de ejecutar el bot.")
        print("💡 Lee los mensajes arriba para ver qué falta configurar.")
    
    print("\n")

if __name__ == "__main__":
    main()
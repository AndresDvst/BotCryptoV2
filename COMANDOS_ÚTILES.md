# ⚡ Comandos Útiles - Referencia Rápida

## 📦 Instalación Inicial

```bash
# 1. Navegar a la carpeta del proyecto
cd crypto-bot

# 2. Instalar todas las dependencias
pip install -r requirements.txt

# 3. Verificar la instalación
python check_setup.py

# 4. Ejecutar el bot
python main.py
```

## 🔄 Actualización de Dependencias

```bash
# Actualizar todas las librerías a la última versión
pip install --upgrade -r requirements.txt

# Actualizar una librería específica
pip install --upgrade ccxt
pip install --upgrade anthropic
```

## 🐛 Solución de Problemas Comunes

### Problema: "pip no se reconoce como comando"

```bash
# Windows
python -m pip install -r requirements.txt

# Mac/Linux
python3 -m pip install -r requirements.txt
```

### Problema: Permisos en Mac/Linux

```bash
# Dar permisos de ejecución
chmod +x main.py

# Ejecutar con permisos
sudo python3 main.py
```

### Problema: "No module named 'dotenv'"

```bash
pip install python-dotenv
```

### Problema: ChromeDriver no funciona

```bash
# Actualizar webdriver-manager
pip install --upgrade webdriver-manager

# Limpiar caché de drivers
pip cache purge
```

## 📊 Ver los Logs

```bash
# Windows
type logs\bot_20250101.log

# Mac/Linux
cat logs/bot_20250101.log

# Ver últimas 50 líneas (Mac/Linux)
tail -n 50 logs/bot_20250101.log

# Ver logs en tiempo real
tail -f logs/bot_20250101.log
```

## 🗑️ Limpiar el Proyecto

```bash
# Eliminar archivos temporales de Python
# Windows
del /s *.pyc
rmdir /s __pycache__

# Mac/Linux
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +

# Limpiar logs antiguos (más de 7 días)
# Windows
forfiles /p logs /m *.log /d -7 /c "cmd /c del @file"

# Mac/Linux
find logs/ -name "*.log" -mtime +7 -delete
```

## 🧪 Probar Componentes Individuales

### Probar solo Binance

```python
# Crea un archivo test_binance.py
from services.binance_service import BinanceService
from config.config import Config

Config.validate()
binance = BinanceService()
coins = binance.filter_significant_changes()
print(f"Monedas encontradas: {len(coins)}")
for coin in coins[:5]:
    print(f"{coin['symbol']}: {coin['change_24h']:.2f}%")
```

```bash
python test_binance.py
```

### Probar solo Telegram

```python
# Crea un archivo test_telegram.py
from services.telegram_service import TelegramService
from config.config import Config

Config.validate()
telegram = TelegramService()
telegram.send_message("🧪 Prueba de bot - ¡Funciona!")
```

```bash
python test_telegram.py
```

### Probar solo la IA (Gemini)

```python
# Ejecuta el script de prueba incluido
python test_gemini.py
```

O crea un archivo `test_ai.py`:

```python
from services.ai_analyzer_service import AIAnalyzerService
from config.config import Config

Config.validate()
ai = AIAnalyzerService()

# Datos de prueba
coins = [{'symbol': 'BTC/USDT', 'change_24h': 5.2, 'price': 45000}]
sentiment = {'overall_sentiment': 'Neutral', 'sentiment_score': 50}

analysis = ai.analyze_and_recommend(coins, sentiment)
print(analysis['full_analysis'])
```

```bash
python test_ai.py
```

## 🔧 Variables de Entorno

### Ver variables cargadas

```python
# Crea un archivo check_env.py
from dotenv import load_dotenv
import os

load_dotenv()

vars_to_check = [
    'BINANCE_API_KEY',
    'TELEGRAM_BOT_TOKEN',
    'ANTHROPIC_API_KEY'
]

for var in vars_to_check:
    value = os.getenv(var)
    if value:
        # Mostrar solo los primeros 10 caracteres por seguridad
        masked = value[:10] + "..." if len(value) > 10 else value
        print(f"✅ {var}: {masked}")
    else:
        print(f"❌ {var}: No configurada")
```

```bash
python check_env.py
```

## 🚀 Comandos para Producción

### Ejecutar en segundo plano (Linux/Mac)

```bash
# Ejecutar en background
nohup python main.py > output.log 2>&1 &

# Ver el proceso
ps aux | grep main.py

# Detener el bot
kill <PID>
```

### Ejecutar como servicio en Linux

```bash
# Crear archivo de servicio
sudo nano /etc/systemd/system/cryptobot.service
```

Contenido del archivo:

```ini
[Unit]
Description=Crypto Trading Bot
After=network.target

[Service]
Type=simple
User=tu_usuario
WorkingDirectory=/ruta/a/crypto-bot
ExecStart=/usr/bin/python3 /ruta/a/crypto-bot/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Recargar systemd
sudo systemctl daemon-reload

# Iniciar el servicio
sudo systemctl start cryptobot

# Habilitar inicio automático
sudo systemctl enable cryptobot

# Ver estado
sudo systemctl status cryptobot

# Ver logs
sudo journalctl -u cryptobot -f
```

### Ejecutar con Docker (Avanzado)

```dockerfile
# Crear archivo Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

```bash
# Construir imagen
docker build -t crypto-bot .

# Ejecutar contenedor
docker run -d --name crypto-bot \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  crypto-bot

# Ver logs
docker logs -f crypto-bot

# Detener
docker stop crypto-bot
```

## 📈 Monitoreo

### Script para verificar que el bot está corriendo

```bash
# check_bot.sh (Linux/Mac)
#!/bin/bash

if ps aux | grep -q "[m]ain.py"; then
    echo "✅ Bot está corriendo"
else
    echo "❌ Bot NO está corriendo"
    echo "🔄 Reiniciando bot..."
    cd /ruta/a/crypto-bot
    nohup python3 main.py > output.log 2>&1 &
fi
```

### Programar verificación cada 5 minutos (crontab)

```bash
# Editar crontab
crontab -e

# Agregar línea:
*/5 * * * * /ruta/a/check_bot.sh
```

## 🎨 Personalización Rápida

### Cambiar el intervalo de ejecución

En `config/config.py`:

```python
REPORT_INTERVAL_HOURS = 2  # Cambiar a 1, 3, 4, etc.
```

### Cambiar el porcentaje de filtro

En `.env`:

```
MIN_CHANGE_PERCENT=10  # Cambiar a 5, 15, 20, etc.
```

### Cambiar hora del reporte matutino

En `config/config.py`:

```python
MORNING_POST_TIME = "06:00"  # Cambiar a "07:00", "08:30", etc.
```

## 🔍 Debug Mode

### Activar modo debug

En `utils/logger.py`, cambiar:

```python
logger.setLevel(logging.DEBUG)  # Ya está así por defecto
```

Para producción:

```python
logger.setLevel(logging.INFO)  # Menos verboso
```

## 🌐 Proxy (Opcional)

Si necesitas usar proxy para las APIs:

```python
# En cada servicio, agregar:
proxies = {
    'http': 'http://proxy:puerto',
    'https': 'http://proxy:puerto'
}

# Ejemplo en requests
requests.get(url, proxies=proxies)

# Ejemplo en Selenium
chrome_options.add_argument('--proxy-server=http://proxy:puerto')
```

## 📱 Notificaciones de Error

Agregar notificación a Telegram cuando hay errores:

```python
# En utils/logger.py, agregar:
def send_error_notification(error_message):
    try:
        from services.telegram_service import TelegramService
        telegram = TelegramService()
        telegram.send_message(f"🚨 ERROR EN BOT:\n\n{error_message}")
    except:
        pass

# Usar en try/except:
try:
    # código
except Exception as e:
    logger.error(f"Error: {e}")
    send_error_notification(str(e))
```

## 🎯 Atajos útiles

```bash
# Alias para comandos frecuentes (agregar a .bashrc o .zshrc)
alias bot-start="cd ~/crypto-bot && python main.py"
alias bot-check="python ~/crypto-bot/check_setup.py"
alias bot-logs="tail -f ~/crypto-bot/logs/*.log"
alias bot-test="python ~/crypto-bot/test_binance.py"
```

---

## 📚 Recursos Adicionales

- **Documentación Binance API**: https://binance-docs.github.io/apidocs/
- **Documentación Bybit API**: https://bybit-exchange.github.io/docs/
- **Documentación Anthropic**: https://docs.anthropic.com/
- **Documentación Telegram Bot**: https://core.telegram.org/bots/api
- **Documentación Selenium**: https://selenium-python.readthedocs.io/

---

**💡 Tip**: Guarda este archivo como referencia. ¡Te ahorrará mucho tiempo!
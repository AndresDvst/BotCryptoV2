# 🤖 Crypto Trading Bot - Análisis Automatizado

<div align="center">
<a href="https://wa.me/+573001234567?text=Hola%20desde%20BotCryptoV2%20🚀" target="_blank" rel="noopener noreferrer"><img src="https://img.shields.io/badge/WhatsApp-25D366?style=for-the-badge&logo=whatsapp&logoColor=white" /></a>
<a href="https://twitter.com/AndresDvst25" target="_blank" rel="noopener noreferrer"><img src="https://img.shields.io/badge/X/Twitter-000000?style=for-the-badge&logo=x&logoColor=white" /></a>
<a href="https://www.facebook.com/andres.campos.732122" target="_blank" rel="noopener noreferrer"><img src="https://img.shields.io/badge/Facebook-1877F2?style=for-the-badge&logo=facebook&logoColor=white" /></a>
<a href="https://www.instagram.com/andres.devback/" target="_blank" rel="noopener noreferrer"><img src="https://img.shields.io/badge/Instagram-E4405F?style=for-the-badge&logo=instagram&logoColor=white" /></a>
<a href="https://www.linkedin.com/in/andresdevback22/" target="_blank" rel="noopener noreferrer"><img src="https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white" /></a>
<a href="https://github.com/AndresDvst" target="_blank" rel="noopener noreferrer"><img src="https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white" /></a>
<a href="https://discord.com/users/1133809866130067476" target="_blank" rel="noopener noreferrer"><img src="https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white" /></a>
</div>

Bot inteligente que analiza el mercado de criptomonedas cada 2 horas, genera reportes con IA y los publica automáticamente en Telegram y Twitter.

## 📋 Características

✅ Consulta **Binance** para obtener todas las criptomonedas  
✅ Filtra monedas con cambios **≥10% en 24h**  
✅ Consulta **Binance** para cambios en las últimas **2 horas**  
✅ Analiza el sentimiento del mercado (**CoinGecko**, **Fear & Greed Index**)  
✅ Genera análisis y recomendaciones con **IA (Google Gemini 2.5 Flash)**  
✅ Envía reportes a **Telegram**  
✅ Publica automáticamente en **Twitter/X** 5 publicaciones
✅ Ejecución cada **2 horas** + reporte matutino a las **6 AM**  
✅ Logs con colores para fácil seguimiento

## 📁 Estructura del Proyecto

```
crypto-bot/
│
├── main.py                          # Script principal
├── bot_orchestrator.py              # Orquestador de servicios
├── requirements.txt                 # Dependencias
├── .env                            # Variables de entorno (CREAR)
├── .env.example                    # Plantilla de configuración
│
├── config/
│   └── config.py                   # Configuración centralizada
│
├── services/
│   ├── binance_service.py          # Servicio de Binance
│   ├── market_sentiment_service.py # Análisis de sentimiento
│   ├── ai_analyzer_service.py      # Análisis con IA
│   ├── telegram_service.py         # Envío a Telegram
│   └── twitter_service.py          # Publicación en Twitter
│
├── utils/
│   └── logger.py                   # Sistema de logs
│
├── images/
│   ├── morning_report.png          # Imagen para reporte 6 AM
│   └── crypto_report.png           # Imagen para reportes cada 2h
│
└── logs/
    └── bot_YYYYMMDD.log           # Logs diarios (se crean automáticamente)
```

## 🚀 GUÍA DE INSTALACIÓN PASO A PASO

### PASO 1: Instalar Python

1. Ve a https://www.python.org/downloads/
2. Descarga Python 3.11 o superior
3. **IMPORTANTE**: Durante la instalación marca ☑ "Add Python to PATH"
4. Completa la instalación

### PASO 2: Verificar Instalación

Abre la terminal (CMD en Windows, Terminal en Mac/Linux) y escribe:

```bash
python --version
```

Debe aparecer algo como: `Python 3.11.x`

### PASO 3: Descargar el Proyecto

1. Descarga todos los archivos del proyecto
2. Colócalos en una carpeta, por ejemplo: `C:\crypto-bot\` o `~/crypto-bot/`

### PASO 4: Instalar Dependencias

En la terminal, navega a la carpeta del proyecto:

```bash
cd C:\crypto-bot
```

O en Mac/Linux:

```bash
cd ~/crypto-bot
```

Ahora instala las librerías necesarias:

```bash
pip install -r requirements.txt
```

Esto tomará unos minutos. ¡Ten paciencia! ☕

### PASO 5: Obtener las Claves API

#### 5.1 Binance API

1. Ve a https://www.binance.com/
2. Crea una cuenta si no tienes una
3. Ve a tu perfil → "API Management"
4. Crea una nueva API Key
5. **IMPORTANTE**: Solo marca permisos de **lectura** (Read)
6. Guarda tu **API Key** y **Secret Key**

#### 5.3 Bot de Telegram

1. Abre Telegram en tu teléfono o computadora
2. Busca el usuario: `@BotFather`
3. Envía el comando: `/newbot`
4. Sigue las instrucciones:
   - Nombre del bot (ej: "Mi Crypto Bot")
   - Username del bot (debe terminar en 'bot', ej: "micryptobot")
5. **BotFather** te dará un **TOKEN**. ¡Guárdalo!
6. Ahora busca el usuario: `@userinfobot`
7. Envía el comando: `/start`
8. Te dará tu **CHAT_ID**. ¡Guárdalo!

#### 5.5 Google Gemini API

1. Ve a https://makersuite.google.com/app/apikey o https://aistudio.google.com/
2. Haz clic en "Create API Key" o "Obtener clave de API"
3. Selecciona o crea un proyecto de Google Cloud
4. Se generará tu API Key automáticamente
5. Guarda tu **API Key**

**💡 Ventaja de Gemini**: 
- ✅ **Completamente GRATIS** (60 solicitudes por minuto)
- ✅ Más generoso que otras APIs
- ✅ No requiere tarjeta de crédito
- ✅ Perfecto para comenzar

### PASO 6: Configurar el Archivo .env

1. Haz una copia del archivo `.env.example` y renómbrala a `.env`
2. Abre el archivo `.env` con un editor de texto (Notepad, VS Code, etc.)
3. Reemplaza todos los valores con tus claves reales:

```env
# BINANCE API
BINANCE_API_KEY=tu_clave_aqui
BINANCE_API_SECRET=tu_secret_aqui

# TELEGRAM BOT
TELEGRAM_BOT_TOKEN=tu_token_aqui
TELEGRAM_CHAT_ID=tu_chat_id_aqui

# GOOGLE GEMINI API
GOOGLE_GEMINI_API_KEY=tu_clave_aqui

# CONFIGURACIÓN
MIN_CHANGE_PERCENT=10
MORNING_IMAGE_PATH=./images/morning_report.png
REPORT_IMAGE_PATH=./images/crypto_report.png
```

4. Guarda el archivo

### PASO 7: Crear las Imágenes

1. Crea dos imágenes PNG (puedes usar cualquier editor):
   - `morning_report.png` (para el reporte de las 6 AM)
   - `crypto_report.png` (para los reportes cada 2 horas)
2. Colócalas en la carpeta `images/`

**Recomendaciones para las imágenes:**
- Tamaño: 1200x675 píxeles (formato Twitter)
- Tema: Relacionado con criptomonedas
- Peso: Menor a 5 MB

### PASO 8: Ejecutar el Bot

En la terminal, ejecuta:

```bash
python main.py
```

El bot te preguntará:

```
1. Ejecutar análisis ahora (una vez)
2. Programar ejecuciones automáticas (cada 2h + 6 AM)
3. Ambas (ejecutar ahora + programar)
```

**Opción recomendada para empezar: 1** (ejecutar una vez para probar)

Si todo funciona bien, luego usa la **opción 3** para dejarlo corriendo automáticamente.

## � Dependencias y Requisitos

- Python 3.11 o superior
- Variables de entorno en `.env`:
  - BINANCE_API_KEY, BINANCE_API_SECRET
  - TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
  - GOOGLE_GEMINI_API_KEY
- Imágenes requeridas en `images/`: `morning_report.png` y `crypto_report.png` (1200×675)

Dependencias principales:
- ccxt, requests, schedule, selenium, webdriver-manager, python-dotenv, colorlog, google-generativeai, pandas, numpy, tqdm

Faltantes detectados del código:
- pyperclip (se usa en Twitter para pegar texto). Instalar: `pip install pyperclip`

Arquitectura y archivos clave:
- Orquestador: [bot_orchestrator.py](file:///i:/Proyectos/BotCryptoV2/bot_orchestrator.py)
- Entrada: [main.py](file:///i:/Proyectos/BotCryptoV2/main.py)
- Configuración: [config.py](file:///i:/Proyectos/BotCryptoV2/config/config.py)
- Servicios: [binance_service.py](file:///i:/Proyectos/BotCryptoV2/services/binance_service.py), [bybit_service.py](file:///i:/Proyectos/BotCryptoV2/services/bybit_service.py), [market_sentiment_service.py](file:///i:/Proyectos/BotCryptoV2/services/market_sentiment_service.py), [ai_analyzer_service.py](file:///i:/Proyectos/BotCryptoV2/services/ai_analyzer_service.py), [telegram_service.py](file:///i:/Proyectos/BotCryptoV2/services/telegram_service.py), [twitter_service.py](file:///i:/Proyectos/BotCryptoV2/services/twitter_service.py)

## �📱 Cómo Funciona

### Flujo Completo

```
1. 🔍 CONSULTA BINANCE
   └─> Obtiene todas las criptomonedas
   └─> Filtra las que cambiaron ≥10% en 24h

2. 📊 CONSULTA BINANCE
   └─> Para cada moneda filtrada
   └─> Obtiene el cambio en las últimas 2 horas

3. 🌐 ANALIZA SENTIMIENTO
   └─> Fear & Greed Index
   └─> Datos globales del mercado
   └─> Monedas en tendencia

4. 🤖 ANÁLISIS CON IA
   └─> Gemini analiza todos los datos
   └─> Genera recomendaciones
   └─> Evalúa riesgos

5. 📱 ENVÍA A TELEGRAM
   └─> Reporte formateado con emojis
   └─> Top 3 monedas
   └─> Recomendación de IA

6. 🐦 PUBLICA EN TWITTER
   └─> Resumen de 700 caracteres
   └─> Con imagen adjunta
   └─> Automáticamente
```

### Horarios de Ejecución

- **6:00 AM**: Reporte matutino completo con `morning_report.png`
- **Cada 2 horas**: Reporte regular con `crypto_report.png`

## 🛠️ Solución de Problemas

### Problema: "ModuleNotFoundError"

**Solución**: Instala de nuevo las dependencias:

```bash
pip install -r requirements.txt
```

### Problema: "API Key inválida"

**Solución**: Verifica que hayas copiado correctamente las claves en el archivo `.env`

### Problema: El bot no envía mensajes a Telegram

**Solución**: 
1. Verifica que el TOKEN y CHAT_ID sean correctos
2. Inicia una conversación con tu bot en Telegram (envíale un mensaje)

### Problema: Twitter no funciona

**Solución**:
1. Verifica que tu cuenta de Twitter tenga permisos de desarrollador
2. Asegúrate de que la app tenga permisos de "Read and Write"
3. Chrome Driver debe estar actualizado (se descarga automáticamente)

### Problema: "Rate Limit Exceeded"

**Solución**: Las APIs tienen límites de uso. Espera unos minutos antes de volver a ejecutar.

## 📊 Ejemplo de Reporte

```
🚀 REPORTE CRIPTO - Análisis de Mercado

😊 Sentimiento del Mercado: Codicia
📊 Fear & Greed Index: 68/100 (Codicia)

💎 Top 3 Criptomonedas con Mayor Movimiento:

1. SOL/USDT 📈
   💰 Precio: $98.45
   📊 Cambio 24h: +15.32%
   ⏱ Cambio 2h: +3.21%

2. MATIC/USDT 📈
   💰 Precio: $0.85
   📊 Cambio 24h: +12.87%
   ⏱ Cambio 2h: +1.95%

3. AVAX/USDT 📉
   💰 Precio: $34.21
   📊 Cambio 24h: -11.24%
   ⏱ Cambio 2h: -2.45%

🤖 Recomendación de IA:
Basado en el análisis, SOL muestra el mayor potencial...
[continúa]

📊 Confianza: 🟢🟢🟢🟢🟢🟢🟢🟢⚪⚪ (8/10)
```

## 🔐 Seguridad

⚠️ **IMPORTANTE**:
- **NUNCA** compartas tu archivo `.env`
- **NUNCA** subas tus claves API a GitHub o redes sociales
- Usa solo claves API con permisos de **lectura** (las APIs de trading no necesitan permisos de escritura)
- Mantén tu computadora segura con antivirus actualizado

## 🚀 Próximas Funcionalidades (Tú las puedes agregar)

- [ ] Base de datos para histórico de análisis
- [ ] Dashboard web con gráficos interactivos
- [ ] Backtesting de estrategias
- [ ] Alertas personalizadas por WhatsApp
- [ ] Trading automático (AVANZADO)
- [ ] Análisis técnico con indicadores
- [ ] Integración con más exchanges

## 📞 Soporte

Si tienes problemas:

1. Revisa los logs en la carpeta `logs/`
2. Lee los mensajes de error con atención
3. Busca el error en Google (la mayoría tienen solución)
4. Revisa que todas las APIs estén configuradas correctamente

## 🗑️ Archivos Obsoletos / Limpieza del Repositorio

- venv/ (entorno virtual local, no debe versionarse)
- utils/chrome-win64/ (binarios de Chrome y chromedriver, pesados y no necesarios si usas webdriver-manager o CHROMEDRIVER_PATH)
- logs/ y archivos `bot_YYYYMMDD.log` (generados en runtime)
- images/ (mantener solo las dos imágenes requeridas)
- tweet_log.json (artefacto de ejecución, no crítico para versionar)
- caches y `__pycache__/` (eliminar y agregar a `.gitignore`)

## 📄 Licencia

Proyecto de código abierto para fines educativos.

---

**⚠️ DISCLAIMER**: Este bot es solo para análisis e información. NO constituye asesoría financiera. Investiga antes de invertir. Las criptomonedas son volátiles y puedes perder tu dinero.

<div align="center">
<a href="https://wa.me/+573001234567?text=Hola%20desde%20BotCryptoV2%20🚀" target="_blank" rel="noopener noreferrer"><img src="https://img.shields.io/badge/WhatsApp-25D366?style=for-the-badge&logo=whatsapp&logoColor=white" /></a>
<a href="https://twitter.com/AndresDvst25" target="_blank" rel="noopener noreferrer"><img src="https://img.shields.io/badge/X/Twitter-000000?style=for-the-badge&logo=x&logoColor=white" /></a>
<a href="https://www.facebook.com/andres.campos.732122" target="_blank" rel="noopener noreferrer"><img src="https://img.shields.io/badge/Facebook-1877F2?style=for-the-badge&logo=facebook&logoColor=white" /></a>
<a href="https://www.instagram.com/andres.devback/" target="_blank" rel="noopener noreferrer"><img src="https://img.shields.io/badge/Instagram-E4405F?style=for-the-badge&logo=instagram&logoColor=white" /></a>
<a href="https://www.linkedin.com/in/andresdevback22/" target="_blank" rel="noopener noreferrer"><img src="https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white" /></a>
<a href="https://github.com/AndresDvst" target="_blank" rel="noopener noreferrer"><img src="https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white" /></a>
<a href="https://discord.com/users/1133809866130067476" target="_blank" rel="noopener noreferrer"><img src="https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white" /></a>
</div>



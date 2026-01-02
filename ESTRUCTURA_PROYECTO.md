# 📂 Estructura Completa del Proyecto

## 🗂️ Vista General

```
crypto-bot/
│
├── 📄 main.py                          # Punto de entrada - Ejecuta el bot
├── 🤖 bot_orchestrator.py              # Coordinador principal
├── 📦 requirements.txt                 # Librerías necesarias
├── 🔐 .env                            # Configuración privada (CREAR)
├── 📋 .env.example                    # Plantilla de configuración
├── 🧪 check_setup.py                  # Verificador de instalación
│
├── 📖 README.md                        # Documentación principal
├── 🐦 TWITTER_SETUP.md                # Guía de Twitter
├── ⚡ COMANDOS_ÚTILES.md              # Referencia rápida
├── 📊 ESTRUCTURA_PROYECTO.md          # Este archivo
│
├── 📁 config/
│   └── ⚙️ config.py                   # Configuración centralizada
│
├── 📁 services/
│   ├── 💰 binance_service.py          # Consulta a Binance
│   ├── 📊 bybit_service.py            # Consulta a Bybit
│   ├── 🌐 market_sentiment_service.py # Análisis de sentimiento
│   ├── 🤖 ai_analyzer_service.py      # Análisis con IA (Gemini)
│   ├── 📱 telegram_service.py         # Envío a Telegram
│   └── 🐦 twitter_service.py          # Publicación en Twitter
│
├── 📁 utils/
│   └── 📝 logger.py                   # Sistema de logs con colores
│
├── 📁 images/
│   ├── 🌅 morning_report.png          # Imagen reporte 6 AM
│   └── 📈 crypto_report.png           # Imagen reportes 2h
│
└── 📁 logs/
    └── 📄 bot_YYYYMMDD.log            # Logs diarios (auto-generados)
```

## 🔄 Flujo de Ejecución

```
┌─────────────────────────────────────────────────────────────┐
│                        INICIO                                │
│                      main.py                                 │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              bot_orchestrator.py                             │
│           (Coordina todos los servicios)                     │
└───┬───────────┬──────────┬──────────┬──────────┬────────────┘
    │           │          │          │          │
    ▼           ▼          ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│Binance │ │ Bybit  │ │Sentim. │ │   IA   │ │Telegram│
│Service │ │Service │ │Service │ │Service │ │Service │
└───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘
    │          │          │          │          │
    │ Filtra   │ Cambios  │ Fear &   │ Análisis │ Envía
    │ monedas  │ 2 horas  │ Greed    │ con IA   │ reporte
    │ ≥10%     │          │          │          │
    │          │          │          │          │
    └──────────┴──────────┴──────────┴──────────┘
                          │
                          ▼
                  ┌──────────────┐
                  │   Twitter    │
                  │   Service    │
                  └──────────────┘
                          │
                          ▼
                    📱 PUBLICADO
```

## 📊 Diagrama de Datos

```
┌───────────────────────────────────────────────────────────┐
│                    FLUJO DE DATOS                          │
└───────────────────────────────────────────────────────────┘

1️⃣ BINANCE
   ├─ Input: Ninguno
   ├─ Proceso: Consulta todas las monedas
   ├─ Filtro: Cambio ≥10% en 24h
   └─ Output: Lista de monedas significativas
      │
      ▼
2️⃣ BYBIT
   ├─ Input: Lista de monedas de Binance
   ├─ Proceso: Consulta histórico de 2 horas
   ├─ Cálculo: Cambio porcentual
   └─ Output: Monedas enriquecidas con datos 2h
      │
      ▼
3️⃣ MARKET SENTIMENT
   ├─ Input: Ninguno
   ├─ Consultas:
   │  ├─ Fear & Greed Index
   │  ├─ Datos globales (CoinGecko)
   │  └─ Monedas en tendencia
   └─ Output: Sentimiento del mercado
      │
      ▼
4️⃣ AI ANALYZER
   ├─ Input:
   │  ├─ Monedas enriquecidas
   │  └─ Sentimiento del mercado
   ├─ Proceso: Análisis con Claude
   └─ Output: Reporte + Recomendación
      │
      ├─────────────────────┬──────────────────┐
      ▼                     ▼                  ▼
5️⃣ TELEGRAM          6️⃣ TWITTER         7️⃣ LOGS
   └─ Reporte         └─ Resumen         └─ Historial
      formateado         + Imagen            completo
```

## 🔑 Configuración (config/config.py)

```python
Config
├── BINANCE_API_KEY         # Clave Binance
├── BINANCE_API_SECRET      # Secret Binance
├── BYBIT_API_KEY           # Clave Bybit
├── BYBIT_API_SECRET        # Secret Bybit
├── TELEGRAM_BOT_TOKEN      # Token del bot
├── TELEGRAM_CHAT_ID        # ID del chat
├── TWITTER_API_KEY         # Clave Twitter
├── TWITTER_API_SECRET      # Secret Twitter
├── TWITTER_ACCESS_TOKEN    # Token de acceso
├── TWITTER_ACCESS_SECRET   # Secret de acceso
├── ANTHROPIC_API_KEY       # Clave Claude
├── MIN_CHANGE_PERCENT      # Filtro (default: 10%)
├── MORNING_IMAGE_PATH      # Imagen 6 AM
├── REPORT_IMAGE_PATH       # Imagen 2h
├── MORNING_POST_TIME       # Hora matutino (06:00)
└── REPORT_INTERVAL_HOURS   # Intervalo (2)
```

## 🧩 Servicios Detallados

### 💰 Binance Service

```
Clase: BinanceService
├── __init__()
│   └─ Inicializa conexión con ccxt.binance
│
├── get_all_tickers()
│   ├─ Consulta todos los pares de trading
│   └─ Retorna diccionario con precios
│
├── filter_significant_changes(min_change_percent)
│   ├─ Filtra pares /USDT
│   ├─ Aplica filtro de % de cambio
│   ├─ Ordena por cambio (mayor a menor)
│   └─ Retorna lista de monedas significativas
│
└── get_coin_info(symbol)
    └─ Información detallada de una moneda
```

### 📊 Bybit Service

```
Clase: BybitService
├── __init__()
│   └─ Inicializa conexión con ccxt.bybit
│
├── get_2hour_change(coins)
│   ├─ Para cada moneda:
│   │   ├─ Obtiene velas de 1m (120 velas = 2h)
│   │   ├─ Compara precio inicial vs final
│   │   └─ Calcula % de cambio
│   └─ Retorna monedas con cambio_2h agregado
│
└── get_current_price(symbol)
    └─ Precio actual de una moneda
```

### 🌐 Market Sentiment Service

```
Clase: MarketSentimentService
├── __init__()
│   └─ Define URLs de APIs
│
├── get_fear_greed_index()
│   ├─ Consulta API alternative.me
│   ├─ Valor 0-100 (0=miedo extremo, 100=codicia extrema)
│   └─ Retorna {value, classification, timestamp}
│
├── get_global_market_data()
│   ├─ Consulta CoinGecko /global
│   └─ Retorna:
│       ├─ Market cap total
│       ├─ Volumen 24h
│       ├─ Dominancia BTC/ETH
│       └─ # de criptos activas
│
├── get_trending_coins()
│   ├─ Consulta CoinGecko /trending
│   └─ Top 10 monedas en tendencia
│
└── analyze_market_sentiment()
    ├─ Ejecuta todos los métodos anteriores
    ├─ Calcula sentimiento promedio
    └─ Retorna análisis completo con emoji
```

### 🤖 AI Analyzer Service

```
Clase: AIAnalyzerService
├── __init__()
│   ├─ Configura API Key de Gemini
│   ├─ Define parámetros de generación
│   ├─ Configura filtros de seguridad
│   └─ Inicializa modelo gemini-1.5-flash
│
├── analyze_and_recommend(coins, market_sentiment)
│   ├─ Prepara contexto con datos
│   ├─ Genera prompt estructurado
│   ├─ Llama a Gemini API
│   ├─ Parsea respuesta en secciones
│   └─ Retorna análisis estructurado:
│       ├─ full_analysis
│       ├─ market_overview
│       ├─ top_coins_analysis
│       ├─ recommendation
│       ├─ confidence_level (1-10)
│       └─ warnings
│
└── generate_short_summary(analysis, max_chars=700)
    ├─ Genera versión corta para redes
    ├─ Incluye emojis
    ├─ Limita a 700 caracteres
    └─ Optimizado para Twitter/Telegram
```

### 📱 Telegram Service

```
Clase: TelegramService
├── __init__()
│   └─ Configura bot_token y chat_id
│
├── send_message(message, parse_mode="HTML")
│   ├─ Valida longitud (máx 4096)
│   ├─ POST a API de Telegram
│   └─ Retorna True/False
│
├── send_report(analysis, market_sentiment, coins)
│   ├─ Formatea reporte con HTML
│   ├─ Incluye:
│   │   ├─ Sentimiento del mercado
│   │   ├─ Top 3 monedas
│   │   ├─ Recomendación IA
│   │   └─ Nivel de confianza
│   └─ Envía mensaje
│
└── _format_report(...)
    └─ Helper para formatear HTML
```

### 🐦 Twitter Service

```
Clase: TwitterService
├── __init__()
│   └─ Inicializa driver como None
│
├── _init_driver()
│   ├─ Configura opciones de Chrome
│   ├─ Descarga ChromeDriver automáticamente
│   └─ Inicializa Selenium WebDriver
│
├── _human_type(element, text)
│   └─ Simula escritura humana con delays
│
├── _human_delay(min, max)
│   └─ Pausa aleatoria
│
├── login_twitter(username, password)
│   ├─ Navega a twitter.com/login
│   ├─ Llena formulario de login
│   ├─ Simula comportamiento humano
│   └─ Retorna True si éxito
│
├── post_tweet(text, image_path)
│   ├─ Navega a twitter.com/home
│   ├─ Encuentra caja de texto
│   ├─ Escribe tweet
│   ├─ Adjunta imagen (opcional)
│   ├─ Hace clic en "Post"
│   └─ Retorna True si éxito
│
└── close()
    └─ Cierra el navegador
```

## 🎨 Utils (logger.py)

```
setup_logger(name)
├─ Crea logger con colores
├─ Niveles:
│  ├─ DEBUG   → Cyan
│  ├─ INFO    → Green
│  ├─ WARNING → Yellow
│  └─ ERROR   → Red
│
├─ Handlers:
│  ├─ Console (con colores)
│  └─ Archivo (sin colores)
│
└─ Formato: 
   "YYYY-MM-DD HH:MM:SS - LEVEL - mensaje"
```

## 📅 Programación (main.py)

```python
Scheduler (schedule library)
│
├── Reporte Matutino
│   ├── Horario: 06:00 AM
│   ├── Función: run_morning_analysis()
│   ├── Imagen: morning_report.png
│   └── Ejecuta: bot.run_analysis_cycle(is_morning=True)
│
└── Reportes Cada 2 Horas
    ├── Horario: Cada 2 horas
    ├── Función: run_regular_analysis()
    ├── Imagen: crypto_report.png
    └── Ejecuta: bot.run_analysis_cycle(is_morning=False)

Loop Principal:
while True:
    schedule.run_pending()
    time.sleep(60)  # Revisar cada minuto
```

## 🔐 Seguridad

```
Archivos a NUNCA compartir:
├── .env                      # Claves API
├── logs/*.log                # Pueden contener info sensible
└── __pycache__/             # Archivos compilados

Archivos seguros para GitHub:
├── *.py                      # Todo el código
├── requirements.txt          # Dependencias
├── .env.example             # Plantilla sin claves
├── *.md                      # Documentación
└── images/*.png             # Imágenes públicas

Crear .gitignore:
.env
logs/
__pycache__/
*.pyc
*.log
```

## 📈 Métricas del Proyecto

```
Total de Archivos: 17
Líneas de Código: ~1,500
Servicios: 6
APIs Integradas: 6
  ├─ Binance
  ├─ Bybit
  ├─ CoinGecko
  ├─ Fear & Greed Index
  ├─ Google Gemini
  └─ Telegram

Tecnologías:
├─ Python 3.11+
├─ ccxt (exchanges)
├─ Selenium (automatización)
├─ Anthropic (IA)
├─ Schedule (tareas)
└─ Telegram Bot API
```

## 🎯 Próximos Pasos

```
Fase 1: Instalación ✅
├─ Instalar Python
├─ Obtener APIs
├─ Configurar .env
└─ Ejecutar check_setup.py

Fase 2: Primera Ejecución ✅
├─ python main.py (opción 1)
├─ Verificar logs
└─ Revisar Telegram

Fase 3: Automatización ⏳
├─ python main.py (opción 3)
├─ Dejar corriendo 24/7
└─ Monitorear logs

Fase 4: Mejoras 🚀
├─ Base de datos
├─ Dashboard web
├─ Más indicadores
└─ ¡Tu imaginación!
```

---

## 💡 Tips para el README de GitHub

Cuando subas esto a GitHub, incluye:

```markdown
## 🎥 Demo
[Video o GIFs mostrando el bot en acción]

## 📊 Tecnologías
![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)
![Selenium](https://img.shields.io/badge/Selenium-43B02A?logo=selenium&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-2CA5E0?logo=telegram&logoColor=white)

## ⭐ Features
- Análisis en tiempo real
- IA integrada
- Automatización completa
- Código modular y limpio
```

---

**¿Listo para impresionar a los reclutadores?** 🚀
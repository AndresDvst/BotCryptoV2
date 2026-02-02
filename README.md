# 🤖 Crypto Trading Bot V3 - Análisis Multi-Mercado con IA

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Gemini](https://img.shields.io/badge/AI-Gemini_2.5-orange.svg)
![Version](https://img.shields.io/badge/Version-3.0-green.svg)

**Bot inteligente de trading que analiza criptomonedas, mercados tradicionales, genera señales técnicas con IA, y publica automáticamente en Telegram y Twitter**

[🚀 Instalación](#-instalación-rápida) • [⚙️ Configuración](#️-configuración) • [🐳 Docker](#-despliegue-con-docker) • [💻 Uso](#-uso)

</div>

---

## 📋 Tabla de Contenidos

- [✨ Características](#-características)
- [🚀 Instalación Rápida](#-instalación-rápida)
- [⚙️ Configuración](#️-configuración)
- [💻 Uso](#-uso)
- [🐳 Despliegue con Docker](#-despliegue-con-docker)
- [🏗️ Arquitectura](#️-arquitectura)
- [🛠️ Solución de Problemas](#️-solución-de-problemas)

---

## ✨ Características

### 📈 Análisis de Mercados

| Mercado | Fuente | Características |
|---------|--------|-----------------|
| **Criptomonedas** | Binance | Top movers, cambios 2h/24h, volumen |
| **Acciones** | Twelve Data | S&P 500, tech stocks, ETFs |
| **Forex** | Twelve Data | EUR/USD, GBP/USD, etc. |
| **Commodities** | Twelve Data | Oro, Plata, Petróleo |

### 🧠 Análisis con IA (Google Gemini)

- Generación automática de análisis y recomendaciones
- Evaluación de riesgos y oportunidades
- Filtrado de noticias por relevancia (scoring 1-10)
- Resúmenes inteligentes para Twitter

### 🎯 Análisis Técnico Avanzado

- **Indicadores**: RSI, MACD, Bollinger Bands, ATR, EMAs, SMAs, Stochastic
- **Señales**: LONG/SHORT/NEUTRAL con confianza 0-100%
- **Position Sizing** automático basado en riesgo
- **Stop Loss/Take Profit** dinámicos (ATR-based)
- Generación de gráficos visuales

### 📱 Publicación Automática

| Plataforma | Bot | Canal |
|------------|-----|-------|
| Telegram | @CryptoBot | Reportes cada 2h + 6AM |
| Telegram | @MarketsBot | Mercados tradicionales |
| Telegram | @SignalsBot | Señales de trading |
| Twitter/X | Selenium | Publicación con imágenes |

### 🔄 Modos de Operación

| Modo | Descripción |
|------|-------------|
| **Análisis Completo** | Crypto + Mercados + Señales + Noticias |
| **Modo Espera Inteligente** | Monitoreo continuo + alertas automáticas |
| **Scheduler** | Ejecuciones programadas cada 2h |
| **Monitoreo Tiempo Real** | Detección de pumps/dumps cada 5 min |

---

## 🚀 Instalación Rápida

### Requisitos

- Python 3.11+
- Google Chrome (para Twitter)
- MySQL (opcional, para persistencia)

### Windows

```powershell
# Clonar repositorio
git clone https://github.com/AndresDvst/BotCryptoV2.git
cd BotCryptoV2

# Crear entorno virtual
python -m venv venv
.\venv\Scripts\Activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
copy .env.example .env
# Editar .env con tus API keys

# Ejecutar
python main.py
```

### Linux/Ubuntu

```bash
# Clonar repositorio
git clone https://github.com/AndresDvst/BotCryptoV2.git
cd BotCryptoV2

# Crear entorno virtual
python3.11 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
nano .env  # Editar con tus API keys

# Ejecutar
python main.py
```

---

## ⚙️ Configuración

### Variables de Entorno (.env)

```env
# ========== BINANCE ==========
BINANCE_API_KEY=tu_api_key
BINANCE_API_SECRET=tu_api_secret

# ========== TELEGRAM (3 bots diferentes) ==========
TELEGRAM_BOT_CRYPTO=token_bot_crypto
TELEGRAM_BOT_MARKETS=token_bot_markets
TELEGRAM_BOT_SIGNALS=token_bot_signals

TELEGRAM_CHAT_ID_CRYPTO=chat_id_crypto
TELEGRAM_CHAT_ID_MARKETS=chat_id_markets
TELEGRAM_CHAT_ID_SIGNALS=chat_id_signals

# Grupos (opcional)
TELEGRAM_GROUP_CRYPTO=@tu_canal_crypto
TELEGRAM_GROUP_MARKETS=@tu_canal_markets
TELEGRAM_GROUP_SIGNALS=@tu_canal_signals

# ========== TWITTER ==========
TWITTER_USERNAME=tu_usuario
TWITTER_PASSWORD=tu_password
TWITTER_HEADLESS=False

# ========== APIs ==========
GOOGLE_GEMINI_API_KEY=tu_gemini_key
TWELVEDATA_API_KEY=tu_twelve_data_key

# ========== CONFIGURACIÓN ==========
MIN_CHANGE_PERCENT=10
BOT_MODE=menu  # menu, 1, 2, 12

# ========== MYSQL (opcional) ==========
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=tu_password
MYSQL_DATABASE=crypto_bot
```

### Obtener API Keys

| Servicio | URL | Notas |
|----------|-----|-------|
| Binance | [API Management](https://www.binance.com/en/my/settings/api-management) | Solo lectura |
| Telegram | [@BotFather](https://t.me/BotFather) | Crear 3 bots |
| Twitter | [Developer Portal](https://developer.twitter.com/) | Read & Write |
| Gemini | [AI Studio](https://aistudio.google.com/) | Gratis, 60 req/min |
| Twelve Data | [Dashboard](https://twelvedata.com/) | 800 req/día gratis |

---

## 💻 Uso

### Menú Principal

```
============================================================
💡 MENÚ PRINCIPAL - CRYPTO BOT V3
============================================================
1.  🌟 Análisis Completo (Todo en un ciclo)
2.  ⏰ Programar ejecuciones automáticas (cada 2h + 6 AM)
3.  🚀 Análisis Básico (solo crypto)
4.  📊 Abrir Dashboard Web
5.  🧹 Limpiar repositorio
6.  🗑️  Limpiar base de datos
7.  📈 Análisis de Mercados Tradicionales
8.  🎯 Análisis Técnico con Señales
9.  🔄 Modo Continuo (Monitoreo 5 min)
10. 📰 Scraping de Noticias TradingView
11. 🔁 Reiniciar Bot
12. ⏰ Modo Espera Inteligente
13. 🧪 Backtesting
14. 📝 Prueba de Mensajes Telegram
0.  👋 Salir
============================================================
```

### Opciones Recomendadas

| Opción | Cuándo usar |
|--------|-------------|
| **1** | Primera ejecución, ver todo funcionando |
| **12** | Operación 24/7 (monitoreo + reportes automáticos) |
| **2** | Solo reportes programados cada 2h |
| **8** | Obtener señales de trading con análisis técnico |

---

## 🐳 Despliegue con Docker

### Requisitos VPS

- Ubuntu 22.04/24.04
- 2GB RAM mínimo (3GB+ recomendado)
- 20GB disco
- Puertos 6080 y 5900 abiertos

### Instalación Rápida

```bash
# Instalar Docker
curl -fsSL https://get.docker.com | sh

# Clonar repositorio
cd /opt
sudo git clone https://github.com/AndresDvst/BotCryptoV2.git
cd BotCryptoV2
sudo chown -R $USER:$USER .

# Configurar
cp .env.example .env
nano .env  # Añadir tus API keys

# Construir y ejecutar
sudo docker compose build
sudo docker compose up -d

# Ver logs
sudo docker compose logs -f
```

### Modo Interactivo (ver menú)

```bash
# Conectar al contenedor
sudo docker attach cryptobot

# Para salir sin matar el bot: Ctrl+P, Ctrl+Q
```

### noVNC (ver navegador Chrome)

Accede a `http://TU_IP:6080` para ver el navegador y hacer login en Twitter.

### Variables de Entorno Docker

| Variable | Descripción | Default |
|----------|-------------|---------|
| `BOT_MODE` | Modo de ejecución (menu, 1, 2, 12) | menu |
| `DOCKER_ENV` | Detectar entorno Docker | true |
| `TZ` | Zona horaria | America/Bogota |

---

## 🏗️ Arquitectura

### Estructura del Proyecto

```
BotCryptoV2/
├── main.py                    # Punto de entrada
├── bot_orchestrator.py        # Orquestador de servicios
├── config/
│   └── config.py              # Configuración centralizada
├── services/
│   ├── binance_service.py     # API Binance
│   ├── telegram_service.py    # Envío Telegram
│   ├── twitter_service.py     # Publicación Twitter
│   ├── ai_analyzer_service.py # Análisis con Gemini
│   ├── technical_analysis_service.py  # Señales trading
│   ├── traditional_markets_service.py # Stocks/Forex
│   ├── news_service.py        # Noticias crypto
│   ├── price_monitor_service.py # Monitoreo tiempo real
│   ├── twelve_data_service.py # API Twelve Data
│   └── backtest_service.py    # Backtesting
├── core/
│   ├── indicators.py          # Indicadores técnicos
│   ├── strategies/            # Estrategias de trading
│   └── risk/                  # Gestión de riesgo
├── database/
│   ├── db_manager.py          # SQLite
│   └── mysql_manager.py       # MySQL
├── dashboard/
│   └── app.py                 # Dashboard Flask
├── docker/
│   ├── supervisord.conf       # Gestor procesos
│   └── entrypoint.sh          # Script inicio
├── images/                    # Imágenes para reportes
├── logs/                      # Logs diarios
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

### Flujo de Datos

```
Binance API ──┐
Twelve Data ──┼──▶ Orquestador ──▶ Gemini AI ──▶ Telegram
CryptoPanic ──┘                                    └──▶ Twitter
```

---

## 🛠️ Solución de Problemas

### Error: ChromeDriver no encontrado

```bash
# El bot detecta automáticamente el SO
# Windows: usa utils/chromedriver.exe
# Linux/Docker: usa /usr/bin/chromedriver
```

### Error: Twitter login falla

1. Accede a noVNC: `http://TU_IP:6080`
2. Abre Chrome y haz login manualmente
3. La sesión se guarda en `chrome_profile/`

### Error: API Rate Limit

```bash
# Twelve Data: 800 req/día (gratis)
# Gemini: 60 req/min
# Binance: 1200 req/min
```

### Container se reinicia

```bash
# Ver logs detallados
sudo docker compose logs --tail 100

# Entrar al container
sudo docker exec -it cryptobot bash
```

---

## 📊 Imágenes para Reportes

Coloca estas imágenes en `images/`:

| Archivo | Uso |
|---------|-----|
| `REPORTE 2H.png` | Reportes cada 2 horas |
| `REPORTE 24H.png` | Reporte matutino 6 AM |
| `ACCIONES.png` | Mercado de acciones |
| `FOREX.png` | Mercado forex |
| `MINERALES.png` | Commodities |
| `SEÑALES.png` | Señales de trading |

**Tamaño recomendado**: 1200x675 px, < 5MB

---

## 🔐 Seguridad

- ❌ **NUNCA** subas `.env` a GitHub
- ✅ El `.gitignore` protege archivos sensibles
- ✅ Usa API keys con permisos mínimos (solo lectura en Binance)
- ✅ El bot detecta rutas de Windows vs Linux automáticamente

---

## 📄 Licencia

MIT License - Proyecto de código abierto para fines educativos.

---

## ⚠️ Disclaimer

Este bot es solo para análisis e información. **NO constituye asesoría financiera**. Las criptomonedas son volátiles y puedes perder dinero. Investiga antes de invertir.

---

<div align="center">

**⭐ Si te gusta este proyecto, dale una estrella en GitHub ⭐**

[WhatsApp](https://wa.link/a3j64p) • [Twitter](https://twitter.com/AndresDvst25) • [LinkedIn](https://www.linkedin.com/in/andresdevback22/) • [GitHub](https://github.com/AndresDvst)

_Hecho con ❤️ por [AndresDvst](https://github.com/AndresDvst)_

</div>


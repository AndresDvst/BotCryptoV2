<div align="center">

[![WhatsApp](https://img.shields.io/badge/WhatsApp-25D366?style=for-the-badge&logo=whatsapp&logoColor=white)](https://wa.me/573001234567?text=Hola%20desde%20BotCryptoV2)
[![X / Twitter](https://img.shields.io/badge/X/Twitter-000000?style=for-the-badge&logo=x&logoColor=white)](https://twitter.com/AndresDvst25)
[![Facebook](https://img.shields.io/badge/Facebook-1877F2?style=for-the-badge&logo=facebook&logoColor=white)](https://facebook.com/AndresDvst)
[![Instagram](https://img.shields.io/badge/Instagram-E4405F?style=for-the-badge&logo=instagram&logoColor=white)](https://instagram.com/AndresDvst)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://linkedin.com/in/andresdvst)
[![Notion](https://img.shields.io/badge/Notion-000000?style=for-the-badge&logo=notion&logoColor=white)](https://www.notion.so/AndresDvst)
[![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/AndresDvst/BotCryptoV2)

</div>

# BotCryptoV2

**Bot inteligente para análisis automatizado del mercado de criptomonedas**

Monitorea cambios significativos del mercado cada 2 horas, genera reportes detallados con inteligencia artificial (Google Gemini), envía notificaciones a Telegram y publica automáticamente resúmenes en X (Twitter).

## Características principales

- Consulta en tiempo real a **Binance** y **Bybit** para detectar movimientos ≥10% en 24h
- Análisis de cambios en las últimas 2 horas (solo monedas listadas en ambos exchanges)
- Integración de **sentimiento del mercado**: Fear & Greed Index + datos globales de CoinGecko
- Análisis y recomendaciones generadas por **Google Gemini 1.5-flash**
- Reportes matutinos especiales (6:00 AM) y cada 2 horas
- Envío automático de reportes formateados a **Telegram**
- Publicación de **4 tweets** independientes en X con delays anti-ban y adjunto de imagen
- Logging detallado y coloreado (consola + archivos diarios)
- Configuración segura mediante archivo `.env`
- Arquitectura modular y fácil de extender

## Estructura del proyecto

BotCryptoV2/
├── config/                    # Configuración central
│   └── config.py
├── services/                  # Servicios independientes
│   ├── binance_service.py
│   ├── bybit_service.py
│   ├── market_sentiment_service.py
│   ├── ai_analyzer_service.py
│   ├── telegram_service.py
│   └── twitter_service.py
├── utils/                     # Utilidades
│   └── logger.py
├── images/                    # Imágenes para tweets
│   ├── morning_report.png     # Reporte matutino (6 AM)
│   └── crypto_report.png      # Reportes regulares
├── logs/                      # Logs generados automáticamente
├── main.py                    # Punto de entrada principal
├── bot_orchestrator.py        # Orquestador del flujo completo
├── requirements.txt           # Dependencias del proyecto
├── .env.example               # Plantilla de variables de entorno
├── README.md                  # Esta documentación
├── COMANDOS_ÚTILES.md
├── ESTRUCTURA_PROYECTO.md
├── GEMINI_SETUP.md
└── TWITTER_SETUP.md

## Requisitos

- Python 3.8 o superior
- Cuenta de API en **Binance**, **Bybit**, **Telegram**, **Google Gemini**
- Credenciales de X (Twitter) para publicación automática (usuario/contraseña o sesión persistente)
- Imágenes personalizadas en la carpeta `images/` (1200×675 px recomendados)

### Dependencias (requirements.txt actualizado)

ccxt==4.2.25
requests==2.31.0
selenium==4.16.0
webdriver-manager==4.0.1
google-generativeai==0.3.2
schedule==1.2.0
python-dotenv==1.0.0
python-dateutil==2.8.2
colorlog==6.8.0
pyperclip==1.8.2

## Instalación paso a paso

1. Clona el repositorio

```bash
git clone https://github.com/AndresDvst/BotCryptoV2.git
cd BotCryptoV2

Crea y configura el entorno virtual (opcional pero recomendado)

bash

python -m venv venv
source venv/bin/activate    # Linux / macOS
# o en Windows:
venv\Scripts\activate

Instala las dependencias

bash

pip install -r requirements.txt

Configura las variables de entorno

Copia el archivo de ejemplo:bash

cp .env.example .env

Edita .env y completa todas las claves necesarias (ver guías en GEMINI_SETUP.md y TWITTER_SETUP.md).Prepara las imágenes

Coloca o crea dos archivos PNG en la carpeta images/:morning_report.png → para reporte de las 6 AM
crypto_report.png → para reportes regulares

Ejecuta el bot

bash

python main.py

Elige una de las opciones:1 → Ejecutar análisis inmediato
2 → Iniciar modo programado (cada 2 horas + 6 AM)
3 → Ambos (inmediato + programado)

Flujo de funcionamientoCarga configuración y valida claves API
Consulta Binance → filtra monedas con |cambio 24h| ≥ 10%
Cruza con Bybit → obtiene cambios en últimas 2 horas
Recopila sentimiento del mercado (Fear & Greed, CoinGecko)
Genera análisis completo con Google Gemini
Envía reporte detallado a Telegram
Publica 4 tweets en X con delays y adjunto de imagen
Registra todo en logs y programa la siguiente ejecución

Solución de problemas comunesError de API keys → Revisa .env y verifica que no tengan espacios ni comillas extras
Twitter/X no publica → Prueba con headless=False en twitter_service.py para ver el navegador y depurar login
Gemini no responde → Confirma que la clave API es válida y que el modelo 1.5-flash está disponible en tu región
Telegram no envía → Verifica token y chat_id con un mensaje de prueba vía curl o Postman
Dependencias fallan → Actualiza pip (pip install --upgrade pip) y vuelve a instalar

DisclaimerEste proyecto es educativo y experimental.
No constituye asesoría financiera. El mercado de criptomonedas es altamente volátil. Usa la información bajo tu propio riesgo.Contribuciones¡Las contribuciones son bienvenidas! Si quieres agregar soporte para más exchanges, notificaciones por email, dashboard web o mejoras en la IA, abre un issue o pull request.<div align="center">

![WhatsApp](https://img.shields.io/badge/WhatsApp-25D366?style=for-the-badge&logo=whatsapp&logoColor=white)
![X / Twitter](https://img.shields.io/badge/X/Twitter-000000?style=for-the-badge&logo=x&logoColor=white)
![Facebook](https://img.shields.io/badge/Facebook-1877F2?style=for-the-badge&logo=facebook&logoColor=white)
![Instagram](https://img.shields.io/badge/Instagram-E4405F?style=for-the-badge&logo=instagram&logoColor=white)
![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)
![Notion](https://img.shields.io/badge/Notion-000000?style=for-the-badge&logo=notion&logoColor=white)
![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)</div>
```


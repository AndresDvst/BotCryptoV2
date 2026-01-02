# 🐦 Guía Detallada: Configuración de Twitter/X

Esta guía te explica paso a paso cómo configurar Twitter para que el bot pueda publicar automáticamente.

## ⚠️ IMPORTANTE: Dos Métodos Disponibles

El bot incluye automatización con Selenium (simula un navegador), pero Twitter puede detectar bots y bloquear la cuenta. Por eso, te recomiendo configurarlo manualmente la primera vez.

## Método 1: Manual (Recomendado para empezar)

### Pasos:

1. **Ejecuta el bot** con `python main.py`
2. Cuando el bot termine el análisis, verás en la terminal el **texto del tweet** generado
3. **Copia** ese texto
4. Abre Twitter en tu navegador
5. **Pega** el texto en un nuevo tweet
6. Adjunta manualmente la imagen desde `images/`
7. Publica

**Ventajas:**
- ✅ Sin riesgo de bloqueo
- ✅ Más seguro
- ✅ Control total

**Desventajas:**
- ❌ Requiere intervención manual cada 2 horas

## Método 2: Automatizado con Selenium

### Pre-requisitos:

1. **Chrome instalado** en tu computadora
2. Cuenta de Twitter activa
3. Paciencia (Twitter tiene muchas medidas anti-bot)

### Configuración:

#### Paso 1: Modificar el código

En `main.py`, busca esta sección (línea ~30):

```python
# Nota: El login de Twitter debe hacerse una sola vez
# Por ahora, comentamos la publicación automática
# twitter_success = self.twitter.post_tweet(short_summary, image_path)
```

Descomenta la última línea:

```python
twitter_success = self.twitter.post_tweet(short_summary, image_path)
```

#### Paso 2: Configurar credenciales

En `bot_orchestrator.py`, después de inicializar los servicios, agrega:

```python
# Login único en Twitter
self.twitter.setup_twitter_login("tu_usuario", "tu_contraseña")
```

#### Paso 3: Primera ejecución

1. Ejecuta el bot
2. Se abrirá una ventana de Chrome
3. Observa cómo el bot hace login (¡es fascinante!)
4. Si Twitter pide verificación (código por email/SMS), **detén el bot** y hazlo manual

### ⚠️ Problemas Comunes con Selenium

#### Problema 1: "ChromeDriver incompatible"

**Solución:** El bot descarga automáticamente el driver correcto, pero si falla:

```bash
pip install --upgrade webdriver-manager
```

#### Problema 2: Twitter pide verificación

**Solución:** Twitter detecta comportamiento de bot. Opciones:

1. **Solución A**: Usa el Método 1 (manual)
2. **Solución B**: Configura 2FA en tu cuenta de Twitter y usa un código de aplicación
3. **Solución C**: Crea una cuenta de Twitter específica para el bot

#### Problema 3: "Element not found"

**Solución:** Twitter cambia frecuentemente su HTML. Si el bot no puede encontrar los botones:

1. Abre `services/twitter_service.py`
2. Busca los selectores CSS
3. Usa las herramientas de desarrollador de Chrome (F12) para encontrar los nuevos selectores
4. Actualiza el código

### 🔒 Recomendaciones de Seguridad

1. **Nunca uses tu cuenta principal** de Twitter para automatización
2. Crea una cuenta secundaria específica para el bot
3. No ejecutes el bot más de 4-5 veces al día (evita límites de Twitter)
4. Agrega delays aleatorios para parecer más humano

### 📝 Ejemplo de uso con Selenium

```python
from services.twitter_service import TwitterService

# Crear instancia
twitter = TwitterService()

# Login (solo una vez)
twitter.login_twitter("tu_usuario", "tu_contraseña")

# Publicar tweet
texto = "🚀 Análisis de mercado cripto..."
imagen = "./images/crypto_report.png"
twitter.post_tweet(texto, imagen)

# Cerrar navegador
twitter.close()
```

## Método 3: API Oficial de Twitter (Avanzado)

Si quieres usar la API oficial de Twitter (más confiable pero más complejo):

### Pre-requisitos:

1. Cuenta de desarrollador de Twitter aprobada
2. Acceso a API v2 con permisos de escritura
3. Suscripción Pro de Twitter (≈$100/mes) o Free tier (muy limitado)

### Configuración con Tweepy:

```python
import tweepy

# Autenticación
auth = tweepy.OAuthHandler(API_KEY, API_SECRET)
auth.set_access_token(ACCESS_TOKEN, ACCESS_SECRET)
api = tweepy.API(auth)

# Publicar con imagen
media = api.media_upload("imagen.png")
api.update_status(status="Tweet text", media_ids=[media.media_id])
```

## 🎯 Mi Recomendación

Para empezar y aprender:

1. **Usa el Método 1 (Manual)** por 1-2 semanas
2. Observa cómo funciona el bot y qué reportes genera
3. Si todo va bien, prueba el **Método 2 (Selenium)** con una cuenta secundaria
4. Solo si realmente lo necesitas, invierte en la **API oficial**

## 🆘 Alternativa: Webhooks

Si la automatización de Twitter es muy complicada, puedes:

1. Configurar un webhook (Zapier, IFTTT)
2. El bot envía el reporte a Telegram
3. El webhook detecta el mensaje de Telegram
4. Automáticamente publica en Twitter

**Ventaja**: No requiere código adicional  
**Desventaja**: Servicios de terceros (algunos son de pago)

## 📊 Comparación de Métodos

| Característica | Manual | Selenium | API Oficial |
|---------------|--------|----------|-------------|
| Dificultad | 🟢 Fácil | 🟡 Media | 🔴 Alta |
| Costo | Gratis | Gratis | $100/mes |
| Riesgo de bloqueo | Ninguno | Alto | Bajo |
| Automatización | No | Sí | Sí |
| Confiabilidad | 100% | 70% | 95% |
| Mantenimiento | Ninguno | Alto | Bajo |

## 💡 Consejo Final

**No te compliques desde el inicio.**

El valor del proyecto está en:
- ✅ La integración de múltiples APIs
- ✅ El análisis con IA
- ✅ La arquitectura del código
- ✅ La automatización del análisis

Que las publicaciones en Twitter sean manuales los primeros días **NO reduce el valor del proyecto** para tu portfolio. Una vez que domines el resto, podrás agregar la automatización de Twitter con calma.

---

**¿Necesitas ayuda?** Los logs del bot te dirán exactamente qué está fallando. Revisa `logs/bot_YYYYMMDD.log`
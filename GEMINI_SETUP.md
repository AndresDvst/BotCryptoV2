# 🤖 Guía Completa: Obtener API Key de Google Gemini

## ¿Por qué Gemini?

✅ **Completamente GRATIS** - Sin necesidad de tarjeta de crédito  
✅ **60 solicitudes por minuto** - Más que suficiente para el bot  
✅ **Fácil de obtener** - En 2 minutos tienes tu API Key  
✅ **Potente** - Gemini 1.5 Flash es muy capaz para análisis  
✅ **Sin cargos ocultos** - Google lo ofrece gratis permanentemente

## 📋 Paso a Paso para Obtener tu API Key

### Opción 1: Google AI Studio (Recomendado)

#### Paso 1: Acceder a Google AI Studio

1. Ve a: **https://aistudio.google.com/**
2. Haz clic en **"Sign in"** en la esquina superior derecha
3. Inicia sesión con tu cuenta de Gmail

#### Paso 2: Crear API Key

1. Una vez dentro, busca en el menú lateral izquierdo **"Get API key"**
2. O ve directamente a: **https://aistudio.google.com/app/apikey**
3. Haz clic en el botón azul **"Create API key"**

#### Paso 3: Seleccionar o Crear Proyecto

Verás dos opciones:

**Opción A: Crear en nuevo proyecto** (Recomendado si es tu primera vez)
- Haz clic en "Create API key in new project"
- Google creará automáticamente un proyecto para ti
- ¡Listo! Tu API Key se generará instantáneamente

**Opción B: Usar proyecto existente**
- Si ya tienes un proyecto de Google Cloud
- Selecciona "Create API key in existing project"
- Elige tu proyecto de la lista
- Se generará la API Key

#### Paso 4: Copiar tu API Key

1. Aparecerá un cuadro con tu API Key
2. Se ve algo así: `AIzaSyC-xxxxxxxxxxxxxxxxxxxxxxxxxxx`
3. Haz clic en el botón **"Copy"** o copia manualmente
4. **¡IMPORTANTE!**: Guárdala en un lugar seguro

### Opción 2: Google Cloud Console (Alternativa)

Si prefieres usar Google Cloud Console:

#### Paso 1: Crear Proyecto

1. Ve a: **https://console.cloud.google.com/**
2. Crea un nuevo proyecto o selecciona uno existente
3. Nombra tu proyecto (ej: "crypto-bot")

#### Paso 2: Habilitar API

1. Ve a **"APIs & Services"** → **"Library"**
2. Busca **"Generative Language API"**
3. Haz clic en **"Enable"**

#### Paso 3: Crear Credenciales

1. Ve a **"APIs & Services"** → **"Credentials"**
2. Haz clic en **"Create Credentials"**
3. Selecciona **"API Key"**
4. Se generará tu API Key
5. Cópiala y guárdala

## 🔐 Configurar en el Bot

Una vez que tengas tu API Key:

### 1. Abre el archivo `.env`

```bash
# Puedes usar cualquier editor de texto
notepad .env        # Windows
nano .env          # Linux/Mac
code .env          # VS Code
```

### 2. Pega tu API Key

```env
# GOOGLE GEMINI API (para análisis con IA)
GOOGLE_GEMINI_API_KEY=AIzaSyC-tu_clave_real_aqui
```

**Ejemplo real** (no uses esta, es solo un ejemplo):
```env
GOOGLE_GEMINI_API_KEY=AIzaSyDGxE8FqPdJ7nXkL9mQR2tUvW3xYz4AbCd
```

### 3. Guarda el archivo

Presiona `Ctrl + S` (Windows) o `Cmd + S` (Mac)

## ✅ Verificar que Funciona

### Prueba rápida en Python:

```python
import google.generativeai as genai

# Configura tu API key
genai.configure(api_key="TU_API_KEY_AQUI")

# Crea el modelo
model = genai.GenerativeModel('gemini-1.5-flash')

# Prueba básica
response = model.generate_content("Dime un dato curioso sobre Bitcoin")
print(response.text)
```

Si ves una respuesta, ¡funciona perfectamente! 🎉

### O usa el verificador del bot:

```bash
python check_setup.py
```

Debe mostrar:
```
✅ Google Gemini API Key
```

## 🚨 Solución de Problemas

### Error: "API key not valid"

**Causa**: La API key no es correcta o no está bien copiada

**Solución**:
1. Ve a https://aistudio.google.com/app/apikey
2. Verifica que copiaste la clave completa
3. Asegúrate de no tener espacios al inicio o al final
4. La clave debe empezar con `AIza`

### Error: "Generative Language API has not been enabled"

**Causa**: La API no está habilitada en tu proyecto

**Solución**:
1. Ve a https://console.cloud.google.com/
2. Selecciona tu proyecto
3. Ve a "APIs & Services" → "Library"
4. Busca "Generative Language API"
5. Haz clic en "Enable"
6. Espera 1-2 minutos y prueba de nuevo

### Error: "Quota exceeded"

**Causa**: Has excedido el límite de 60 solicitudes por minuto

**Solución**:
- Espera 1 minuto y prueba de nuevo
- El bot ejecuta cada 2 horas, así que no deberías tener este problema
- Si lo necesitas más frecuentemente, considera espaciar más las ejecuciones

### Error: "PERMISSION_DENIED"

**Causa**: Tu cuenta de Google tiene restricciones

**Solución**:
1. Asegúrate de tener una cuenta de Google válida
2. Algunos correos corporativos tienen restricciones
3. Usa una cuenta personal de Gmail
4. Ve a https://console.cloud.google.com/billing y verifica el estado

## 📊 Límites y Cuotas (Nivel Gratuito)

| Característica | Límite Gratuito |
|---------------|-----------------|
| Solicitudes por minuto | 60 |
| Solicitudes por día | 1,500 |
| Tokens por minuto | 32,000 |
| Tokens por solicitud | 8,192 (entrada) + 8,192 (salida) |
| Costo | **$0.00** (GRATIS) |

**Para nuestro bot** (ejecuta cada 2 horas):
- Solicitudes por día: ~24 (12 ejecuciones × 2 llamadas a IA)
- Tokens por día: ~6,000
- **Conclusión**: Estamos MUY por debajo de los límites 🎉

## 🎯 Modelos Disponibles

El bot usa **gemini-1.5-flash** por defecto (el mejor para este caso):

| Modelo | Velocidad | Calidad | Costo | Recomendado |
|--------|-----------|---------|-------|-------------|
| gemini-1.5-flash | ⚡⚡⚡ Muy rápido | ⭐⭐⭐ Buena | Gratis | ✅ SÍ (por defecto) |
| gemini-1.5-pro | ⚡⚡ Rápido | ⭐⭐⭐⭐⭐ Excelente | Gratis | Solo si necesitas más calidad |
| gemini-1.0-pro | ⚡ Normal | ⭐⭐⭐ Buena | Gratis | No recomendado |

**Para cambiar de modelo**, edita `services/ai_analyzer_service.py`:

```python
# Línea 38, cambia:
self.model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",  # Cambiar aquí
    ...
)

# Opciones:
# - "gemini-1.5-flash"  (por defecto, recomendado)
# - "gemini-1.5-pro"    (más inteligente pero más lento)
# - "gemini-1.0-pro"    (versión anterior)
```

## 💡 Consejos Pro

### 1. Protege tu API Key

```bash
# NUNCA hagas esto:
git add .env
git commit -m "agregando configuración"
git push

# SIEMPRE asegúrate que .env está en .gitignore
echo ".env" >> .gitignore
```

### 2. Monitorea tu Uso

Ve a: https://console.cloud.google.com/apis/dashboard

Aquí puedes ver:
- ✅ Cuántas solicitudes has hecho
- ✅ Si estás cerca del límite
- ✅ Errores recientes

### 3. Múltiples Proyectos

Si tienes varios proyectos con IA:
- Crea una API Key diferente para cada uno
- Así puedes monitorear el uso por separado
- Puedes revocar una sin afectar las demás

### 4. Backup de tu API Key

Guarda tu API Key en un lugar seguro:
- ✅ Gestor de contraseñas (1Password, Bitwarden)
- ✅ Archivo encriptado en tu computadora
- ✅ Nota en tu teléfono con Face ID
- ❌ NUNCA en GitHub, Discord, o lugares públicos

## 🔄 Regenerar API Key

Si perdiste tu API Key o crees que está comprometida:

1. Ve a https://aistudio.google.com/app/apikey
2. Encuentra tu API Key en la lista
3. Haz clic en los tres puntos (⋮)
4. Selecciona **"Delete"**
5. Crea una nueva con **"Create API key"**
6. Actualiza tu archivo `.env` con la nueva clave

## 🎓 Recursos Adicionales

- **Documentación oficial**: https://ai.google.dev/docs
- **Ejemplos de código**: https://ai.google.dev/tutorials
- **Playground interactivo**: https://aistudio.google.com/
- **Límites y cuotas**: https://ai.google.dev/pricing
- **Guía de inicio rápido**: https://ai.google.dev/tutorials/python_quickstart

## ❓ Preguntas Frecuentes

### ¿Necesito tarjeta de crédito?

**NO.** Gemini es completamente gratis para uso personal y desarrollo. No necesitas ningún método de pago.

### ¿Por cuánto tiempo es gratis?

Google ha indicado que el nivel gratuito es **permanente** para el modelo Gemini 1.5 Flash. Aunque siempre pueden cambiar las políticas en el futuro.

### ¿Puedo usarlo comercialmente?

Sí, el nivel gratuito permite uso comercial con los límites mencionados. Para proyectos grandes, existe un plan de pago.

### ¿Es mejor que ChatGPT/Claude?

Para este bot, Gemini 1.5 Flash es perfecto porque:
- ✅ Es GRATIS sin límites estrictos
- ✅ Es muy rápido (responde en 1-2 segundos)
- ✅ La calidad es excelente para análisis de datos
- ✅ No necesitas poner tarjeta de crédito

### ¿Puedo cambiar a otro modelo después?

¡Claro! El código está diseñado para ser flexible. Solo necesitas:
1. Modificar `ai_analyzer_service.py`
2. Cambiar las llamadas a la API
3. Actualizar las variables de entorno

---

**¡Ya tienes todo listo para usar Gemini en tu bot!** 🚀

Si tienes problemas, ejecuta:
```bash
python check_setup.py
```

Y revisa los logs en:
```bash
cat logs/bot_*.log
```
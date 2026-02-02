# 🐳 Guía de Despliegue en VPS Ubuntu

## 📋 Requisitos Previos
- VPS Ubuntu 22.04 o 24.04
- Mínimo 2GB RAM (recomendado 3GB+)
- 20GB espacio en disco
- Puertos 6080 y 5900 abiertos

---

## 🚀 PASO 1: Conectar a la VPS

```bash
ssh root@TU_IP_VPS
# O con usuario normal:
ssh usuario@TU_IP_VPS
```

---

## 🔧 PASO 2: Instalar Docker

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependencias
sudo apt install -y apt-transport-https ca-certificates curl gnupg lsb-release

# Añadir clave GPG de Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Añadir repositorio
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Instalar Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Verificar instalación
docker --version
docker compose version

# (Opcional) Añadir tu usuario al grupo docker para no usar sudo
sudo usermod -aG docker $USER
# Cierra sesión y vuelve a entrar para que aplique
```

---

## 📁 PASO 3: Subir el Proyecto

### Opción A: Con Git (recomendado)
```bash
cd /opt
sudo git clone https://github.com/AndresDvst/BotCryptoV2.git
cd BotCryptoV2
sudo chown -R ubuntu:ubuntu .
```

### Opción B: Con SCP desde tu PC Windows
```powershell
# Ejecutar en PowerShell de tu PC
scp -i "C:\Users\WinterOS\Downloads\key.pem" -r I:\Proyectos\BotCryptoV2 ubuntu@IP:~

### En la vps
sudo mv ~/BotCryptoV2 /opt/
sudo chown -R ubuntu:ubuntu /opt/BotCryptoV2
cd /opt/BotCryptoV2

### Actualizar GIT
cd /opt/BotCryptoV2
git init
git remote add origin https://github.com/AndresDvst/BotCryptoV2.git
git fetch origin
git reset --hard origin/main
```

### Opción C: Con FileZilla
1. Conectar a la VPS por SFTP
2. Subir la carpeta a `/opt/BotCryptoV2`

---

## ⚙️ PASO 4: Configurar Variables de Entorno

```bash
cd /opt/BotCryptoV2

# Copiar el ejemplo
cp .env.example .env

# Editar con nano
nano .env
```

**Configurar estas variables (OBLIGATORIO):**
```env
# APIs
BINANCE_API_KEY=tu_api_key_aqui
BINANCE_API_SECRET=tu_api_secret_aqui
GOOGLE_GEMINI_API_KEY=tu_gemini_key_aqui

# Telegram
TELEGRAM_BOT_TOKEN=tu_token_aqui
TELEGRAM_CHAT_ID=tu_chat_id

# Twitter (si usas)
TWITTER_USERNAME=tu_usuario
TWITTER_PASSWORD=tu_password

# Twelve Data (opcional)
TWELVE_DATA_API_KEY=tu_key_aqui
```

**Guardar:** `Ctrl + O`, Enter, `Ctrl + X`

---

## 🔥 PASO 5: Abrir Puertos en el Firewall

```bash
# Si usas UFW
sudo ufw allow 6080/tcp   # noVNC
sudo ufw allow 5900/tcp   # VNC (opcional)
sudo ufw allow 22/tcp     # SSH
sudo ufw enable
sudo ufw status
```

---

## 🐳 PASO 6: Construir y Ejecutar

```bash
cd /opt/BotCryptoV2

# Construir la imagen (primera vez, tarda ~5-10 min)
sudo docker compose build

# Iniciar el contenedor
sudo docker compose up -d

# Ver logs en tiempo real
sudo docker compose logs -f
```

---

## 🔑 PASO 7: Login a Twitter (UNA SOLA VEZ)

1. **Abrir en tu navegador:** `http://TU_IP_VPS:6080`

2. Verás el escritorio virtual con Chrome

3. Abre Chrome y ve a `https://twitter.com`

4. Haz login con tu cuenta

5. ¡Listo! La sesión queda guardada en el volumen

---

## ✅ PASO 8: Verificar que Funciona

```bash
# Ver estado del contenedor
docker compose ps

# Ver logs del bot
docker compose logs -f cryptobot

# Verificar que Chrome profile existe
ls -la /opt/BotCryptoV2/chrome_profile/
```

---

## 📊 Comandos Útiles

```bash
# Detener el bot
docker compose down

# Reiniciar
docker compose restart

# Ver logs
docker compose logs -f

# Entrar al contenedor (debug)
docker exec -it cryptobot bash

# Reconstruir después de cambios
docker compose build --no-cache
docker compose up -d
```

---

## 🔄 Actualizar el Bot

```bash
cd /opt/BotCryptoV2

# Detener
docker compose down

# Actualizar código (si usas git)
git pull

# O resubir archivos con scp/sftp

# Reconstruir
docker compose build
docker compose up -d
```

---

## ⚠️ Solución de Problemas

### Chrome no abre en noVNC
```bash
docker compose logs | grep -i error
docker exec -it cryptobot google-chrome --version
```

### Sesión de Twitter perdida
```bash
# Verificar que el volumen existe
docker volume ls
ls -la /opt/BotCryptoV2/chrome_profile/
# Si está vacío, hacer login de nuevo en noVNC
```

### El contenedor se reinicia constantemente
```bash
docker compose logs --tail 100
# Buscar errores de Python o dependencias
```

### Memoria insuficiente
```bash
# Ver uso de memoria
docker stats
# Aumentar límite en docker-compose.yml
```

---

## 🔐 Seguridad (Recomendado)

### Proteger noVNC con contraseña
Editar `docker/supervisord.conf`:
```ini
[program:x11vnc]
command=/usr/bin/x11vnc -display :99 -forever -shared -rfbport 5900 -passwd TU_PASSWORD_AQUI
```

### Usar Nginx como proxy con SSL
```bash
sudo apt install nginx certbot python3-certbot-nginx

# Configurar proxy inverso para noVNC en puerto 443
```

---

## 📞 Soporte

Si tienes problemas:
1. Revisa los logs: `docker compose logs -f`
2. Verifica el .env tiene todas las variables
3. Comprueba que los puertos están abiertos
4. Asegúrate de tener suficiente RAM

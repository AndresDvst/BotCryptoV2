# 🚀 Guía de Despliegue en VPS Ubuntu

Esta guía cubre **dos métodos** de despliegue:
- **Método A (Recomendado):** Sin Docker, con escritorio remoto XFCE
- **Método B:** Con Docker (más complejo, problemas conocidos con Chrome)

---

# 📋 Requisitos Previos

- VPS Ubuntu 22.04 o 24.04 (AWS EC2, DigitalOcean, etc.)
- Mínimo 2GB RAM (recomendado 3GB+)
- 20GB espacio en disco
- Acceso SSH

---

# 🖥️ MÉTODO A: Sin Docker (RECOMENDADO)

Este método es más estable y permite ver Chrome visualmente para hacer login en Twitter.

## Paso 1: Conectar al VPS

```bash
ssh ubuntu@TU_IP_VPS
# O con clave .pem (AWS):
ssh -i "tu_clave.pem" ubuntu@TU_IP_VPS
```

## Paso 2: Instalar Escritorio LXDE + XRDP

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar escritorio LXDE (muy ligero, ~200MB RAM)
sudo apt install -y lxde-core lxterminal

# Instalar XRDP (servidor de escritorio remoto)
sudo apt install -y xrdp

# Configurar XRDP para usar LXDE
echo "startlxde" > ~/.xsession

# Reiniciar XRDP
sudo systemctl restart xrdp
sudo systemctl enable xrdp

# Abrir puerto 3389 en el firewall
sudo ufw allow 3389/tcp
sudo ufw allow 22/tcp
sudo ufw enable
```

> **Alternativas de escritorio:**
> | Escritorio | RAM | Comando de instalación |
> |------------|-----|------------------------|
> | LXDE (recomendado) | ~200MB | `sudo apt install -y lxde-core` |
> | LXQt | ~250MB | `sudo apt install -y lxqt` |
> | XFCE | ~400MB | `sudo apt install -y xfce4` |
> | Openbox (solo ventanas) | ~100MB | `sudo apt install -y openbox` |

## Paso 3: Crear contraseña para el usuario

```bash
sudo passwd ubuntu
# Ingresa una contraseña segura (2 veces)
```

## Paso 4: Abrir puerto 3389 en AWS Security Groups

1. Ve a la consola de AWS EC2
2. Selecciona tu instancia → Security Groups
3. Edit inbound rules
4. Agrega: **Type:** RDP, **Port:** 3389, **Source:** Tu IP o 0.0.0.0/0

## Paso 5: Conectar desde Windows

1. Abre **Conexión a Escritorio remoto** (busca "mstsc" en Windows)
2. Escribe: `TU_IP_VPS`
3. Usuario: `ubuntu`
4. Contraseña: la que creaste

## Paso 6: Instalar Python y dependencias

```bash
# Agregar repositorio para Python 3.11
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update

# Instalar Python 3.11
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# Clonar el proyecto
cd ~
git clone https://github.com/AndresDvst/BotCryptoV2.git
cd BotCryptoV2

# Crear entorno virtual
python3.11 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

## Paso 7: Instalar Chrome y ChromeDriver

sudo apt update
sudo apt install -y unzip

```bash
# Instalar Chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb
sudo apt --fix-broken install -y

# Instalar ChromeDriver compatible
CHROME_VERSION=$(google-chrome --version | grep -oP '\d+' | head -1)
wget "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/$(curl -s https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_$CHROME_VERSION)/linux64/chromedriver-linux64.zip"
unzip chromedriver-linux64.zip
sudo mv chromedriver-linux64/chromedriver /usr/bin/chromedriver
sudo chmod +x /usr/bin/chromedriver

# Verificar instalación
google-chrome --version
chromedriver --version
```

## Paso 8: Configurar .env

```bash
cd ~/BotCryptoV2
nano .env
```

**⚠️ IMPORTANTE:** Dejar vacías las rutas de Windows:
```env
# APIs (copiar tus valores reales)
BINANCE_API_KEY=tu_api_key
BINANCE_API_SECRET=tu_api_secret
GOOGLE_GEMINI_API_KEY=tu_gemini_key

# Telegram
TELEGRAM_BOT_CRYPTO=tu_token
TELEGRAM_CHAT_ID=tu_chat_id
# ... resto de variables

# Twitter
TWITTER_USERNAME=tu_usuario
TWITTER_PASSWORD=tu_password
TWITTER_EMAIL=tu_email

# IMPORTANTE: Dejar vacías en Linux
CHROMEDRIVER_PATH=
CHROME_USER_DATA_DIR=
TWITTER_HEADLESS=False
```

Guardar: `Ctrl+X`, `Y`, `Enter`

## Paso 9: Login de Twitter (UNA SOLA VEZ)

**Desde el escritorio remoto (XRDP):**

```bash
# Abrir Chrome con el perfil del bot
google-chrome --user-data-dir=/home/ubuntu/BotCryptoV2/chrome_profile
```

1. Ve a `https://x.com`
2. Haz login con tu cuenta de Twitter
3. **Cierra Chrome completamente**

## Paso 10: Ejecutar el Bot

```bash
cd ~/BotCryptoV2
source venv/bin/activate
python main.py
```

## Paso 11: Ejecutar en Segundo Plano (screen/tmux)

```bash
# Instalar screen
sudo apt install -y screen

# Crear sesión
screen -S cryptobot

# Dentro de la sesión, ejecutar el bot
cd ~/BotCryptoV2
source venv/bin/activate
python main.py

# Para desconectarte sin detener el bot: Ctrl+A, luego D

# Para reconectarte después:
screen -r cryptobot
```

---

# 🐳 MÉTODO B: Con Docker

⚠️ **Nota:** Este método tiene problemas conocidos con Chrome en Docker. Se recomienda el Método A.

## Problemas conocidos y soluciones:

### 1. Chrome "session not created" error
- **Causa:** Permisos del perfil de Chrome
- **Solución:** El código ahora usa `~/.config/cryptobot_chrome_profile` automáticamente

### 2. "cannot create default profile directory"
- **Causa:** El directorio montado no tiene permisos
- **Solución:** Agregar `shm_size: '2gb'` en docker-compose.yml

### 3. Perfil de Windows incompatible
- **Causa:** Copiar chrome_profile de Windows a Linux
- **Solución:** Eliminar el perfil y crear uno nuevo en Linux

## Instalación con Docker

```bash
# Instalar Docker
sudo apt update
sudo apt install -y apt-transport-https ca-certificates curl gnupg lsb-release
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Clonar proyecto
cd /opt
sudo git clone https://github.com/TU_USUARIO/BotCryptoV2.git
cd BotCryptoV2
sudo chown -R $USER:$USER .

# Configurar .env
cp .env.example .env
nano .env  # Configurar variables

# Construir y ejecutar
sudo docker compose build
sudo docker compose up -d

# Ver logs
sudo docker compose logs -f
```

## Acceso a noVNC (para login de Twitter)
1. Abrir: `http://TU_IP_VPS:6080`
2. Hacer click derecho → abrir terminal
3. Ejecutar: `google-chrome`
4. Login en Twitter

---

# 📊 Comandos Útiles

## Sin Docker
```bash
# Ejecutar bot
cd ~/BotCryptoV2 && source venv/bin/activate && python main.py

# Ver sesiones de screen
screen -ls

# Reconectar a sesión
screen -r cryptobot

# Matar sesión
screen -X -S cryptobot quit
```

## Con Docker
```bash
# Estado
docker compose ps

# Logs
docker compose logs -f

# Reiniciar
docker compose restart

# Detener
docker compose down

# Reconstruir
docker compose build --no-cache && docker compose up -d
```

---

# 🔧 Solución de Problemas

## Twitter no detecta la sesión
1. Asegúrate de abrir Chrome **con el perfil del bot**:
   ```bash
   google-chrome --user-data-dir=/home/ubuntu/BotCryptoV2/chrome_profile
   ```
2. Haz login en Twitter
3. **Cierra Chrome completamente**
4. Luego ejecuta el bot

## Error: "ChromeDriver not found"
```bash
# Verificar instalación
which chromedriver
chromedriver --version

# Reinstalar si es necesario
sudo apt remove chromedriver
# Seguir instrucciones del Paso 7
```

## Error de MySQL (no crítico)
El bot funciona sin MySQL. Si quieres instalarlo:
```bash
sudo apt install -y mysql-server
sudo mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '1234';"
sudo mysql -e "CREATE DATABASE crypto_bot;"
```

## El bot se cierra al desconectar SSH
Usa `screen` o `tmux`:
```bash
screen -S cryptobot
# Ejecutar bot
# Ctrl+A, D para desconectar
```

## Memoria insuficiente
```bash
# Ver uso de memoria
free -h

# Crear swap (si no tienes)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

# 🔐 Seguridad

## Cambiar puerto SSH (recomendado)
```bash
sudo nano /etc/ssh/sshd_config
# Cambiar Port 22 a otro número
sudo systemctl restart sshd
```

## Configurar fail2ban
```bash
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
```

---

# 📞 Resumen Rápido

## Método A (Sin Docker) - Comandos esenciales:
```bash
# Primera vez
sudo apt update && sudo apt install -y lxde-core lxterminal xrdp
echo "startlxde" > ~/.xsession
sudo systemctl restart xrdp
sudo passwd ubuntu
# Conectar con Escritorio Remoto de Windows

# En el servidor
cd ~/BotCryptoV2
source venv/bin/activate
python main.py
```

## Método B (Docker) - Comandos esenciales:
```bash
cd /opt/BotCryptoV2
sudo docker compose up -d
# Abrir http://IP:6080 para noVNC
```

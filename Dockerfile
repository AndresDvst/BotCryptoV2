# ============================================
# BotCryptoV2 - Dockerfile
# Python 3.11 + Chrome + noVNC para visualización
# ============================================

FROM python:3.11-slim-bookworm

# Evitar prompts interactivos
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Directorio de trabajo
WORKDIR /app

# ============================================
# 1. Instalar dependencias del sistema
# ============================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Dependencias básicas
    wget \
    curl \
    gnupg \
    ca-certificates \
    unzip \
    # Dependencias para Chrome
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    # Para noVNC y display virtual
    xvfb \
    x11vnc \
    fluxbox \
    novnc \
    websockify \
    # Utilidades
    procps \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# ============================================
# 2. Instalar Google Chrome
# ============================================
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# ============================================
# 3. Instalar ChromeDriver compatible
# ============================================
RUN CHROME_VERSION=$(google-chrome --version | grep -oP '\d+\.\d+\.\d+') \
    && DRIVER_VERSION=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_$(echo $CHROME_VERSION | cut -d. -f1)") \
    && wget -q "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/${DRIVER_VERSION}/linux64/chromedriver-linux64.zip" -O /tmp/chromedriver.zip \
    && unzip /tmp/chromedriver.zip -d /tmp/ \
    && mv /tmp/chromedriver-linux64/chromedriver /usr/bin/chromedriver \
    && chmod +x /usr/bin/chromedriver \
    && rm -rf /tmp/chromedriver*

# ============================================
# 4. Copiar requirements e instalar dependencias Python
# ============================================
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ============================================
# 5. Copiar código del proyecto
# ============================================
COPY . .

# ============================================
# 6. Configurar supervisord para manejar procesos
# ============================================
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# ============================================
# 7. Script de inicio
# ============================================
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# ============================================
# 8. Variables de entorno para Docker
# ============================================
ENV DISPLAY=:99
ENV CHROME_BINARY_PATH=/usr/bin/google-chrome
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
ENV DOCKER_ENV=true

# Puertos
# 6080 = noVNC (acceso web al navegador)
# 5900 = VNC directo (opcional)
EXPOSE 6080 5900

# Volumen para persistir datos
VOLUME ["/app/logs"]

ENTRYPOINT ["/entrypoint.sh"]

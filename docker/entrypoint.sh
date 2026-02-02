#!/bin/bash
set -e

echo "============================================"
echo "🚀 BotCryptoV2 - Iniciando contenedor"
echo "============================================"

# Crear directorios necesarios
mkdir -p /app/chrome_profile
mkdir -p /app/logs
mkdir -p /app/images/signals
mkdir -p /var/log/supervisor

# Permisos
chmod -R 777 /app/chrome_profile
chmod -R 777 /app/logs

# Crear archivos de historial si no existen
for file in news_history.json signals_history.json stats_history.json tweet_history.json traditional_signals_history.json; do
    if [ ! -f "/app/$file" ]; then
        echo "[]" > "/app/$file"
        echo "📄 Creado: $file"
    fi
done

# Archivo especial para stats
if [ ! -s "/app/stats_history.json" ] || [ "$(cat /app/stats_history.json)" = "[]" ]; then
    echo '{"entries":[]}' > /app/stats_history.json
fi

echo "============================================"
echo "📺 noVNC disponible en: http://localhost:6080"
echo "🔑 Perfil Chrome en: /app/chrome_profile"
echo "============================================"

# Iniciar servicios gráficos en background
/usr/bin/Xvfb :99 -screen 0 1920x1080x24 &
sleep 2
DISPLAY=:99 /usr/bin/fluxbox &
/usr/bin/x11vnc -display :99 -forever -shared -rfbport 5900 -nopw &
/usr/share/novnc/utils/novnc_proxy --vnc localhost:5900 --listen 6080 &

echo "============================================"
echo "🖥️ Servicios gráficos iniciados"
echo "============================================"

# Esperar a que X esté listo
sleep 3

# Ejecutar el bot en foreground (permite docker attach)
exec python /app/main.py

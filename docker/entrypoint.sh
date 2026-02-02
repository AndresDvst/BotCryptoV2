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

# Iniciar supervisord (maneja todos los procesos)
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf

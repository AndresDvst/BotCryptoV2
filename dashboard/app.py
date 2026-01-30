"""
Dashboard web para visualizar análisis del bot de criptomonedas
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, render_template, jsonify
from database.mysql_manager import MySQLManager
from config.config import Config

app = Flask(__name__)

# Obtener configuración de MySQL desde Config o usar valores por defecto
db = MySQLManager(
    host=getattr(Config, 'MYSQL_HOST', 'localhost'),
    user=getattr(Config, 'MYSQL_USER', 'root'),
    password=getattr(Config, 'MYSQL_PASSWORD', '1234'),
    database=getattr(Config, 'MYSQL_DATABASE', 'crypto_bot'),
    port=getattr(Config, 'MYSQL_PORT', 3306)
)



@app.route('/')
def dashboard():
    """Página principal del dashboard"""
    return render_template('dashboard.html')


@app.route('/api/latest')
def api_latest():
    """API: Obtiene el último análisis"""
    try:
        data = db.get_latest_analysis()
        if data:
            return jsonify(data)
        return jsonify({'error': 'No hay datos disponibles'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/historical/<int:days>')
def api_historical(days):
    """API: Obtiene datos históricos"""
    try:
        data = db.get_historical_data(days)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/coin/<symbol>/<int:days>')
def api_coin_history(symbol, days):
    """API: Obtiene histórico de una moneda específica"""
    try:
        data = db.get_coin_history(symbol, days)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats')
def api_stats():
    """API: Obtiene estadísticas generales"""
    try:
        stats = db.get_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🌐 CRYPTO BOT DASHBOARD")
    print("=" * 60)
    print("📊 Dashboard iniciado en: http://localhost:5000")
    print("⚠️  Solo para uso local - No exponer a internet")
    print("=" * 60 + "\n")
    
    app.run(debug=True, port=5000, host='127.0.0.1')

"""
Dashboard web para visualizar análisis del bot de criptomonedas
"""
import sys
import os
import re
import threading
from typing import Any, Callable, Dict, Optional, Tuple

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, render_template, jsonify
from database.mysql_manager import MySQLManager
from config.config import Config
from utils.logger import logger

app = Flask(__name__)
app.config['JSONIFY_MIMETYPE'] = 'application/json'
app.config['JSON_SORT_KEYS'] = False

_db_lock = threading.Lock()
_db_instance: Optional[MySQLManager] = None


def _init_db() -> MySQLManager:
    """
    Inicializa MySQLManager con configuración segura y por defecto si faltan valores.
    """
    return MySQLManager(
        host=getattr(Config, 'MYSQL_HOST', 'localhost'),
        user=getattr(Config, 'MYSQL_USER', 'root'),
        password=getattr(Config, 'MYSQL_PASSWORD', '1234'),
        database=getattr(Config, 'MYSQL_DATABASE', 'crypto_bot'),
        port=getattr(Config, 'MYSQL_PORT', 3306)
    )


def get_db() -> MySQLManager:
    """
    Obtiene la instancia global de MySQLManager de forma thread-safe.
    Reintenta inicializar si la instancia no existe.
    """
    global _db_instance
    if _db_instance is None:
        with _db_lock:
            if _db_instance is None:
                _db_instance = _init_db()
    return _db_instance


def json_response(data: Any = None, error: Optional[Dict[str, Any]] = None, status: str = "ok", http_status: int = 200):
    """
    Genera una respuesta JSON consistente con estructura {status, data, error}.
    """
    payload = {
        "status": status,
        "data": data if error is None else None,
        "error": error,
    }
    return jsonify(payload), http_status


def validate_days(days: int) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Valida el parámetro days: entero positivo y razonable (1-365).
    """
    if days < 1 or days > 365:
        return False, {"code": "invalid_days", "message": "El parámetro 'days' debe estar entre 1 y 365"}
    return True, None


def validate_symbol(symbol: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Valida el parámetro symbol: caracteres alfanuméricos y separadores simples.
    """
    if not symbol or len(symbol) > 20:
        return False, {"code": "invalid_symbol", "message": "El parámetro 'symbol' es inválido"}
    if not re.match(r'^[A-Za-z0-9_\-\.]+$', symbol):
        return False, {"code": "invalid_symbol", "message": "El parámetro 'symbol' contiene caracteres no permitidos"}
    return True, None


def _safe_db_call(call: Callable[[], Any]) -> Tuple[bool, Any, Optional[Dict[str, Any]]]:
    """
    Ejecuta una operación de DB con modo robusto:
    - Intento inicial
    - Si falla, re-inicializa la conexión y reintenta una vez
    """
    try:
        result = call()
        return True, result, None
    except Exception as e:
        logger.warning(f"⚠️ Error de DB, reintentando: {e}")
        # Re-inicializar y reintentar
        with _db_lock:
            try:
                globals()['_db_instance'] = _init_db()
            except Exception as init_err:
                logger.error(f"❌ Error re-inicializando DB: {init_err}")
                return False, None, {"code": "db_init_failed", "message": "No se pudo re-inicializar la base de datos"}
        try:
            result = call()
            return True, result, None
        except Exception as e2:
            logger.error(f"❌ Error persistente de DB: {e2}")
            return False, None, {"code": "db_failure", "message": "Error de base de datos"}


@app.errorhandler(404)
def handle_404(_):
    return json_response(error={"code": "not_found", "message": "Ruta no encontrada"}, status="error", http_status=404)


@app.errorhandler(500)
def handle_500(e):
    logger.error(f"❌ Error interno: {e}")
    return json_response(error={"code": "internal_error", "message": "Error interno del servidor"}, status="error", http_status=500)


@app.route('/')
def dashboard():
    """Página principal del dashboard"""
    return render_template('dashboard.html')


@app.route('/api/latest')
def api_latest():
    """API: Obtiene el último análisis"""
    ok, data, err = _safe_db_call(lambda: get_db().get_latest_analysis())
    if not ok:
        return json_response(error=err, status="error", http_status=500)
    if not data:
        return json_response(error={"code": "no_data", "message": "No hay datos disponibles"}, status="error", http_status=404)
    return json_response(data=data, status="ok", http_status=200)


@app.route('/api/historical/<int:days>')
def api_historical(days: int):
    """API: Obtiene datos históricos"""
    valid, err = validate_days(days)
    if not valid:
        return json_response(error=err, status="error", http_status=400)
    ok, data, err2 = _safe_db_call(lambda: get_db().get_historical_data(days))
    if not ok:
        return json_response(error=err2, status="error", http_status=500)
    return json_response(data=data, status="ok", http_status=200)


@app.route('/api/coin/<symbol>/<int:days>')
def api_coin_history(symbol: str, days: int):
    """API: Obtiene histórico de una moneda específica"""
    valid_days, err_days = validate_days(days)
    if not valid_days:
        return json_response(error=err_days, status="error", http_status=400)
    valid_sym, err_sym = validate_symbol(symbol)
    if not valid_sym:
        return json_response(error=err_sym, status="error", http_status=400)
    ok, data, err = _safe_db_call(lambda: get_db().get_coin_history(symbol.upper(), days))
    if not ok:
        return json_response(error=err, status="error", http_status=500)
    return json_response(data=data, status="ok", http_status=200)


@app.route('/api/stats')
def api_stats():
    """API: Obtiene estadísticas generales"""
    ok, stats, err = _safe_db_call(lambda: get_db().get_stats())
    if not ok:
        return json_response(error=err, status="error", http_status=500)
    return json_response(data=stats, status="ok", http_status=200)


if __name__ == '__main__':
    logger.info("🌐 CRYPTO BOT DASHBOARD")
    logger.info("📊 Iniciado en http://127.0.0.1:5000 (uso local)")
    # Debug desactivado para producción local
    app.run(debug=False, port=5000, host='127.0.0.1')

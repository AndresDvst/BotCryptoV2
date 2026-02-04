"""
Gestor de base de datos SQLite para el bot de criptomonedas
"""
import os
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from utils.logger import logger


class DatabaseManager:
    """Gestor de base de datos para almacenar análisis históricos (thread-safe)"""
    
    def __init__(self, db_path: str = "data/crypto_bot.db"):
        """
        Inicializa el gestor de base de datos
        
        Args:
            db_path: Ruta al archivo de base de datos
        """
        self.db_path = db_path
        self._lock = threading.RLock()
        
        # Crear directorio si no existe
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        
        # Inicializar base de datos
        self.init_database()
        logger.info(f"✅ Base de datos inicializada: {db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Obtiene una conexión thread-safe a SQLite."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self) -> None:
        """Crea las tablas si no existen"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS analysis (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME NOT NULL,
                        coins_analyzed INTEGER,
                        sentiment TEXT,
                        fear_greed_index INTEGER,
                        ai_recommendation TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS coin_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        analysis_id INTEGER,
                        symbol TEXT NOT NULL,
                        price REAL NOT NULL,
                        change_24h REAL,
                        change_2h REAL,
                        volume REAL,
                        FOREIGN KEY (analysis_id) REFERENCES analysis(id)
                    )
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_analysis_timestamp 
                    ON analysis(timestamp)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_coin_symbol 
                    ON coin_data(symbol)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_coin_analysis 
                    ON coin_data(analysis_id)
                """)
                
                # Tabla para tracking de engagement en Twitter
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS twitter_engagement (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tweet_id TEXT UNIQUE NOT NULL,
                        action TEXT NOT NULL,
                        comment_text TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_engagement_tweet 
                    ON twitter_engagement(tweet_id)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_engagement_action 
                    ON twitter_engagement(action)
                """)
                
                conn.commit()
            finally:
                conn.close()
    
    def save_analysis(self, analysis_data: Dict[str, Any]) -> int:
        """
        Guarda un análisis completo en la base de datos (thread-safe)
        
        Args:
            analysis_data: Diccionario con datos del análisis
                - timestamp: datetime
                - coins_analyzed: int
                - sentiment: str
                - fear_greed_index: int
                - ai_recommendation: str
                - coins: List[Dict] (datos de monedas)
        
        Returns:
            ID del análisis guardado
        """
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT INTO analysis 
                    (timestamp, coins_analyzed, sentiment, fear_greed_index, ai_recommendation)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    analysis_data['timestamp'],
                    analysis_data['coins_analyzed'],
                    analysis_data['sentiment'],
                    analysis_data['fear_greed_index'],
                    analysis_data['ai_recommendation']
                ))
                
                analysis_id = cursor.lastrowid
                
                if 'coins' in analysis_data:
                    for coin in analysis_data['coins']:
                        cursor.execute("""
                            INSERT INTO coin_data 
                            (analysis_id, symbol, price, change_24h, change_2h, volume)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            analysis_id,
                            coin.get('symbol', ''),
                            coin.get('price', 0.0),
                            coin.get('change_24h', 0.0),
                            coin.get('change_2h', 0.0),
                            coin.get('volume', 0.0)
                        ))
                
                conn.commit()
                logger.info(f"✅ Análisis guardado con ID: {analysis_id}")
                return analysis_id
                
            except Exception as e:
                logger.error(f"❌ Error guardando análisis: {e}")
                conn.rollback()
                return -1
            finally:
                conn.close()
    
    def get_latest_analysis(self) -> Optional[Dict[str, Any]]:
        """
        Obtiene el último análisis realizado (thread-safe)
        
        Returns:
            Diccionario con datos del análisis o None
        """
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    SELECT * FROM analysis 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """)
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                analysis = dict(row)
                
                cursor.execute("""
                    SELECT * FROM coin_data 
                    WHERE analysis_id = ?
                """, (analysis['id'],))
                
                coins = [dict(coin) for coin in cursor.fetchall()]
                analysis['coins'] = coins
                
                return analysis
                
            except Exception as e:
                logger.error(f"❌ Error obteniendo último análisis: {e}")
                return None
            finally:
                conn.close()
    
    def get_historical_data(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Obtiene datos históricos de análisis (thread-safe)
        
        Args:
            days: Número de días hacia atrás
        
        Returns:
            Lista de análisis
        """
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                cutoff_date = datetime.now() - timedelta(days=days)
                
                cursor.execute("""
                    SELECT * FROM analysis 
                    WHERE timestamp >= ?
                    ORDER BY timestamp ASC
                """, (cutoff_date,))
                
                analyses = [dict(row) for row in cursor.fetchall()]
                
                return analyses
                
            except Exception as e:
                logger.error(f"❌ Error obteniendo datos históricos: {e}")
                return []
            finally:
                conn.close()
    
    def get_coin_history(self, symbol: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        Obtiene el histórico de una moneda específica (thread-safe)
        
        Args:
            symbol: Símbolo de la moneda (ej: 'BTCUSDT')
            days: Número de días hacia atrás
        
        Returns:
            Lista de datos de la moneda
        """
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                cutoff_date = datetime.now() - timedelta(days=days)
                
                cursor.execute("""
                    SELECT cd.*, a.timestamp 
                    FROM coin_data cd
                    JOIN analysis a ON cd.analysis_id = a.id
                    WHERE cd.symbol = ? AND a.timestamp >= ?
                    ORDER BY a.timestamp ASC
                """, (symbol, cutoff_date))
                
                history = [dict(row) for row in cursor.fetchall()]
                
                return history
                
            except Exception as e:
                logger.error(f"❌ Error obteniendo histórico de {symbol}: {e}")
                return []
            finally:
                conn.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas generales de la base de datos (thread-safe)
        
        Returns:
            Diccionario con estadísticas
        """
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                # Total de análisis
                cursor.execute("SELECT COUNT(*) FROM analysis")
                total_analyses = cursor.fetchone()[0]
                
                # Total de monedas analizadas
                cursor.execute("SELECT COUNT(DISTINCT symbol) FROM coin_data")
                total_coins = cursor.fetchone()[0]
                
                # Primer y último análisis
                cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM analysis")
                first, last = cursor.fetchone()
                
                return {
                    'total_analyses': total_analyses,
                    'total_unique_coins': total_coins,
                    'first_analysis': first,
                    'last_analysis': last
                }
                
            except Exception as e:
                logger.error(f"❌ Error obteniendo estadísticas: {e}")
                return {}
            finally:
                conn.close()
    
    def clear_database(self) -> bool:
        """
        Limpia toda la base de datos (thread-safe, CUIDADO!)
        
        Returns:
            True si se limpió correctamente
        """
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute("DELETE FROM coin_data")
                cursor.execute("DELETE FROM analysis")
                conn.commit()
                
                logger.info("✅ Base de datos limpiada exitosamente")
                return True
                
            except Exception as e:
                logger.error(f"❌ Error limpiando base de datos: {e}")
                conn.rollback()
                return False
            finally:
                conn.close()
    
    def execute_query(self, query: str, params: tuple = ()) -> Optional[List]:
        """
        Ejecuta una query SQL personalizada (thread-safe)
        
        Args:
            query: Query SQL a ejecutar
            params: Parámetros para la query
            
        Returns:
            Resultados de la query o None
        """
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute(query, params)
                
                # Si es INSERT/UPDATE/DELETE, hacer commit
                if query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
                    conn.commit()
                    return None
                
                # Si es SELECT, retornar resultados
                results = cursor.fetchall()
                return results
                
            except Exception as e:
                logger.error(f"❌ Error ejecutando query: {e}")
                conn.rollback()
                return None
            finally:
                conn.close()

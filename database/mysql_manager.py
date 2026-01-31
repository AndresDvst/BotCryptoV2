"""
Gestor de base de datos MySQL para el bot de criptomonedas
"""
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pymysql
from utils.logger import logger
from config.config import Config


class MySQLManager:
    """Gestor de base de datos MySQL para almacenar análisis históricos"""
    
    def __init__(
        self,
        host: str = getattr(Config, 'MYSQL_HOST', 'localhost'),
        user: str = getattr(Config, 'MYSQL_USER', 'root'),
        password: str = getattr(Config, 'MYSQL_PASSWORD', '1234'),
        database: str = getattr(Config, 'MYSQL_DATABASE', 'crypto_bot'),
        port: int = getattr(Config, 'MYSQL_PORT', 3306)
    ):
        """
        Inicializa el gestor de base de datos MySQL
        
        Args:
            host: Host del servidor MySQL
            user: Usuario de MySQL
            password: Contraseña de MySQL
            database: Nombre de la base de datos
            port: Puerto de MySQL
        """
        self.host = host or getattr(Config, 'MYSQL_HOST', 'localhost')
        self.user = user or getattr(Config, 'MYSQL_USER', 'root')
        self.password = password or getattr(Config, 'MYSQL_PASSWORD', '1234')
        self.database = database or getattr(Config, 'MYSQL_DATABASE', 'crypto_bot')
        self.port = port or getattr(Config, 'MYSQL_PORT', 3306)
        
        # Crear base de datos y tablas si no existen
        self.init_database()
        logger.info(f"✅ Base de datos MySQL inicializada: {database}")
    
    def get_connection(self, use_db: bool = True) -> pymysql.connections.Connection:
        """Obtiene una conexión a MySQL"""
        try:
            if use_db:
                return pymysql.connect(
                    host=self.host,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                    port=self.port,
                    charset='utf8mb4',
                    cursorclass=pymysql.cursors.DictCursor
                )
            else:
                return pymysql.connect(
                    host=self.host,
                    user=self.user,
                    password=self.password,
                    port=self.port,
                    charset='utf8mb4'
                )
        except Exception as e:
            logger.error(f"❌ Error conectando a MySQL: {e}")
            raise
    
    def init_database(self) -> None:
        """Crea la base de datos y tablas si no existen"""
        try:
            # Crear base de datos si no existe
            conn = self.get_connection(use_db=False)
            cursor = conn.cursor()
            
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            logger.info(f"✅ Base de datos '{self.database}' verificada/creada")
            
            cursor.close()
            conn.close()
            
            # Crear tablas
            conn = self.get_connection(use_db=True)
            cursor = conn.cursor()
            
            # Tabla de análisis
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    timestamp DATETIME NOT NULL,
                    coins_analyzed INT,
                    sentiment VARCHAR(100),
                    fear_greed_index INT,
                    ai_recommendation TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_timestamp (timestamp)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            
            # Tabla de datos de monedas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS coin_data (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    analysis_id INT,
                    symbol VARCHAR(50) NOT NULL,
                    price DECIMAL(20, 8) NOT NULL,
                    change_24h DECIMAL(10, 2),
                    change_2h DECIMAL(10, 2),
                    volume DECIMAL(20, 2),
                    FOREIGN KEY (analysis_id) REFERENCES analysis(id) ON DELETE CASCADE,
                    INDEX idx_symbol (symbol),
                    INDEX idx_analysis_id (analysis_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            
            conn.commit()
            logger.info("✅ Tablas verificadas/creadas")
            
            # Ejecutar script V3 para nuevas tablas
            self._execute_v3_schema(cursor)
            conn.commit()
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Error inicializando base de datos: {e}")
            raise
    
    def _execute_v3_schema(self, cursor: pymysql.cursors.Cursor) -> None:
        """Ejecuta el script SQL de V3 para crear nuevas tablas de forma idempotente"""
        try:
            schema_path = os.path.join(os.path.dirname(__file__), 'v3_schema.sql')
            
            if not os.path.exists(schema_path):
                logger.warning("⚠️ Archivo v3_schema.sql no encontrado, saltando...")
                return
            
            logger.info("📦 Ejecutando schema V3...")
            
            with open(schema_path, 'r', encoding='utf-8') as f:
                sql_script = f.read()
            
            # Ejecutar cada statement separadamente
            statements = [s.strip() for s in sql_script.split(';') if s.strip()]
            for statement in statements:
                if statement.startswith('--'):
                    continue
                try:
                    cursor.execute(statement)
                except Exception as e:
                    msg = str(e).lower()
                    if 'already exists' in msg or 'duplicate' in msg:
                        logger.info("ℹ️ Statement ya aplicado, continuando")
                        continue
                    logger.warning(f"⚠️ Error en statement SQL: {e}")
            
            logger.info("✅ Schema V3 ejecutado correctamente")
            
        except Exception as e:
            logger.warning(f"⚠️ Error ejecutando schema V3: {e}")
            try:
                cursor.connection.rollback()
            except Exception:
                pass
    
    def save_analysis(self, analysis_data: Dict[str, Any]) -> int:
        """
        Guarda un análisis completo en la base de datos
        
        Args:
            analysis_data: Diccionario con datos del análisis
        
        Returns:
            ID del análisis guardado
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Guardar análisis principal
            cursor.execute("""
                INSERT INTO analysis 
                (timestamp, coins_analyzed, sentiment, fear_greed_index, ai_recommendation)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                analysis_data['timestamp'],
                analysis_data['coins_analyzed'],
                analysis_data['sentiment'],
                analysis_data['fear_greed_index'],
                analysis_data['ai_recommendation']
            ))
            
            analysis_id = cursor.lastrowid
            
            # Guardar datos de monedas
            if 'coins' in analysis_data and analysis_data['coins']:
                for coin in analysis_data['coins']:
                    cursor.execute("""
                        INSERT INTO coin_data 
                        (analysis_id, symbol, price, change_24h, change_2h, volume)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        analysis_id,
                        coin.get('symbol', ''),
                        coin.get('price', 0.0),
                        coin.get('change_24h', 0.0),
                        coin.get('change_2h', 0.0),
                        coin.get('volume', 0.0)
                    ))
            
            conn.commit()
            logger.info(f"✅ Análisis guardado en MySQL con ID: {analysis_id}")
            return analysis_id
            
        except Exception as e:
            logger.error(f"❌ Error guardando análisis: {e}")
            conn.rollback()
            return -1
        finally:
            cursor.close()
            conn.close()
    
    def get_latest_analysis(self) -> Optional[Dict[str, Any]]:
        """Obtiene el último análisis realizado"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM analysis 
                ORDER BY timestamp DESC 
                LIMIT 1
            """)
            
            analysis = cursor.fetchone()
            if not analysis:
                return None
            
            # Obtener monedas del análisis
            cursor.execute("""
                SELECT * FROM coin_data 
                WHERE analysis_id = %s
            """, (analysis['id'],))
            
            coins = cursor.fetchall()
            analysis['coins'] = coins
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo último análisis: {e}")
            return None
        finally:
            cursor.close()
            conn.close()
    
    def get_historical_data(self, days: int = 30) -> List[Dict[str, Any]]:
        """Obtiene datos históricos de análisis"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            cursor.execute("""
                SELECT * FROM analysis 
                WHERE timestamp >= %s
                ORDER BY timestamp ASC
            """, (cutoff_date,))
            
            analyses = cursor.fetchall()
            return analyses
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo datos históricos: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    def get_coin_history(self, symbol: str, days: int = 30) -> List[Dict[str, Any]]:
        """Obtiene el histórico de una moneda específica"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            cursor.execute("""
                SELECT cd.*, a.timestamp 
                FROM coin_data cd
                JOIN analysis a ON cd.analysis_id = a.id
                WHERE cd.symbol = %s AND a.timestamp >= %s
                ORDER BY a.timestamp ASC
            """, (symbol, cutoff_date))
            
            history = cursor.fetchall()
            return history
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo histórico de {symbol}: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas generales de la base de datos"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Total de análisis
            cursor.execute("SELECT COUNT(*) as total FROM analysis")
            total_analyses = cursor.fetchone()['total']
            
            # Total de monedas únicas
            cursor.execute("SELECT COUNT(DISTINCT symbol) as total FROM coin_data")
            total_coins = cursor.fetchone()['total']
            
            # Primer y último análisis
            cursor.execute("SELECT MIN(timestamp) as first, MAX(timestamp) as last FROM analysis")
            result = cursor.fetchone()
            
            return {
                'total_analyses': total_analyses,
                'total_unique_coins': total_coins,
                'first_analysis': result['first'],
                'last_analysis': result['last']
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas: {e}")
            return {}
        finally:
            cursor.close()
            conn.close()
    
    def clear_database(self) -> bool:
        """Limpia toda la base de datos (CUIDADO!)"""
        conn = self.get_connection()
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
            cursor.close()
            conn.close()

"""
Módulo de seguridad centralizado.
Proporciona funciones para sanitización, validación y manejo seguro de datos sensibles.
"""
import os
import re
import hashlib
import secrets
from typing import Any, Dict, List, Optional, Set
import pandas as pd
from functools import lru_cache


class SecurityConfig:
    """Configuración de seguridad centralizada."""
    
    # Patrones para detectar información sensible
    SENSITIVE_PATTERNS = [
        r'[a-zA-Z0-9]{32,}',  # Tokens largos
        r'\d{10,}:[A-Za-z0-9_-]{35}',  # Tokens de Telegram
        r'sk-[a-zA-Z0-9]{32,}',  # OpenAI API keys
        r'AIza[a-zA-Z0-9_-]{35}',  # Google API keys
    ]
    
    # Palabras clave que indican datos sensibles
    SENSITIVE_KEYWORDS = [
        'password', 'secret', 'token', 'api_key', 'apikey',
        'access_token', 'private', 'credential', 'auth'
    ]
    
    # Símbolos válidos para criptomonedas/mercados
    VALID_SYMBOL_PATTERN = r'^[A-Z0-9]{2,10}$'
    
    # Límites de validación
    MAX_SYMBOL_LENGTH = 20
    MAX_INPUT_LENGTH = 1000
    MAX_DATABASE_NAME_LENGTH = 64


class SecretRedactor:
    """Redactor de secretos para logs y mensajes de error."""
    
    def __init__(self):
        self._secrets: Set[str] = set()
        self._compiled_patterns = [
            re.compile(p) for p in SecurityConfig.SENSITIVE_PATTERNS
        ]
    
    def register_secret(self, secret: Optional[str]) -> None:
        """Registra un secreto para ser redactado."""
        if secret and len(secret) >= 8:
            self._secrets.add(secret)
    
    def register_secrets_from_config(self, config_class: Any) -> None:
        """Registra secretos desde una clase de configuración."""
        sensitive_attrs = [
            'BINANCE_API_KEY', 'BINANCE_API_SECRET',
            'TELEGRAM_BOT_TOKEN', 'TELEGRAM_BOT_CRYPTO',
            'TELEGRAM_BOT_MARKETS', 'TELEGRAM_BOT_SIGNALS',
            'TWITTER_API_KEY', 'TWITTER_API_SECRET',
            'TWITTER_ACCESS_TOKEN', 'TWITTER_ACCESS_SECRET',
            'TWITTER_PASSWORD', 'TWITTER_USERNAME',
            'GOOGLE_GEMINI_API_KEY', 'OPENAI_API_KEY',
            'OPENROUTER_API_KEY', 'MYSQL_PASSWORD',
            'DB_PASSWORD', 'TWELVEDATA_API_KEY'
        ]
        
        for attr in sensitive_attrs:
            value = getattr(config_class, attr, None)
            if value:
                self.register_secret(value)
    
    def redact(self, text: str) -> str:
        """Redacta todos los secretos registrados de un texto."""
        if not text:
            return text
        
        result = text
        
        # Redactar secretos registrados explícitamente
        for secret in self._secrets:
            if secret in result:
                # Mostrar primeros y últimos 2 caracteres para depuración
                if len(secret) > 8:
                    masked = f"{secret[:2]}***{secret[-2:]}"
                else:
                    masked = "[REDACTED]"
                result = result.replace(secret, masked)
        
        # Redactar patrones conocidos
        for pattern in self._compiled_patterns:
            result = pattern.sub('[SENSITIVE_DATA_REDACTED]', result)
        
        return result
    
    def redact_exception(self, exc: Exception) -> str:
        """Redacta información sensible de una excepción."""
        return self.redact(str(exc))


# Instancia global del redactor
_redactor = SecretRedactor()


def get_redactor() -> SecretRedactor:
    """Obtiene la instancia global del redactor."""
    return _redactor


def sanitize_log_message(message: str) -> str:
    """Sanitiza un mensaje de log removiendo información sensible."""
    return _redactor.redact(message)


def sanitize_exception(exc: Exception) -> str:
    """Sanitiza una excepción para logging seguro."""
    return _redactor.redact_exception(exc)


class InputValidator:
    """Validador de entradas del usuario."""
    
    @staticmethod
    def validate_symbol(symbol: str) -> tuple[bool, Optional[str]]:
        """
        Valida un símbolo de criptomoneda/mercado.
        
        Returns:
            Tuple (es_válido, mensaje_error)
        """
        if not symbol:
            return False, "El símbolo no puede estar vacío"
        
        if len(symbol) > SecurityConfig.MAX_SYMBOL_LENGTH:
            return False, f"El símbolo excede {SecurityConfig.MAX_SYMBOL_LENGTH} caracteres"
        
        # Normalizar a mayúsculas
        symbol_upper = symbol.upper().strip()
        
        # Validar solo caracteres alfanuméricos
        if not re.match(SecurityConfig.VALID_SYMBOL_PATTERN, symbol_upper):
            return False, "El símbolo contiene caracteres no permitidos"
        
        return True, None
    
    @staticmethod
    def validate_database_name(name: str) -> tuple[bool, Optional[str]]:
        """
        Valida un nombre de base de datos para prevenir SQL injection.
        
        Returns:
            Tuple (es_válido, mensaje_error)
        """
        if not name:
            return False, "El nombre de base de datos no puede estar vacío"
        
        if len(name) > SecurityConfig.MAX_DATABASE_NAME_LENGTH:
            return False, f"El nombre excede {SecurityConfig.MAX_DATABASE_NAME_LENGTH} caracteres"
        
        # Solo permitir caracteres seguros para nombres de DB
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', name):
            return False, "El nombre de base de datos contiene caracteres no permitidos"
        
        return True, None
    
    @staticmethod
    def validate_days(days: int) -> tuple[bool, Optional[str]]:
        """
        Valida el parámetro days para consultas históricas.
        
        Returns:
            Tuple (es_válido, mensaje_error)
        """
        if not isinstance(days, int):
            return False, "El parámetro 'days' debe ser un entero"
        
        if days < 1 or days > 365:
            return False, "El parámetro 'days' debe estar entre 1 y 365"
        
        return True, None
    
    @staticmethod
    def sanitize_string(text: str, max_length: int = 1000) -> str:
        """Sanitiza una cadena de texto removiendo caracteres peligrosos."""
        if not text:
            return ""
        
        # Truncar si es muy largo
        if len(text) > max_length:
            text = text[:max_length]
        
        # Remover caracteres de control excepto newlines y tabs
        sanitized = ''.join(
            char for char in text 
            if char.isprintable() or char in '\n\r\t'
        )
        
        return sanitized


class PasswordValidator:
    """Validador de fortaleza de contraseñas."""
    
    # Contraseñas débiles conocidas que NO deben usarse
    WEAK_PASSWORDS = {
        '1234', '12345', '123456', 'password', 'admin',
        'root', 'test', 'demo', 'default', 'changeme',
        'qwerty', 'letmein', 'welcome', 'monkey', 'dragon'
    }
    
    @staticmethod
    def is_weak_password(password: str) -> bool:
        """Verifica si una contraseña es débil o común."""
        if not password:
            return True
        
        # Verificar longitud mínima
        if len(password) < 8:
            return True
        
        # Verificar contra lista de contraseñas débiles
        if password.lower() in PasswordValidator.WEAK_PASSWORDS:
            return True
        
        # Verificar que no sea solo números simples
        if password.isdigit() and len(set(password)) < 4:
            return True
        
        return False
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Genera un token seguro aleatorio."""
        return secrets.token_urlsafe(length)


def hash_for_dedup(content: str) -> str:
    """
    Genera un hash seguro para deduplicación.
    Usa SHA-256 en lugar de MD5.
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def validate_dataframe(df: Any) -> None:
    """
    Valida un DataFrame para cálculos de indicadores técnicos.
    """
    if df is None:
        raise ValueError("DataFrame vacío")
    if not isinstance(df, pd.DataFrame):
        raise ValueError("DataFrame inválido")
    if df.empty:
        raise ValueError("DataFrame vacío")

    required_columns = {"open", "high", "low", "close", "volume"}
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"DataFrame sin columnas requeridas: {', '.join(sorted(missing_columns))}")

    if df[list(required_columns)].isnull().any().any():
        raise ValueError("DataFrame contiene valores nulos en columnas requeridas")


def safe_path_join(base_path: str, *paths: str) -> Optional[str]:
    """
    Une paths de forma segura, previniendo path traversal.
    
    Returns:
        Path unido o None si hay intento de traversal.
    """
    base = os.path.abspath(base_path)
    result = os.path.abspath(os.path.join(base, *paths))
    
    # Verificar que el resultado está dentro del base
    if not result.startswith(base):
        return None
    
    return result


class RateLimiter:
    """Rate limiter simple basado en tiempo."""
    
    def __init__(self, max_calls: int, time_window_seconds: float):
        self.max_calls = max_calls
        self.time_window = time_window_seconds
        self._calls: List[float] = []
    
    def can_proceed(self) -> bool:
        """Verifica si se puede proceder con una nueva llamada."""
        import time
        now = time.time()
        
        # Limpiar llamadas antiguas
        self._calls = [t for t in self._calls if now - t < self.time_window]
        
        if len(self._calls) >= self.max_calls:
            return False
        
        self._calls.append(now)
        return True
    
    def time_until_available(self) -> float:
        """Retorna segundos hasta que se pueda hacer otra llamada."""
        import time
        if len(self._calls) < self.max_calls:
            return 0.0
        
        now = time.time()
        oldest = min(self._calls)
        return max(0.0, self.time_window - (now - oldest))

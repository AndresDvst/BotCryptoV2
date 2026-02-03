"""
Tests para el módulo de configuración
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from config.config import Config


class TestConfig:
    """Tests para la clase Config"""
    
    def test_config_loads_env_vars(self, mock_env_vars):
        """Test que Config carga las variables de entorno correctamente"""
        # Recargar el módulo para que tome las nuevas variables
        from importlib import reload
        import config.config
        reload(config.config)
        from config.config import Config
        
        assert Config.BINANCE_API_KEY == 'test_binance_key'
        assert Config.TELEGRAM_BOT_TOKEN == 'test_telegram_token'
        assert Config.GOOGLE_GEMINI_API_KEY == 'test_gemini_key'
    
    @patch('os.path.exists')
    def test_config_validation_success(self, mock_exists, mock_env_vars):
        """Test que la validación pasa con todas las variables configuradas"""
        # Mockear os.path.exists para que devuelva True para todo (imágenes, driver, etc.)
        mock_exists.return_value = True

        from importlib import reload
        import config.config
        reload(config.config)
        from config.config import Config
        
        # No debería lanzar excepción
        assert Config.validate() == True
    
    def test_config_validation_fails_missing_binance_key(self, monkeypatch):
        """Test que la validación falla cuando falta BINANCE_API_KEY"""
        # Configurar todas las variables excepto BINANCE_API_KEY
        monkeypatch.setenv('BINANCE_API_KEY', '')
        monkeypatch.setenv('BINANCE_API_SECRET', 'test')
        monkeypatch.setenv('TELEGRAM_BOT_TOKEN', 'test')
        monkeypatch.setenv('TELEGRAM_CHAT_ID', 'test')
        monkeypatch.setenv('TWITTER_API_KEY', 'test')
        monkeypatch.setenv('TWITTER_API_SECRET', 'test')
        monkeypatch.setenv('TWITTER_ACCESS_TOKEN', 'test')
        monkeypatch.setenv('TWITTER_ACCESS_SECRET', 'test')
        monkeypatch.setenv('GOOGLE_GEMINI_API_KEY', 'test')
        
        from importlib import reload
        import config.config
        reload(config.config)
        from config.config import Config
        
        with pytest.raises(ValueError, match="Faltan las siguientes variables"):
            Config.validate()
    
    def test_config_has_default_values(self, mock_env_vars):
        """Test que Config tiene valores por defecto"""
        from importlib import reload
        import config.config
        reload(config.config)
        from config.config import Config
        
        assert Config.REPORT_INTERVAL_HOURS == 2
        assert Config.MORNING_POST_TIME == "06:00"
        assert Config.MIN_CHANGE_PERCENT == 10

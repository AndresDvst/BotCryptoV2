"""
Fixtures compartidas para tests
"""
import pytest
from unittest.mock import Mock, MagicMock
import os

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock de variables de entorno para tests"""
    env_vars = {
        'BINANCE_API_KEY': 'test_binance_key',
        'BINANCE_API_SECRET': 'test_binance_secret',
        'BYBIT_API_KEY': 'test_bybit_key',
        'BYBIT_API_SECRET': 'test_bybit_secret',
        'TELEGRAM_BOT_TOKEN': 'test_telegram_token',
        'TELEGRAM_CHAT_ID': 'test_chat_id',
        'TWITTER_API_KEY': 'test_twitter_key',
        'TWITTER_API_SECRET': 'test_twitter_secret',
        'TWITTER_ACCESS_TOKEN': 'test_access_token',
        'TWITTER_ACCESS_SECRET': 'test_access_secret',
        'GOOGLE_GEMINI_API_KEY': 'test_gemini_key',
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    
    return env_vars


@pytest.fixture
def mock_binance_client():
    """Mock del cliente de Binance"""
    client = Mock()
    
    # Mock de get_ticker
    client.get_ticker.return_value = [
        {
            'symbol': 'BTCUSDT',
            'lastPrice': '50000.00',
            'priceChangePercent': '5.2',
            'volume': '1000000'
        },
        {
            'symbol': 'ETHUSDT',
            'lastPrice': '3000.00',
            'priceChangePercent': '3.1',
            'volume': '500000'
        },
        {
            'symbol': 'SOLUSDT',
            'lastPrice': '100.00',
            'priceChangePercent': '15.5',
            'volume': '200000'
        }
    ]
    
    # Mock de get_klines
    client.get_klines.return_value = [
        [1640000000000, '49000', '50500', '48500', '50000', '1000'],
        [1640003600000, '50000', '51000', '49500', '50500', '1100']
    ]
    
    return client


@pytest.fixture
def sample_coin_data():
    """Datos de ejemplo de criptomonedas"""
    return [
        {
            'symbol': 'BTCUSDT',
            'price': 50000.0,
            'change_24h': 5.2,
            'change_2h': 1.5,
            'volume': 1000000
        },
        {
            'symbol': 'ETHUSDT',
            'price': 3000.0,
            'change_24h': 3.1,
            'change_2h': 0.8,
            'volume': 500000
        },
        {
            'symbol': 'SOLUSDT',
            'price': 100.0,
            'change_24h': 15.5,
            'change_2h': 3.2,
            'volume': 200000
        }
    ]


@pytest.fixture
def mock_logger():
    """Mock del logger"""
    logger = Mock()
    logger.info = Mock()
    logger.error = Mock()
    logger.warning = Mock()
    logger.debug = Mock()
    return logger

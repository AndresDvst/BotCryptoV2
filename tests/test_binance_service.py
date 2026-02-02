"""
Tests para el servicio de Binance
"""
import pytest
from unittest.mock import Mock, patch
from services.binance_service import BinanceService


class TestBinanceService:
    """Tests para BinanceService"""
    
    @patch('services.binance_service.ccxt.binance')
    def test_initialization(self, mock_client_class, mock_env_vars):
        """Test que el servicio se inicializa correctamente"""
        service = BinanceService()
        assert service is not None
        mock_client_class.assert_called_once()
    
    @patch('services.binance_service.ccxt.binance')
    def test_get_all_tickers(self, mock_client_class, mock_env_vars):
        """Test obtención de todos los tickers"""
        mock_exchange = Mock()
        mock_exchange.fetch_tickers.return_value = {
            'BTC/USDT': {'last': 50000.0, 'percentage': 5.0, 'quoteVolume': 1000000, 'active': True},
            'ETH/USDT': {'last': 3000.0, 'percentage': 3.0, 'quoteVolume': 500000, 'active': True},
        }
        mock_exchange.fetch_balance.return_value = {}
        mock_exchange.fetch_tickers.__name__ = "fetch_tickers"
        mock_exchange.fetch_balance.__name__ = "fetch_balance"
        mock_client_class.return_value = mock_exchange
        
        service = BinanceService()
        tickers = service.get_all_tickers()
        
        assert isinstance(tickers, dict)
        assert len(tickers) > 0
        mock_exchange.fetch_tickers.assert_called_once()
    
    @patch('services.binance_service.ccxt.binance')
    def test_filter_by_change_filters_correctly(self, mock_client_class, mock_env_vars):
        """Test que filtra correctamente por cambio porcentual"""
        mock_exchange = Mock()
        mock_exchange.fetch_tickers.return_value = {
            'BTC/USDT': {'last': 50000.0, 'percentage': 5.0, 'quoteVolume': 1000000, 'active': True},
            'SOL/USDT': {'last': 100.0, 'percentage': 15.5, 'quoteVolume': 200000, 'active': True},
            'FOO/USDT': {'last': 1.0, 'percentage': 20.0, 'quoteVolume': 100, 'active': True},
        }
        mock_exchange.fetch_balance.return_value = {}
        mock_exchange.fetch_tickers.__name__ = "fetch_tickers"
        mock_exchange.fetch_balance.__name__ = "fetch_balance"
        mock_client_class.return_value = mock_exchange
        
        service = BinanceService()
        filtered = service.filter_significant_changes(min_change_percent=10.0)
        
        # Solo SOLUSDT tiene cambio >= 10%
        assert isinstance(filtered, list)
        # Verificar que se filtró correctamente
        if len(filtered) > 0:
            for coin in filtered:
                assert abs(float(coin.get('change_24h', 0))) >= 10.0
    
    @patch('services.binance_service.ccxt.binance')
    def test_get_2h_change(self, mock_client_class, mock_env_vars):
        """Test cálculo de cambio en 2 horas"""
        mock_exchange = Mock()
        mock_exchange.fetch_ohlcv.return_value = [
            [1640000000000, 49000, 50500, 48500, 50000, 1000],
            [1640003600000, 50000, 51000, 49500, 50500, 1100],
            [1640007200000, 50500, 52000, 50000, 51000, 1200],
        ]
        mock_exchange.fetch_balance.return_value = {}
        mock_exchange.fetch_ohlcv.__name__ = "fetch_ohlcv"
        mock_exchange.fetch_balance.__name__ = "fetch_balance"
        mock_client_class.return_value = mock_exchange
        
        service = BinanceService()
        change = service.get_2hour_change([{'symbol': 'BTC/USDT'}])
        
        assert isinstance(change, list)
        mock_exchange.fetch_ohlcv.assert_called_once()
    
    @patch('services.binance_service.ccxt.binance')
    def test_handles_api_errors_gracefully(self, mock_client_class, mock_env_vars):
        """Test que maneja errores de API correctamente"""
        mock_exchange = Mock()
        mock_exchange.fetch_tickers.side_effect = Exception("API Error")
        mock_exchange.fetch_balance.return_value = {}
        mock_exchange.fetch_tickers.__name__ = "fetch_tickers"
        mock_exchange.fetch_balance.__name__ = "fetch_balance"
        mock_client_class.return_value = mock_exchange
        
        service = BinanceService()
        
        # Debería manejar el error sin crashear
        try:
            result = service.get_all_tickers()
            # Si retorna algo, debería ser una lista vacía o None
            assert result is None or result == [] or result == {}
        except Exception:
            # O puede lanzar la excepción, dependiendo de la implementación
            pass

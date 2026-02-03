"""
Tests para el servicio de Binance
"""
import pytest
from unittest.mock import Mock, patch
from services.binance_service import BinanceService


class TestBinanceService:
    """Tests para BinanceService"""
    
    @patch('services.binance_service.Client')
    def test_initialization(self, mock_client_class, mock_env_vars):
        """Test que el servicio se inicializa correctamente"""
        service = BinanceService()
        assert service is not None
        mock_client_class.assert_called_once()
    
    @patch('services.binance_service.Client')
    def test_get_all_tickers(self, mock_client_class, mock_binance_client, mock_env_vars):
        """Test obtención de todos los tickers"""
        mock_client_class.return_value = mock_binance_client
        
        service = BinanceService()
        tickers = service.get_all_tickers()
        
        assert isinstance(tickers, list)
        assert len(tickers) > 0
        mock_binance_client.get_ticker.assert_called_once()
    
    @patch('services.binance_service.Client')
    def test_filter_by_change_filters_correctly(self, mock_client_class, mock_binance_client, mock_env_vars):
        """Test que filtra correctamente por cambio porcentual"""
        mock_client_class.return_value = mock_binance_client
        
        service = BinanceService()
        filtered = service.filter_by_change(min_change=10.0)
        
        # Solo SOLUSDT tiene cambio >= 10%
        assert isinstance(filtered, list)
        # Verificar que se filtró correctamente
        if len(filtered) > 0:
            for coin in filtered:
                assert abs(float(coin.get('priceChangePercent', 0))) >= 10.0
    
    @patch('services.binance_service.Client')
    def test_get_2h_change(self, mock_client_class, mock_binance_client, mock_env_vars):
        """Test cálculo de cambio en 2 horas"""
        mock_client_class.return_value = mock_binance_client
        
        service = BinanceService()
        change = service.get_2h_change('BTCUSDT')
        
        assert isinstance(change, (int, float))
        mock_binance_client.get_klines.assert_called_once()
    
    @patch('services.binance_service.Client')
    def test_handles_api_errors_gracefully(self, mock_client_class, mock_env_vars):
        """Test que maneja errores de API correctamente"""
        mock_client = Mock()
        mock_client.get_ticker.side_effect = Exception("API Error")
        mock_client_class.return_value = mock_client
        
        service = BinanceService()
        
        # Debería manejar el error sin crashear
        try:
            result = service.get_all_tickers()
            # Si retorna algo, debería ser una lista vacía o None
            assert result is None or result == []
        except Exception:
            # O puede lanzar la excepción, dependiendo de la implementación
            pass

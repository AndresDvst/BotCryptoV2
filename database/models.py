"""
Modelos de datos para la base de datos
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Analysis:
    """Modelo para un análisis completo"""
    id: Optional[int]
    timestamp: datetime
    coins_analyzed: int
    sentiment: str
    fear_greed_index: int
    ai_recommendation: str
    created_at: Optional[datetime] = None


@dataclass
class CoinData:
    """Modelo para datos de una criptomoneda"""
    id: Optional[int]
    analysis_id: int
    symbol: str
    price: float
    change_24h: float
    change_2h: float
    volume: float

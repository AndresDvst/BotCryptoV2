"""
Modelos de datos para la base de datos
"""
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, Optional


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
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "Analysis":
        return cls(
            id=row.get("id"),
            timestamp=row.get("timestamp"),
            coins_analyzed=row.get("coins_analyzed", 0),
            sentiment=row.get("sentiment", ""),
            fear_greed_index=row.get("fear_greed_index", 0),
            ai_recommendation=row.get("ai_recommendation", ""),
            created_at=row.get("created_at"),
        )


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
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "CoinData":
        return cls(
            id=row.get("id"),
            analysis_id=row.get("analysis_id", 0),
            symbol=row.get("symbol", ""),
            price=float(row.get("price", 0.0)),
            change_24h=float(row.get("change_24h", 0.0)),
            change_2h=float(row.get("change_2h", 0.0)),
            volume=float(row.get("volume", 0.0)),
        )

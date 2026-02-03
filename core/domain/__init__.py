from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Candle:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: Optional[str] = None


@dataclass
class MarketSeries:
    symbol: str
    candles: List[Candle]
    timeframe: Optional[str] = None

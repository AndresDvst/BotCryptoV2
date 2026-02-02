from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"


class DecisionType(str, Enum):
    HOLD = "HOLD"
    BUY = "BUY"
    SELL = "SELL"
    EXIT = "EXIT"


@dataclass(frozen=True)
class Candle:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class MarketSeries:
    symbol: str
    candles: List[Candle]


@dataclass
class OrderIntent:
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    reference_price: float
    stop_loss: float
    take_profit: float
    invalidation: float
    created_at: int


@dataclass
class OrderFill:
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    fee: float
    filled_at: int


@dataclass
class Position:
    symbol: str
    side: OrderSide
    entry_price: float
    quantity: float
    stop_loss: float
    take_profit: float
    opened_at: int
    closed_at: Optional[int] = None
    exit_price: Optional[float] = None
    realized_pnl: Optional[float] = None
    fees_paid: float = 0.0


@dataclass
class Trade:
    symbol: str
    side: OrderSide
    entry_price: float
    exit_price: float
    quantity: float
    entry_time: int
    exit_time: int
    pnl: float
    return_pct: float
    fees_paid: float
    exit_reason: str


@dataclass
class PortfolioState:
    cash: float
    equity: float
    peak_equity: float
    drawdown: float = 0.0
    open_positions: List[Position] = field(default_factory=list)
    realized_pnl: float = 0.0
    consecutive_losses: int = 0


@dataclass(frozen=True)
class RiskLimits:
    risk_per_trade: float
    max_drawdown: float
    max_positions: int
    max_exposure_pct: float
    max_consecutive_losses: int


@dataclass(frozen=True)
class StrategyDecision:
    action: DecisionType
    intent: Optional[OrderIntent] = None
    reason: Optional[str] = None
    metadata: Optional[Dict[str, float]] = None

from dataclasses import dataclass
from typing import Optional
import random

from core.domain import OrderIntent, OrderFill, OrderSide, Candle


@dataclass(frozen=True)
class ExecutionConfig:
    fee_rate: float = 0.001
    slippage_pct: float = 0.0005
    spread_pct: float = 0.0004
    latency_bars: int = 1
    partial_fill_probability: float = 0.0
    partial_fill_ratio: float = 0.5
    seed: Optional[int] = 7


class ExecutionModel:
    def __init__(self, config: Optional[ExecutionConfig] = None) -> None:
        self.config = config or ExecutionConfig()
        self.rng = random.Random(self.config.seed)

    def execution_index(self, current_index: int) -> int:
        return current_index + max(1, self.config.latency_bars)

    def fill_order(self, intent: OrderIntent, candle: Candle) -> Optional[OrderFill]:
        if candle.open <= 0:
            return None

        price = candle.open
        price = self._apply_spread_slippage(price, intent.side)
        qty = intent.quantity
        if qty <= 0:
            return None

        if self.config.partial_fill_probability > 0:
            if self.rng.random() < self.config.partial_fill_probability:
                qty = qty * self.config.partial_fill_ratio

        fee = abs(price * qty) * self.config.fee_rate
        return OrderFill(
            symbol=intent.symbol,
            side=intent.side,
            quantity=qty,
            price=price,
            fee=fee,
            filled_at=candle.timestamp,
        )

    def _apply_spread_slippage(self, price: float, side: OrderSide) -> float:
        spread = price * self.config.spread_pct
        slippage = price * self.config.slippage_pct
        if side == OrderSide.BUY:
            return price + (spread / 2) + slippage
        return price - (spread / 2) - slippage

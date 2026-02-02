from dataclasses import dataclass
from typing import Optional

from core.domain import PortfolioState, RiskLimits, OrderIntent


@dataclass(frozen=True)
class RiskConfig:
    risk_per_trade: float = 0.01
    max_drawdown: float = 0.2
    max_positions: int = 1
    max_exposure_pct: float = 0.5
    max_consecutive_losses: int = 4

    def to_limits(self) -> RiskLimits:
        return RiskLimits(
            risk_per_trade=self.risk_per_trade,
            max_drawdown=self.max_drawdown,
            max_positions=self.max_positions,
            max_exposure_pct=self.max_exposure_pct,
            max_consecutive_losses=self.max_consecutive_losses,
        )


class RiskManager:
    def __init__(self, config: Optional[RiskConfig] = None) -> None:
        self.config = config or RiskConfig()

    def can_open_trade(self, portfolio: PortfolioState) -> bool:
        limits = self.config.to_limits()
        if portfolio.drawdown >= limits.max_drawdown:
            return False
        if portfolio.consecutive_losses >= limits.max_consecutive_losses:
            return False
        if len(portfolio.open_positions) >= limits.max_positions:
            return False
        return True

    def size_position(self, equity: float, intent: OrderIntent) -> float:
        risk_amount = equity * self.config.risk_per_trade
        risk_per_unit = abs(intent.reference_price - intent.stop_loss)
        if risk_per_unit <= 0:
            return 0.0
        quantity = risk_amount / risk_per_unit
        if quantity < 0:
            return 0.0
        return quantity

    def exposure_ok(self, equity: float, quantity: float, price: float) -> bool:
        if equity <= 0:
            return False
        exposure = (quantity * price) / equity
        return exposure <= self.config.max_exposure_pct

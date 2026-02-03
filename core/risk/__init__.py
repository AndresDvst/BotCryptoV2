from dataclasses import dataclass


@dataclass
class RiskConfig:
    risk_per_trade: float = 0.02
    max_drawdown: float = 0.20
    max_consecutive_losses: int = 4


class RiskManager:
    def __init__(self, config: RiskConfig):
        self.config = config
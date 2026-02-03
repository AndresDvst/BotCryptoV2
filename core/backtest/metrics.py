from dataclasses import dataclass


@dataclass
class BacktestMetrics:
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0

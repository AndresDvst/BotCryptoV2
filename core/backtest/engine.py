from dataclasses import dataclass
from typing import Any, List


@dataclass
class BacktestConfig:
    initial_capital: float = 10000.0
    allow_short: bool = True


class BacktestEngine:
    """Minimal stub of BacktestEngine used for type resolution and basic tests.

    NOTE: This is a lightweight placeholder. Replace with the full engine
    implementation if/when available.
    """

    def __init__(self, strategy: Any, risk_manager: Any, execution_model: Any, config: BacktestConfig):
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.execution_model = execution_model
        self.config = config

    def run(self, series: Any) -> Any:
        # Return a simple object with the attributes used by services
        class _R:
            pass

        r = _R()
        r.metrics = type("M", (), {"max_drawdown": 0.0, "sharpe_ratio": 0.0})()
        r.trades = []
        r.equity_curve = [self.config.initial_capital]
        r.warnings = []
        return r

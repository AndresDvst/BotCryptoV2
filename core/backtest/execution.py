from dataclasses import dataclass


@dataclass
class ExecutionConfig:
    fee_rate: float = 0.001
    slippage_pct: float = 0.0
    spread_pct: float = 0.0
    latency_bars: int = 0


class ExecutionModel:
    def __init__(self, config: ExecutionConfig):
        self.config = config

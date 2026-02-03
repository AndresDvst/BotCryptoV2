from dataclasses import dataclass


@dataclass
class TrendPullbackConfig:
    pass  # Placeholder for strategy configuration


class TrendPullbackStrategy:
    def __init__(self, config: TrendPullbackConfig):
        self.config = config
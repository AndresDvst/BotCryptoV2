from abc import ABC, abstractmethod
from typing import Optional

from core.domain import MarketSeries, Position, PortfolioState, StrategyDecision


class Strategy(ABC):
    @abstractmethod
    def min_bars(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def evaluate(
        self,
        market: MarketSeries,
        position: Optional[Position],
        portfolio: PortfolioState,
    ) -> StrategyDecision:
        raise NotImplementedError

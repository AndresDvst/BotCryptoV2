from dataclasses import dataclass
from typing import Optional

from core.backtest import BacktestEngine, BacktestConfig
from core.backtest.execution import ExecutionConfig, ExecutionModel
from core.risk import RiskManager, RiskConfig
from core.strategies import TrendPullbackStrategy, TrendPullbackConfig
from core.domain import MarketSeries
from infra.market_data import load_candles_from_csv


@dataclass(frozen=True)
class BacktestRequest:
    symbol: str
    csv_path: str
    initial_capital: float
    fee_rate: float
    slippage_pct: float
    spread_pct: float
    latency_bars: int
    risk_per_trade: float
    max_drawdown: float
    max_consecutive_losses: int
    allow_short: bool


def run_backtest(request: BacktestRequest):
    candles = load_candles_from_csv(request.csv_path)
    series = MarketSeries(symbol=request.symbol, candles=candles)
    strategy = TrendPullbackStrategy(TrendPullbackConfig())
    risk_manager = RiskManager(
        RiskConfig(
            risk_per_trade=request.risk_per_trade,
            max_drawdown=request.max_drawdown,
            max_consecutive_losses=request.max_consecutive_losses,
        )
    )
    execution = ExecutionModel(
        ExecutionConfig(
            fee_rate=request.fee_rate,
            slippage_pct=request.slippage_pct,
            spread_pct=request.spread_pct,
            latency_bars=request.latency_bars,
        )
    )
    engine = BacktestEngine(
        strategy=strategy,
        risk_manager=risk_manager,
        execution_model=execution,
        config=BacktestConfig(
            initial_capital=request.initial_capital,
            allow_short=request.allow_short,
        ),
    )
    return engine.run(series)

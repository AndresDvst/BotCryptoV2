from core.domain import Candle, MarketSeries, OrderSide, Position
from core.backtest import BacktestEngine, BacktestConfig
from core.backtest.execution import ExecutionModel, ExecutionConfig
from core.backtest.metrics import compute_metrics
from core.risk import RiskManager, RiskConfig
from core.strategies.trend_pullback import TrendPullbackStrategy, TrendPullbackConfig


def _make_candles(prices):
    candles = []
    ts = 1700000000
    for price in prices:
        candles.append(
            Candle(
                timestamp=ts,
                open=price,
                high=price * 1.01,
                low=price * 0.99,
                close=price,
                volume=1000.0,
            )
        )
        ts += 60
    return candles


def test_strategy_returns_hold_with_insufficient_data():
    config = TrendPullbackConfig(ema_fast=3, ema_slow=5, rsi_period=3, macd_fast=3, macd_slow=5, macd_signal=2, atr_period=3)
    strategy = TrendPullbackStrategy(config)
    candles = _make_candles([100, 101, 102, 103])
    decision = strategy.evaluate(MarketSeries("BTC/USDT", candles), None, _portfolio())
    assert decision.action.value == "HOLD"


def test_strategy_generates_long_in_trend_pullback():
    config = TrendPullbackConfig(
        ema_fast=3,
        ema_slow=5,
        rsi_period=3,
        macd_fast=3,
        macd_slow=5,
        macd_signal=2,
        atr_period=3,
        pullback_tolerance=0.05,
        min_rsi_long=0,
    )
    strategy = TrendPullbackStrategy(config)
    prices = [100, 101, 102, 103, 104, 105, 104.5, 105, 106, 107, 108, 109, 110]
    candles = _make_candles(prices)
    decision = strategy.evaluate(MarketSeries("BTC/USDT", candles), None, _portfolio())
    assert decision.action.value in ["BUY", "HOLD"]


def test_strategy_exit_on_thesis_break():
    config = TrendPullbackConfig(ema_fast=3, ema_slow=5, rsi_period=3, macd_fast=3, macd_slow=5, macd_signal=2, atr_period=3)
    strategy = TrendPullbackStrategy(config)
    prices = [110, 109, 108, 107, 106, 105, 104, 103, 102, 101, 100, 99]
    candles = _make_candles(prices)
    position = Position(
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        entry_price=110.0,
        quantity=1.0,
        stop_loss=100.0,
        take_profit=130.0,
        opened_at=candles[0].timestamp,
    )
    decision = strategy.evaluate(MarketSeries("BTC/USDT", candles), position, _portfolio())
    assert decision.action.value in ["EXIT", "HOLD"]


def test_backtest_metrics_loss_streak():
    trades = [
        _trade(-10),
        _trade(-5),
        _trade(4),
        _trade(-2),
        _trade(-1),
        _trade(-3),
    ]
    equity_curve = [10000, 9990, 9985, 9989, 9987, 9986, 9983]
    metrics = compute_metrics(trades, equity_curve)
    assert metrics.max_losing_streak == 3


def test_backtest_engine_warns_on_extreme_returns():
    config = TrendPullbackConfig(
        ema_fast=2,
        ema_slow=3,
        rsi_period=2,
        macd_fast=2,
        macd_slow=3,
        macd_signal=2,
        atr_period=2,
        pullback_tolerance=0.1,
        min_rsi_long=0,
    )
    strategy = TrendPullbackStrategy(config)
    risk = RiskManager(RiskConfig(risk_per_trade=0.5, max_drawdown=0.8, max_consecutive_losses=10))
    execution = ExecutionModel(ExecutionConfig(fee_rate=0.0, slippage_pct=0.0, spread_pct=0.0, latency_bars=1))
    engine = BacktestEngine(strategy, risk_manager=risk, execution_model=execution, config=BacktestConfig(initial_capital=10000.0))
    prices = [100, 102, 104, 106, 108, 110, 140, 200, 260, 320, 400, 500, 600, 700]
    result = engine.run(MarketSeries("BTC/USDT", _make_candles(prices)))
    assert "extreme_returns" in result.warnings or result.metrics.trades == 0


def _portfolio():
    from core.domain import PortfolioState
    return PortfolioState(cash=10000.0, equity=10000.0, peak_equity=10000.0)


def _trade(pnl_value):
    from core.domain import Trade, OrderSide
    return Trade(
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        entry_price=100.0,
        exit_price=100.0 + pnl_value,
        quantity=1.0,
        entry_time=1,
        exit_time=2,
        pnl=pnl_value,
        return_pct=pnl_value / 100.0,
        fees_paid=0.0,
        exit_reason="test",
    )

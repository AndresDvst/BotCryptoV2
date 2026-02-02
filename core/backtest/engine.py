from dataclasses import dataclass
from typing import List, Optional, Tuple

from core.domain import (
    Candle,
    MarketSeries,
    Position,
    PortfolioState,
    OrderIntent,
    OrderSide,
    OrderType,
    StrategyDecision,
    DecisionType,
    Trade,
)
from core.risk import RiskManager, RiskConfig
from core.strategies.base import Strategy
from core.backtest.execution import ExecutionModel, ExecutionConfig
from core.backtest.metrics import compute_metrics, BacktestMetrics


@dataclass(frozen=True)
class BacktestConfig:
    initial_capital: float = 10000.0
    allow_short: bool = True
    min_bars: Optional[int] = None


@dataclass(frozen=True)
class BacktestResult:
    trades: List[Trade]
    metrics: BacktestMetrics
    equity_curve: List[float]
    warnings: List[str]


class BacktestEngine:
    def __init__(
        self,
        strategy: Strategy,
        risk_manager: Optional[RiskManager] = None,
        execution_model: Optional[ExecutionModel] = None,
        config: Optional[BacktestConfig] = None,
    ) -> None:
        self.strategy = strategy
        self.risk_manager = risk_manager or RiskManager(RiskConfig())
        self.execution_model = execution_model or ExecutionModel(ExecutionConfig())
        self.config = config or BacktestConfig()

    def run(self, series: MarketSeries) -> BacktestResult:
        if not series.candles:
            metrics = compute_metrics([], [])
            return BacktestResult(trades=[], metrics=metrics, equity_curve=[], warnings=["no_data"])

        min_bars = self.config.min_bars or self.strategy.min_bars()
        portfolio = PortfolioState(
            cash=self.config.initial_capital,
            equity=self.config.initial_capital,
            peak_equity=self.config.initial_capital,
        )
        open_position: Optional[Position] = None
        trades: List[Trade] = []
        equity_curve: List[float] = []
        pending_orders: List[Tuple[int, OrderIntent, str]] = []

        for idx in range(min_bars, len(series.candles)):
            candle = series.candles[idx]
            self._execute_pending_orders(idx, candle, portfolio, trades, pending_orders)
            open_position = portfolio.open_positions[0] if portfolio.open_positions else None

            if open_position:
                exit_trade = self._check_stop_take(candle, open_position)
                if exit_trade:
                    trade, position = exit_trade
                    self._close_position(portfolio, trade, position)
                    trades.append(trade)

            open_position = portfolio.open_positions[0] if portfolio.open_positions else None
            decision = self.strategy.evaluate(
                MarketSeries(series.symbol, series.candles[: idx + 1]),
                open_position,
                portfolio,
            )

            if decision.action == DecisionType.EXIT and open_position:
                exit_intent = self._create_exit_intent(open_position, candle)
                pending_orders.append((self.execution_model.execution_index(idx), exit_intent, "signal_exit"))

            if decision.action in (DecisionType.BUY, DecisionType.SELL) and not open_position:
                if decision.action == DecisionType.SELL and not self.config.allow_short:
                    pass
                else:
                    intent = self._size_intent(decision, portfolio)
                    if intent and self.risk_manager.can_open_trade(portfolio):
                        pending_orders.append((self.execution_model.execution_index(idx), intent, "signal_entry"))

            self._update_equity(portfolio, candle, open_position)
            equity_curve.append(portfolio.equity)

        metrics = compute_metrics(trades, equity_curve)
        warnings = self._evaluate_warnings(trades, equity_curve, series)
        return BacktestResult(trades=trades, metrics=metrics, equity_curve=equity_curve, warnings=warnings)

    def _execute_pending_orders(
        self,
        index: int,
        candle: Candle,
        portfolio: PortfolioState,
        trades: List[Trade],
        pending_orders: List[Tuple[int, OrderIntent, str]],
    ) -> None:
        if not pending_orders:
            return
        ready = [o for o in pending_orders if o[0] == index]
        pending_orders[:] = [o for o in pending_orders if o[0] != index]
        for _, intent, reason in ready:
            fill = self.execution_model.fill_order(intent, candle)
            if not fill:
                continue
            open_position = portfolio.open_positions[0] if portfolio.open_positions else None
            if open_position and reason == "signal_exit":
                trade = self._build_trade_from_exit(open_position, fill, reason)
                self._close_position(portfolio, trade, open_position)
                trades.append(trade)
                continue
            if not open_position and reason == "signal_entry":
                position = Position(
                    symbol=fill.symbol,
                    side=fill.side,
                    entry_price=fill.price,
                    quantity=fill.quantity,
                    stop_loss=intent.stop_loss,
                    take_profit=intent.take_profit,
                    opened_at=fill.filled_at,
                )
                position.fees_paid += fill.fee
                self._apply_entry_cash(portfolio, position)
                portfolio.open_positions = [position]

    def _check_stop_take(self, candle: Candle, position: Position) -> Optional[Tuple[Trade, Position]]:
        if position.side == OrderSide.BUY:
            hit_stop = candle.low <= position.stop_loss
            hit_take = candle.high >= position.take_profit
            if hit_stop and hit_take:
                exit_price = position.stop_loss
                reason = "stop_loss"
            elif hit_stop:
                exit_price = position.stop_loss
                reason = "stop_loss"
            elif hit_take:
                exit_price = position.take_profit
                reason = "take_profit"
            else:
                return None
        else:
            hit_stop = candle.high >= position.stop_loss
            hit_take = candle.low <= position.take_profit
            if hit_stop and hit_take:
                exit_price = position.stop_loss
                reason = "stop_loss"
            elif hit_stop:
                exit_price = position.stop_loss
                reason = "stop_loss"
            elif hit_take:
                exit_price = position.take_profit
                reason = "take_profit"
            else:
                return None

        side = OrderSide.SELL if position.side == OrderSide.BUY else OrderSide.BUY
        exit_price = self.execution_model._apply_spread_slippage(exit_price, side)
        fee = abs(exit_price * position.quantity) * self.execution_model.config.fee_rate
        trade = self._build_trade(
            position,
            exit_price,
            candle.timestamp,
            fee,
            reason,
        )
        position.exit_price = exit_price
        position.closed_at = candle.timestamp
        position.realized_pnl = trade.pnl
        return trade, position

    def _size_intent(self, decision: StrategyDecision, portfolio: PortfolioState) -> Optional[OrderIntent]:
        intent = decision.intent
        if not intent:
            return None
        quantity = self.risk_manager.size_position(portfolio.equity, intent)
        if quantity <= 0:
            return None
        if not self.risk_manager.exposure_ok(portfolio.equity, quantity, intent.reference_price):
            return None
        return OrderIntent(
            symbol=intent.symbol,
            side=intent.side,
            order_type=OrderType.MARKET,
            quantity=quantity,
            reference_price=intent.reference_price,
            stop_loss=intent.stop_loss,
            take_profit=intent.take_profit,
            invalidation=intent.invalidation,
            created_at=intent.created_at,
        )

    def _create_exit_intent(self, position: Position, candle: Candle) -> OrderIntent:
        side = OrderSide.SELL if position.side == OrderSide.BUY else OrderSide.BUY
        return OrderIntent(
            symbol=position.symbol,
            side=side,
            order_type=OrderType.MARKET,
            quantity=position.quantity,
            reference_price=candle.close,
            stop_loss=0.0,
            take_profit=0.0,
            invalidation=0.0,
            created_at=candle.timestamp,
        )

    def _apply_entry_cash(self, portfolio: PortfolioState, position: Position) -> None:
        notional = position.entry_price * position.quantity
        if position.side == OrderSide.BUY:
            portfolio.cash -= notional + position.fees_paid
        else:
            portfolio.cash += notional - position.fees_paid

    def _close_position(self, portfolio: PortfolioState, trade: Trade, position: Position) -> None:
        notional = trade.exit_price * trade.quantity
        if position.side == OrderSide.BUY:
            portfolio.cash += notional - (trade.fees_paid - position.fees_paid)
        else:
            portfolio.cash -= notional + (trade.fees_paid - position.fees_paid)
        portfolio.realized_pnl += trade.pnl
        if trade.pnl <= 0:
            portfolio.consecutive_losses += 1
        else:
            portfolio.consecutive_losses = 0
        portfolio.open_positions = []

    def _update_equity(self, portfolio: PortfolioState, candle: Candle, position: Optional[Position]) -> None:
        if position:
            if position.side == OrderSide.BUY:
                portfolio.equity = portfolio.cash + position.quantity * candle.close
            else:
                portfolio.equity = portfolio.cash - position.quantity * candle.close
        else:
            portfolio.equity = portfolio.cash
        if portfolio.equity > portfolio.peak_equity:
            portfolio.peak_equity = portfolio.equity
        if portfolio.peak_equity > 0:
            portfolio.drawdown = (portfolio.peak_equity - portfolio.equity) / portfolio.peak_equity

    def _build_trade_from_exit(self, position: Position, fill, reason: str) -> Trade:
        return self._build_trade(position, fill.price, fill.filled_at, fill.fee, reason)

    def _build_trade(
        self,
        position: Position,
        exit_price: float,
        exit_time: int,
        exit_fee: float,
        reason: str,
    ) -> Trade:
        if position.side == OrderSide.BUY:
            pnl = (exit_price - position.entry_price) * position.quantity - (position.fees_paid + exit_fee)
        else:
            pnl = (position.entry_price - exit_price) * position.quantity - (position.fees_paid + exit_fee)
        return_pct = pnl / (position.entry_price * position.quantity) if position.entry_price > 0 else 0.0
        return Trade(
            symbol=position.symbol,
            side=position.side,
            entry_price=position.entry_price,
            exit_price=exit_price,
            quantity=position.quantity,
            entry_time=position.opened_at,
            exit_time=exit_time,
            pnl=pnl,
            return_pct=return_pct,
            fees_paid=position.fees_paid + exit_fee,
            exit_reason=reason,
        )

    def _evaluate_warnings(self, trades: List[Trade], equity_curve: List[float], series: MarketSeries) -> List[str]:
        warnings: List[str] = []
        if not trades:
            warnings.append("no_trades")
            return warnings

        timestamps = [c.timestamp for c in series.candles]
        days = max(1.0, (timestamps[-1] - timestamps[0]) / 86400)
        trades_per_day = len(trades) / days
        if trades_per_day > 10:
            warnings.append("overtrading")

        if equity_curve:
            if max(equity_curve) == min(equity_curve):
                warnings.append("flat_equity")
        else:
            warnings.append("no_equity_curve")

        if any(abs(t.return_pct) > 1.0 for t in trades):
            warnings.append("extreme_returns")

        return warnings

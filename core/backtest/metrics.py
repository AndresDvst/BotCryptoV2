from dataclasses import dataclass
from typing import List, Dict

from core.domain import Trade


@dataclass(frozen=True)
class BacktestMetrics:
    net_pnl: float
    win_rate: float
    expectancy: float
    max_drawdown: float
    profit_factor: float
    trades: int
    max_losing_streak: int
    avg_win: float
    avg_loss: float


def compute_metrics(trades: List[Trade], equity_curve: List[float]) -> BacktestMetrics:
    trades_count = len(trades)
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    net_pnl = sum(t.pnl for t in trades)
    win_rate = (len(wins) / trades_count) if trades_count > 0 else 0.0
    avg_win = sum(t.pnl for t in wins) / len(wins) if wins else 0.0
    avg_loss = sum(t.pnl for t in losses) / len(losses) if losses else 0.0
    loss_rate = (len(losses) / trades_count) if trades_count > 0 else 0.0
    expectancy = (avg_win * win_rate) + (avg_loss * loss_rate)
    gross_profit = sum(t.pnl for t in wins)
    gross_loss = abs(sum(t.pnl for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    max_drawdown = _max_drawdown(equity_curve)
    max_losing_streak = _max_consecutive_losses(trades)
    return BacktestMetrics(
        net_pnl=net_pnl,
        win_rate=win_rate,
        expectancy=expectancy,
        max_drawdown=max_drawdown,
        profit_factor=profit_factor,
        trades=trades_count,
        max_losing_streak=max_losing_streak,
        avg_win=avg_win,
        avg_loss=avg_loss,
    )


def _max_drawdown(equity_curve: List[float]) -> float:
    peak = equity_curve[0] if equity_curve else 0.0
    max_dd = 0.0
    for value in equity_curve:
        if value > peak:
            peak = value
        if peak > 0:
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
    return max_dd


def _max_consecutive_losses(trades: List[Trade]) -> int:
    max_streak = 0
    current = 0
    for trade in trades:
        if trade.pnl <= 0:
            current += 1
            if current > max_streak:
                max_streak = current
        else:
            current = 0
    return max_streak

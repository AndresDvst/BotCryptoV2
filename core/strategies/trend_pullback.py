from dataclasses import dataclass
from typing import Optional, List

from core.domain import (
    MarketSeries,
    Position,
    PortfolioState,
    StrategyDecision,
    DecisionType,
    OrderIntent,
    OrderSide,
    OrderType,
)
from core.indicators import ema, rsi, macd, atr, slope


@dataclass(frozen=True)
class TrendPullbackConfig:
    ema_fast: int = 20
    ema_slow: int = 50
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    atr_period: int = 14
    swing_lookback: int = 10
    pullback_tolerance: float = 0.003
    atr_stop_mult: float = 1.6
    rr_ratio: float = 2.0
    min_atr_pct: float = 0.002
    max_atr_pct: float = 0.08
    min_rsi_long: float = 52.0
    max_rsi_short: float = 48.0


class TrendPullbackStrategy:
    def __init__(self, config: Optional[TrendPullbackConfig] = None) -> None:
        self.config = config or TrendPullbackConfig()

    def min_bars(self) -> int:
        return max(
            self.config.ema_slow + 2,
            self.config.atr_period + 2,
            self.config.macd_slow + self.config.macd_signal + 2,
            self.config.rsi_period + 2,
            self.config.swing_lookback + 2,
        )

    def evaluate(
        self,
        market: MarketSeries,
        position: Optional[Position],
        portfolio: PortfolioState,
    ) -> StrategyDecision:
        candles = market.candles
        if len(candles) < self.min_bars():
            return StrategyDecision(action=DecisionType.HOLD, reason="insufficient_data")

        closes = [c.close for c in candles]
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        last = candles[-1]

        ema_fast = ema(closes, self.config.ema_fast)
        ema_slow = ema(closes, self.config.ema_slow)
        if not ema_fast or not ema_slow:
            return StrategyDecision(action=DecisionType.HOLD, reason="ema_unavailable")

        ema_fast_last = ema_fast[-1]
        ema_slow_last = ema_slow[-1]
        ema_slow_slope = slope(ema_slow)[-1] if len(ema_slow) > 1 else 0.0

        trend_bull = ema_fast_last > ema_slow_last and ema_slow_slope > 0
        trend_bear = ema_fast_last < ema_slow_last and ema_slow_slope < 0

        atr_values = atr(highs, lows, closes, self.config.atr_period)
        if not atr_values:
            return StrategyDecision(action=DecisionType.HOLD, reason="atr_unavailable")
        atr_last = atr_values[-1]
        atr_pct = atr_last / last.close if last.close > 0 else 0.0
        if atr_pct < self.config.min_atr_pct or atr_pct > self.config.max_atr_pct:
            return StrategyDecision(action=DecisionType.HOLD, reason="volatility_filter")

        rsi_values = rsi(closes, self.config.rsi_period)
        if len(rsi_values) < 2:
            return StrategyDecision(action=DecisionType.HOLD, reason="rsi_unavailable")
        rsi_last = rsi_values[-1]
        rsi_prev = rsi_values[-2]

        macd_line, macd_signal, macd_hist = macd(
            closes,
            self.config.macd_fast,
            self.config.macd_slow,
            self.config.macd_signal,
        )
        if len(macd_hist) < 2:
            return StrategyDecision(action=DecisionType.HOLD, reason="macd_unavailable")
        hist_last = macd_hist[-1]
        hist_prev = macd_hist[-2]

        pullback_band = self.config.pullback_tolerance * last.close
        near_fast = abs(last.close - ema_fast_last) <= pullback_band

        if position:
            if position.side == OrderSide.BUY:
                if last.close < ema_slow_last or hist_last < 0:
                    return StrategyDecision(action=DecisionType.EXIT, reason="thesis_failed")
                return StrategyDecision(action=DecisionType.HOLD, reason="in_position")
            if position.side == OrderSide.SELL:
                if last.close > ema_slow_last or hist_last > 0:
                    return StrategyDecision(action=DecisionType.EXIT, reason="thesis_failed")
                return StrategyDecision(action=DecisionType.HOLD, reason="in_position")

        if trend_bull and near_fast and hist_last > 0 and hist_last > hist_prev and rsi_last > self.config.min_rsi_long and rsi_last > rsi_prev:
            stop = self._compute_stop_loss(lows, last.close, atr_last, OrderSide.BUY)
            take = last.close + (last.close - stop) * self.config.rr_ratio
            intent = OrderIntent(
                symbol=market.symbol,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=0.0,
                reference_price=last.close,
                stop_loss=stop,
                take_profit=take,
                invalidation=ema_slow_last,
                created_at=last.timestamp,
            )
            return StrategyDecision(
                action=DecisionType.BUY,
                intent=intent,
                reason="trend_pullback_long",
                metadata={"atr": atr_last, "rsi": rsi_last},
            )

        if trend_bear and near_fast and hist_last < 0 and hist_last < hist_prev and rsi_last < self.config.max_rsi_short and rsi_last < rsi_prev:
            stop = self._compute_stop_loss(highs, last.close, atr_last, OrderSide.SELL)
            take = last.close - (stop - last.close) * self.config.rr_ratio
            intent = OrderIntent(
                symbol=market.symbol,
                side=OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=0.0,
                reference_price=last.close,
                stop_loss=stop,
                take_profit=take,
                invalidation=ema_slow_last,
                created_at=last.timestamp,
            )
            return StrategyDecision(
                action=DecisionType.SELL,
                intent=intent,
                reason="trend_pullback_short",
                metadata={"atr": atr_last, "rsi": rsi_last},
            )

        return StrategyDecision(action=DecisionType.HOLD, reason="no_setup")

    def _compute_stop_loss(self, swings: List[float], price: float, atr_value: float, side: OrderSide) -> float:
        lookback = swings[-self.config.swing_lookback:]
        if side == OrderSide.BUY:
            swing_low = min(lookback)
            return min(swing_low, price - atr_value * self.config.atr_stop_mult)
        swing_high = max(lookback)
        return max(swing_high, price + atr_value * self.config.atr_stop_mult)

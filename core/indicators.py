from typing import List, Tuple


def ema(values: List[float], period: int) -> List[float]:
    if period <= 0 or len(values) < period:
        return []
    k = 2 / (period + 1)
    ema_values = []
    sma = sum(values[:period]) / period
    ema_values.append(sma)
    for price in values[period:]:
        ema_values.append((price - ema_values[-1]) * k + ema_values[-1])
    return ema_values


def sma(values: List[float], period: int) -> List[float]:
    if period <= 0 or len(values) < period:
        return []
    result = []
    window_sum = sum(values[:period])
    result.append(window_sum / period)
    for i in range(period, len(values)):
        window_sum += values[i] - values[i - period]
        result.append(window_sum / period)
    return result


def rsi(values: List[float], period: int = 14) -> List[float]:
    if period <= 0 or len(values) <= period:
        return []
    gains = []
    losses = []
    for i in range(1, len(values)):
        delta = values[i] - values[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    rsi_values = []
    rs = avg_gain / avg_loss if avg_loss > 0 else 0.0
    rsi_values.append(100 - (100 / (1 + rs)))
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        rs = avg_gain / avg_loss if avg_loss > 0 else 0.0
        rsi_values.append(100 - (100 / (1 + rs)))
    return rsi_values


def macd(values: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[List[float], List[float], List[float]]:
    if len(values) < slow + signal:
        return [], [], []
    ema_fast = ema(values, fast)
    ema_slow = ema(values, slow)
    if not ema_fast or not ema_slow:
        return [], [], []
    macd_line = [f - s for f, s in zip(ema_fast[-len(ema_slow):], ema_slow)]
    signal_line = ema(macd_line, signal)
    if not signal_line:
        return [], [], []
    hist = [m - s for m, s in zip(macd_line[-len(signal_line):], signal_line)]
    return macd_line[-len(signal_line):], signal_line, hist


def atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> List[float]:
    if len(closes) < period + 1:
        return []
    trs = []
    for i in range(1, len(closes)):
        high = highs[i]
        low = lows[i]
        prev_close = closes[i - 1]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
    atr_values = []
    atr_values.append(sum(trs[:period]) / period)
    for i in range(period, len(trs)):
        atr_values.append((atr_values[-1] * (period - 1) + trs[i]) / period)
    return atr_values


def bollinger(values: List[float], period: int = 20, std_dev: float = 2.0) -> Tuple[List[float], List[float], List[float]]:
    if len(values) < period:
        return [], [], []
    mid = []
    upper = []
    lower = []
    for i in range(period - 1, len(values)):
        window = values[i - period + 1:i + 1]
        mean = sum(window) / period
        variance = sum((x - mean) ** 2 for x in window) / period
        std = variance ** 0.5
        mid.append(mean)
        upper.append(mean + std_dev * std)
        lower.append(mean - std_dev * std)
    return upper, mid, lower


def stdev(values: List[float], period: int) -> List[float]:
    if period <= 0 or len(values) < period:
        return []
    result = []
    for i in range(period - 1, len(values)):
        window = values[i - period + 1:i + 1]
        mean = sum(window) / period
        variance = sum((x - mean) ** 2 for x in window) / period
        result.append(variance ** 0.5)
    return result


def slope(values: List[float]) -> List[float]:
    if len(values) < 2:
        return []
    return [values[i] - values[i - 1] for i in range(1, len(values))]

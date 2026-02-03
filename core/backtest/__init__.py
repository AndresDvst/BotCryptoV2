"""Backtest package stubs.

This module intentionally provides small lightweight stubs so IDEs and imports
(e.g., Pylance) can resolve names used across the codebase. These are
minimal and safe; replace with full implementations when available.
"""

from .engine import BacktestEngine, BacktestConfig
from .execution import ExecutionModel, ExecutionConfig
from .metrics import BacktestMetrics

__all__ = [
    "BacktestEngine",
    "BacktestConfig",
    "ExecutionModel",
    "ExecutionConfig",
    "BacktestMetrics",
]

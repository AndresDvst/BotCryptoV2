"""
Servicio de Backtesting integrado con el bot.
Permite ejecutar backtests usando datos históricos de Binance.
"""
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict

from utils.logger import logger
from config.config import Config

# Imports del motor de backtesting
from core.domain import Candle, MarketSeries
from core.backtest import BacktestEngine, BacktestConfig
from core.backtest.execution import ExecutionModel, ExecutionConfig
from core.backtest.metrics import BacktestMetrics
from core.risk import RiskManager, RiskConfig
from core.strategies import TrendPullbackStrategy, TrendPullbackConfig


@dataclass
class BacktestResult:
    symbol: str
    timeframe: str
    period_days: int
    initial_capital: float
    final_equity: float
    total_return_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown_pct: float
    sharpe_ratio: float
    avg_trade_pnl: float
    best_trade_pct: float
    worst_trade_pct: float
    avg_holding_time_hours: float
    warnings: List[str]
    executed_at: str


class BacktestService:
    """Servicio para ejecutar backtests usando datos de Binance."""
    
    RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backtest_results')
    
    def __init__(self, binance_service=None):
        """
        Inicializa el servicio de backtesting.
        
        Args:
            binance_service: Instancia de BinanceService (lazy loading si no se proporciona)
        """
        self._binance = binance_service
        os.makedirs(self.RESULTS_DIR, exist_ok=True)
        logger.info("✅ Servicio de Backtesting inicializado")
    
    @property
    def binance(self):
        """Lazy loading de BinanceService con manejo seguro de imports."""
        if self._binance is None:
            try:
                # Importación diferida para evitar circular imports
                from services.binance_service import BinanceService
                self._binance = BinanceService()
                logger.info("✅ BinanceService inicializado para Backtesting")
            except ImportError as e:
                logger.error(f"❌ Error de importación de BinanceService: {e}")
                raise RuntimeError("No se pudo importar BinanceService. Verifique las dependencias.") from e
            except Exception as e:
                logger.error(f"❌ Error inicializando BinanceService: {e}")
                raise RuntimeError(f"Error inicializando BinanceService: {e}") from e
        return self._binance
    
    def _fetch_historical_candles(
        self,
        symbol: str,
        timeframe: str = '1h',
        days: int = 30
    ) -> List[Candle]:
        """
        Obtiene velas históricas de Binance.
        
        Args:
            symbol: Par de trading (ej: 'BTC/USDT')
            timeframe: Timeframe ('1m', '5m', '15m', '1h', '4h', '1d')
            days: Días de histórico
            
        Returns:
            Lista de Candles para el motor de backtest
        """
        try:
            # Calcular límite de velas según timeframe
            timeframe_minutes = {
                '1m': 1, '5m': 5, '15m': 15, '30m': 30,
                '1h': 60, '2h': 120, '4h': 240, '1d': 1440
            }
            minutes_per_candle = timeframe_minutes.get(timeframe, 60)
            total_minutes = days * 24 * 60
            limit = min(1000, total_minutes // minutes_per_candle)
            
            # Obtener OHLCV de Binance
            ohlcv = self.binance.exchange.fetch_ohlcv(
                symbol,
                timeframe=timeframe,
                limit=limit
            )
            
            candles = []
            for row in ohlcv:
                candles.append(Candle(
                    timestamp=int(row[0]),
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5])
                ))
            
            logger.info(f"📊 Obtenidas {len(candles)} velas de {symbol} ({timeframe}, {days} días)")
            return candles
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo histórico de {symbol}: {e}")
            return []
    
    def run_backtest(
        self,
        symbol: str = 'BTC/USDT',
        timeframe: str = '1h',
        days: int = 30,
        initial_capital: float = 10000.0,
        risk_per_trade: float = 0.02,
        max_drawdown: float = 0.20,
        allow_short: bool = True,
        fee_rate: float = 0.001,
        slippage_pct: float = 0.0005
    ) -> Optional[BacktestResult]:
        """
        Ejecuta un backtest completo.
        
        Args:
            symbol: Par de trading
            timeframe: Timeframe para las velas
            days: Días de histórico
            initial_capital: Capital inicial
            risk_per_trade: Riesgo por operación (% del capital)
            max_drawdown: Drawdown máximo permitido
            allow_short: Permitir posiciones cortas
            fee_rate: Comisión por operación
            slippage_pct: Slippage estimado
            
        Returns:
            BacktestResult con métricas o None si falla
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"🧪 INICIANDO BACKTEST: {symbol}")
        logger.info(f"{'='*60}")
        logger.info(f"📈 Timeframe: {timeframe}")
        logger.info(f"📅 Período: {days} días")
        logger.info(f"💰 Capital inicial: ${initial_capital:,.2f}")
        logger.info(f"⚠️ Riesgo por trade: {risk_per_trade*100:.1f}%")
        logger.info(f"📉 Max Drawdown: {max_drawdown*100:.1f}%")
        
        # Obtener datos históricos
        candles = self._fetch_historical_candles(symbol, timeframe, days)
        if not candles:
            logger.error("❌ No se pudieron obtener datos históricos")
            return None
        
        # Configurar estrategia
        strategy = TrendPullbackStrategy(TrendPullbackConfig())
        
        # Configurar gestión de riesgo
        risk_manager = RiskManager(RiskConfig(
            risk_per_trade=risk_per_trade,
            max_drawdown=max_drawdown,
            max_consecutive_losses=4
        ))
        
        # Configurar modelo de ejecución
        execution = ExecutionModel(ExecutionConfig(
            fee_rate=fee_rate,
            slippage_pct=slippage_pct,
            spread_pct=0.0004,
            latency_bars=1
        ))
        
        # Configurar motor de backtest
        engine = BacktestEngine(
            strategy=strategy,
            risk_manager=risk_manager,
            execution_model=execution,
            config=BacktestConfig(
                initial_capital=initial_capital,
                allow_short=allow_short
            )
        )
        
        # Ejecutar backtest
        logger.info("⏳ Ejecutando simulación...")
        series = MarketSeries(symbol=symbol, candles=candles)
        result = engine.run(series)
        
        # Procesar resultados
        metrics = result.metrics
        trades = result.trades
        equity_curve = result.equity_curve
        
        # Calcular métricas adicionales
        final_equity = equity_curve[-1] if equity_curve else initial_capital
        total_return = ((final_equity - initial_capital) / initial_capital) * 100
        
        winning = [t for t in trades if t.pnl > 0]
        losing = [t for t in trades if t.pnl <= 0]
        win_rate = (len(winning) / len(trades) * 100) if trades else 0
        
        gross_profit = sum(t.pnl for t in winning) if winning else 0.0
        gross_loss = abs(sum(t.pnl for t in losing)) if losing else 0.0
        
        # Evitar división por cero con manejo seguro
        if gross_loss > 1e-10:  # Usar tolerancia para valores muy pequeños
            profit_factor = gross_profit / gross_loss
        else:
            profit_factor = float('inf') if gross_profit > 0 else 1.0
        
        avg_pnl = sum(t.pnl for t in trades) / len(trades) if trades else 0
        best_trade = max((t.return_pct for t in trades), default=0)
        worst_trade = min((t.return_pct for t in trades), default=0)
        
        # Tiempo promedio de holding
        if trades:
            holding_times = [(t.exit_time - t.entry_time) / 3600000 for t in trades]  # ms a horas
            avg_holding = sum(holding_times) / len(holding_times)
        else:
            avg_holding = 0
        
        # Crear resultado
        backtest_result = BacktestResult(
            symbol=symbol,
            timeframe=timeframe,
            period_days=days,
            initial_capital=initial_capital,
            final_equity=final_equity,
            total_return_pct=total_return,
            total_trades=len(trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=win_rate,
            profit_factor=min(profit_factor, 1000.0) if profit_factor != float('inf') else 1000.0,
            max_drawdown_pct=metrics.max_drawdown * 100 if hasattr(metrics, 'max_drawdown') else 0,
            sharpe_ratio=metrics.sharpe_ratio if hasattr(metrics, 'sharpe_ratio') else 0,
            avg_trade_pnl=avg_pnl,
            best_trade_pct=best_trade * 100,
            worst_trade_pct=worst_trade * 100,
            avg_holding_time_hours=avg_holding,
            warnings=result.warnings,
            executed_at=datetime.now().isoformat()
        )
        
        # Mostrar resultados
        self._print_results(backtest_result)
        
        # Guardar resultados
        self._save_result(backtest_result)
        
        return backtest_result

    def _print_results(self, result: BacktestResult) -> None:
        logger.info("🏁 Backtest finalizado:")
        logger.info(f"   Symbol: {result.symbol}")
        logger.info(f"   Period: {result.period_days}d {result.timeframe}")
        logger.info(f"   Final equity: ${result.final_equity:,.2f}")
        logger.info(f"   Return: {result.total_return_pct:.2f}%")
        logger.info(f"   Trades: {result.total_trades} (W:{result.winning_trades}/L:{result.losing_trades})")
        logger.info(f"   Win rate: {result.win_rate:.2f}%")
        logger.info(f"   Profit factor: {result.profit_factor:.2f}")
        logger.info(f"   Max drawdown: {result.max_drawdown_pct:.2f}%")
        if result.warnings:
            logger.warning(f"   Warnings: {len(result.warnings)}")

    def _save_result(self, result: BacktestResult) -> None:
        try:
            filename = f"{result.symbol.replace('/','_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            path = os.path.join(self.RESULTS_DIR, filename)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(asdict(result), f, indent=2, default=str)
            logger.info(f"💾 Resultado guardado en {path}")
        except Exception as e:
            logger.error(f"❌ Error guardando resultado: {e}")
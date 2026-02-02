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
    """Resultado de un backtest con métricas y trades."""
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
        """Lazy loading de BinanceService."""
        if self._binance is None:
            try:
                from services.binance_service import BinanceService
                self._binance = BinanceService()
                logger.info("✅ BinanceService inicializado para Backtesting")
            except Exception as e:
                logger.error(f"❌ Error inicializando BinanceService: {e}")
                raise
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
        
        gross_profit = sum(t.pnl for t in winning) if winning else 0
        gross_loss = abs(sum(t.pnl for t in losing)) if losing else 0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')
        
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
            profit_factor=profit_factor if profit_factor != float('inf') else 999.99,
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
        """Imprime los resultados del backtest de forma visual."""
        print("\n" + "="*60)
        print("📊 RESULTADOS DEL BACKTEST")
        print("="*60)
        
        # Retorno con color
        if result.total_return_pct >= 0:
            return_emoji = "🟢"
        else:
            return_emoji = "🔴"
        
        print(f"\n💰 RENDIMIENTO")
        print(f"   Capital Inicial: ${result.initial_capital:,.2f}")
        print(f"   Capital Final:   ${result.final_equity:,.2f}")
        print(f"   {return_emoji} Retorno Total: {result.total_return_pct:+.2f}%")
        
        print(f"\n📈 ESTADÍSTICAS DE TRADES")
        print(f"   Total de Trades: {result.total_trades}")
        print(f"   Trades Ganadores: {result.winning_trades} ({result.win_rate:.1f}%)")
        print(f"   Trades Perdedores: {result.losing_trades}")
        print(f"   Profit Factor: {result.profit_factor:.2f}")
        
        print(f"\n⚠️ RIESGO")
        print(f"   Max Drawdown: {result.max_drawdown_pct:.2f}%")
        print(f"   Sharpe Ratio: {result.sharpe_ratio:.2f}")
        
        print(f"\n📋 DETALLES")
        print(f"   PnL Promedio: ${result.avg_trade_pnl:,.2f}")
        print(f"   Mejor Trade: {result.best_trade_pct:+.2f}%")
        print(f"   Peor Trade: {result.worst_trade_pct:+.2f}%")
        print(f"   Tiempo Promedio: {result.avg_holding_time_hours:.1f} horas")
        
        if result.warnings:
            print(f"\n⚠️ ADVERTENCIAS: {', '.join(result.warnings)}")
        
        print("="*60 + "\n")
    
    def _save_result(self, result: BacktestResult) -> None:
        """Guarda el resultado del backtest en un archivo JSON."""
        filename = f"backtest_{result.symbol.replace('/', '_')}_{result.timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.RESULTS_DIR, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(asdict(result), f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Resultados guardados en: {filepath}")
    
    def run_multi_symbol_backtest(
        self,
        symbols: List[str] = None,
        timeframe: str = '1h',
        days: int = 30,
        initial_capital: float = 10000.0
    ) -> List[BacktestResult]:
        """
        Ejecuta backtests para múltiples símbolos.
        
        Args:
            symbols: Lista de pares (default: top 5 por volumen)
            timeframe: Timeframe
            days: Días de histórico
            initial_capital: Capital inicial por símbolo
            
        Returns:
            Lista de resultados
        """
        if symbols is None:
            # Obtener top 5 por volumen
            top_coins = self.binance.get_top_coins(limit=5)
            symbols = [f"{coin['base']}/USDT" for coin in top_coins if coin.get('base')]
        
        logger.info(f"\n🔄 Ejecutando backtests para: {', '.join(symbols)}")
        
        results = []
        for symbol in symbols:
            try:
                result = self.run_backtest(
                    symbol=symbol,
                    timeframe=timeframe,
                    days=days,
                    initial_capital=initial_capital
                )
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"❌ Error en backtest de {symbol}: {e}")
        
        # Resumen comparativo
        if results:
            self._print_comparison(results)
        
        return results
    
    def _print_comparison(self, results: List[BacktestResult]) -> None:
        """Imprime comparación de resultados de múltiples backtests."""
        print("\n" + "="*70)
        print("📊 COMPARACIÓN DE BACKTESTS")
        print("="*70)
        print(f"{'Símbolo':<12} {'Retorno':<10} {'Win Rate':<10} {'Trades':<8} {'Sharpe':<8} {'MaxDD':<10}")
        print("-"*70)
        
        for r in sorted(results, key=lambda x: x.total_return_pct, reverse=True):
            emoji = "🟢" if r.total_return_pct >= 0 else "🔴"
            print(f"{r.symbol:<12} {emoji}{r.total_return_pct:>+7.2f}%  {r.win_rate:>7.1f}%   {r.total_trades:>6}  {r.sharpe_ratio:>7.2f}  {r.max_drawdown_pct:>7.2f}%")
        
        print("="*70)
        
        # Mejor y peor
        best = max(results, key=lambda x: x.total_return_pct)
        worst = min(results, key=lambda x: x.total_return_pct)
        print(f"\n🏆 Mejor: {best.symbol} ({best.total_return_pct:+.2f}%)")
        print(f"💀 Peor: {worst.symbol} ({worst.total_return_pct:+.2f}%)")
        print()
    
    def interactive_backtest(self) -> None:
        """Menú interactivo para ejecutar backtests."""
        while True:
            print("\n" + "="*60)
            print("🧪 MENÚ DE BACKTESTING")
            print("="*60)
            print("1. 📈 Backtest de un símbolo")
            print("2. 📊 Backtest múltiple (Top 5 por volumen)")
            print("3. ⚙️ Backtest personalizado")
            print("4. 📁 Ver resultados guardados")
            print("0. 🔙 Volver al menú principal")
            print("="*60)
            
            choice = input("\nSelecciona una opción: ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                symbol = input("Símbolo (ej: BTC/USDT): ").strip().upper() or 'BTC/USDT'
                self.run_backtest(symbol=symbol)
            elif choice == '2':
                self.run_multi_symbol_backtest()
            elif choice == '3':
                self._custom_backtest_menu()
            elif choice == '4':
                self._list_saved_results()
            else:
                print("❌ Opción no válida")
    
    def _custom_backtest_menu(self) -> None:
        """Menú para backtest personalizado."""
        print("\n⚙️ CONFIGURACIÓN PERSONALIZADA")
        print("-"*40)
        
        symbol = input("Símbolo (BTC/USDT): ").strip().upper() or 'BTC/USDT'
        timeframe = input("Timeframe (1h): ").strip() or '1h'
        days = int(input("Días de histórico (30): ").strip() or '30')
        capital = float(input("Capital inicial (10000): ").strip() or '10000')
        risk = float(input("Riesgo por trade % (2): ").strip() or '2') / 100
        allow_short = input("Permitir shorts? (s/n): ").strip().lower() == 's'
        
        self.run_backtest(
            symbol=symbol,
            timeframe=timeframe,
            days=days,
            initial_capital=capital,
            risk_per_trade=risk,
            allow_short=allow_short
        )
    
    def _list_saved_results(self) -> None:
        """Lista los resultados de backtests guardados."""
        files = [f for f in os.listdir(self.RESULTS_DIR) if f.endswith('.json')]
        
        if not files:
            print("\n📭 No hay resultados guardados")
            return
        
        print(f"\n📁 Resultados guardados ({len(files)}):")
        print("-"*50)
        for i, f in enumerate(sorted(files, reverse=True)[:10], 1):
            print(f"  {i}. {f}")
        
        if len(files) > 10:
            print(f"  ... y {len(files) - 10} más")

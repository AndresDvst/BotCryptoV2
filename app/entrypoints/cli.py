import argparse
import json

from app.use_cases import run_backtest, BacktestRequest


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["backtest"], required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--csv", dest="csv_path", required=True)
    parser.add_argument("--initial-capital", type=float, default=10000.0)
    parser.add_argument("--fee-rate", type=float, default=0.001)
    parser.add_argument("--slippage", type=float, default=0.0005)
    parser.add_argument("--spread", type=float, default=0.0004)
    parser.add_argument("--latency-bars", type=int, default=1)
    parser.add_argument("--risk-per-trade", type=float, default=0.01)
    parser.add_argument("--max-drawdown", type=float, default=0.2)
    parser.add_argument("--max-consecutive-losses", type=int, default=4)
    parser.add_argument("--allow-short", action="store_true")
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    if args.mode == "backtest":
        request = BacktestRequest(
            symbol=args.symbol,
            csv_path=args.csv_path,
            initial_capital=args.initial_capital,
            fee_rate=args.fee_rate,
            slippage_pct=args.slippage,
            spread_pct=args.spread,
            latency_bars=args.latency_bars,
            risk_per_trade=args.risk_per_trade,
            max_drawdown=args.max_drawdown,
            max_consecutive_losses=args.max_consecutive_losses,
            allow_short=args.allow_short,
        )
        result = run_backtest(request)
        payload = {
            "metrics": result.metrics.__dict__,
            "trades": [t.__dict__ for t in result.trades],
            "warnings": result.warnings,
        }
        print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

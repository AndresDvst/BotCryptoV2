import time
import types
import sys

# Avoid importing heavy optional deps (e.g., talib) during test collection by stubbing them
if 'talib' not in sys.modules:
    import types as _types
    sys.modules['talib'] = _types.ModuleType('talib')
    sys.modules['talib.abstract'] = _types.ModuleType('talib.abstract')

# Stub minimal 'utils' module used by technical modules to avoid import-time side effects
if 'utils' not in sys.modules:
    import types as _types
    _mod = _types.ModuleType('utils')
    _mod.validate_dataframe = lambda df: None
    sys.modules['utils'] = _mod

# Stub utils.logger as well
if 'utils.logger' not in sys.modules:
    import types as _types
    _logmod = _types.ModuleType('utils.logger')
    class _DummyLogger:
        def info(self, *a, **kw): pass
        def warning(self, *a, **kw): pass
        def error(self, *a, **kw): pass
        def debug(self, *a, **kw): pass
    _logmod.logger = _DummyLogger()
    sys.modules['utils.logger'] = _logmod

# Stub utils.security
if 'utils.security' not in sys.modules:
    import types as _types
    _sec = _types.ModuleType('utils.security')
    _sec.sanitize_exception = lambda e: str(e)
    class _Redactor:
        def register_secrets_from_config(self, cfg): pass
    _sec.get_redactor = lambda: _Redactor()
    sys.modules['utils.security'] = _sec

# Stub services.backtest_service to avoid import-time syntax errors in the repo
if 'services.backtest_service' not in sys.modules:
    import types as _types
    _mod = _types.ModuleType('services.backtest_service')
    class BacktestService:
        def __init__(self, *a, **kw):
            pass
    _mod.BacktestService = BacktestService
    sys.modules['services.backtest_service'] = _mod

from bot_orchestrator import CryptoBotOrchestrator


class FakeBinance:
    def __init__(self, all_tickers, significant):
        self._all = all_tickers
        self._sig = significant

    def filter_significant_changes(self):
        return self._sig

    def get_all_tickers(self):
        return self._all

    def get_2hour_change(self, coins):
        # Return enriched coins mirroring input (symbol + change_2h)
        res = []
        for c in coins:
            sym = c.get('symbol')
            # Make sure top-by-volume CREAM/USDT has a significant change_2h so test can detect it
            ch = 12.3 if sym == 'CREAM/USDT' else 1.0
            res.append({'symbol': sym, 'change_2h': ch, 'price': 1.0, 'change_24h': 0.0})
        return res


class FakeAI:
    def analyze_complete_market_batch(self, coins, market_sentiment, news_titles):
        return {
            'market_analysis': {'overview': 'ok'},
            'trading_summary': {'main_recommendation': 'none', 'confidence': 0},
            'crypto_recommendations': {'top_buys': [], 'top_sells': []}
        }
    def generate_twitter_4_summaries(self, market_sentiment, coins_only_binance, coins_both_enriched, max_chars=280):
        # Minimal stub returning empty summaries
        return {"up_24h":"","down_24h":"","up_2h":"","down_2h":""}


def test_execute_analysis_steps_uses_top_volume_for_2h():
    # Setup: significant_coins does NOT include CREAM/USDT
    significant_coins = [{'symbol': 'AAA/USDT', 'change_24h': 20.0}]

    # all_tickers includes CREAM with very high volume, should be picked for 2h scan
    all_tickers = {
        'AAA/USDT': {'quoteVolume': 1000},
        'CREAM/USDT': {'quoteVolume': 1_000_000},
        'BBB/USDT': {'quoteVolume': 5000}
    }

    fake_binance = FakeBinance(all_tickers, significant_coins)
    fake_ai = FakeAI()

    # Create orchestrator instance without calling __init__ to avoid Config.validate side-effects
    orchestrator = CryptoBotOrchestrator.__new__(CryptoBotOrchestrator)
    # Minimal attributes required by _execute_analysis_steps
    orchestrator.binance = fake_binance
    orchestrator.ai_analyzer = fake_ai
    orchestrator.technical_analysis = None
    orchestrator.market_sentiment = None
    orchestrator.news_service = None

    result = orchestrator._execute_analysis_steps()

    coins_enriched = result.get('coins_enriched', [])
    symbols = [c.get('symbol') for c in coins_enriched]

    # Expect that top-volume symbol CREAM/USDT is present in coins_enriched
    assert 'CREAM/USDT' in symbols, "CREAM/USDT should be included in 2h enrichment (top volume)"

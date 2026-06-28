"""WalletProfiler 단위 테스트"""
from src.domain.wallet_profiler import WalletProfiler


def _trade(side="BUY", outcome="Yes", market="mkt1", pnl=0.0, ts=1_700_000_000):
    return {"side": side, "outcome": outcome, "market": market,
            "cashPnl": pnl, "timestamp": ts}


def test_empty_history_returns_defaults():
    p = WalletProfiler.from_history([])
    assert p.total_trades == 0
    assert p.win_rate == 0.5
    assert p.bias_up == 0.5
    assert p.n_markets == 0


def test_total_trades_count():
    trades = [_trade() for _ in range(10)]
    p = WalletProfiler.from_history(trades)
    assert p.total_trades == 10


def test_n_markets_unique():
    trades = [_trade(market="m1"), _trade(market="m2"), _trade(market="m1")]
    p = WalletProfiler.from_history(trades)
    assert p.n_markets == 2


def test_bias_up_yes_heavy():
    trades = [_trade(side="BUY", outcome="Yes")] * 3 + [_trade(side="BUY", outcome="No")]
    p = WalletProfiler.from_history(trades)
    assert p.bias_up == 0.75


def test_total_pnl_sum():
    trades = [_trade(side="SELL", pnl=1000.0), _trade(side="SELL", pnl=-200.0)]
    p = WalletProfiler.from_history(trades)
    assert p.total_pnl == 800.0


def test_win_rate_from_sell_pnl():
    trades = [
        _trade(side="SELL", pnl=500.0),
        _trade(side="SELL", pnl=300.0),
        _trade(side="SELL", pnl=-100.0),
        _trade(side="SELL", pnl=-200.0),
    ]
    p = WalletProfiler.from_history(trades)
    assert p.win_rate == 0.5


def test_age_days_from_timestamp():
    import time
    old_ts = int(time.time()) - 10 * 86400  # 10 days ago
    trades = [_trade(ts=old_ts), _trade(ts=int(time.time()))]
    p = WalletProfiler.from_history(trades)
    assert 9 <= p.age_days <= 11

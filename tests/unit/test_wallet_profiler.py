"""WalletProfiler 단위 테스트"""
from src.domain.wallet_profiler import WalletProfiler


def _pos(outcome="Yes", market="mkt1", cash_pnl=0.0):
    return {"conditionId": market, "outcome": outcome,
            "cashPnl": cash_pnl, "avgPrice": 0.5, "curPrice": 0.5}


def test_empty_history_returns_defaults():
    p = WalletProfiler.from_history([])
    assert p.total_trades == 0
    assert p.win_rate == 0.5
    assert p.bias_up == 0.5
    assert p.n_markets == 0


def test_total_trades_count():
    p = WalletProfiler.from_history([_pos() for _ in range(10)])
    assert p.total_trades == 10


def test_n_markets_unique():
    p = WalletProfiler.from_history([_pos(market="m1"), _pos(market="m2"), _pos(market="m1")])
    assert p.n_markets == 2


def test_bias_up_yes_heavy():
    positions = [_pos(outcome="Yes")] * 3 + [_pos(outcome="No")]
    p = WalletProfiler.from_history(positions)
    assert p.bias_up == 0.75


def test_total_pnl_sum():
    positions = [_pos(cash_pnl=1000.0), _pos(cash_pnl=-200.0)]
    p = WalletProfiler.from_history(positions)
    assert p.total_pnl == 800.0


def test_win_rate_from_cash_pnl():
    positions = [
        _pos(cash_pnl=500.0),
        _pos(cash_pnl=300.0),
        _pos(cash_pnl=-100.0),
        _pos(cash_pnl=-200.0),
    ]
    p = WalletProfiler.from_history(positions)
    assert p.win_rate == 0.5


def test_insider_profile_classified():
    """신규 계정 시뮬레이션: age_days=0, n_markets<=3, total_trades<=5 → INSIDER"""
    from src.domain.wallet import Classification
    from src.domain.wallet_classifier import WalletClassifier

    positions = [
        _pos(outcome="Yes", market="m1", cash_pnl=15_000.0),
        _pos(outcome="Yes", market="m2", cash_pnl=8_000.0),
        _pos(outcome="No", market="m3", cash_pnl=-500.0),
    ]
    p = WalletProfiler.from_history(positions)
    # age_days=0 < 90, n_markets=3, total_trades=3 → INSIDER
    assert WalletClassifier.classify(p) == Classification.INSIDER

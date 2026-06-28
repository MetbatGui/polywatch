"""WalletProfile VO + Classification 단위 테스트"""
from src.domain.wallet import WalletProfile, Classification


def test_wallet_profile_fields():
    p = WalletProfile(
        win_rate=0.75,
        n_markets=5,
        total_pnl=30_000.0,
        age_days=10,
        bias_up=0.6,
        total_trades=50,
    )
    assert p.win_rate == 0.75
    assert p.n_markets == 5
    assert p.total_pnl == 30_000.0
    assert p.age_days == 10
    assert p.bias_up == 0.6
    assert p.total_trades == 50


def test_wallet_profile_is_immutable():
    p = WalletProfile(win_rate=0.5, n_markets=3, total_pnl=0.0,
                      age_days=30, bias_up=0.5, total_trades=10)
    try:
        p.win_rate = 0.9  # type: ignore
        assert False, "Should be immutable"
    except (AttributeError, TypeError):
        pass


def test_classification_values():
    assert Classification.INSIDER
    assert Classification.AMM_BOT
    assert Classification.ARBITRAGER
    assert Classification.GAMBLER
    assert Classification.UNKNOWN

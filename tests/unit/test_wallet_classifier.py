"""WalletClassifier Domain Service 단위 테스트"""
from src.domain.wallet import Classification, WalletProfile
from src.domain.wallet_classifier import WalletClassifier


def _profile(**kwargs) -> WalletProfile:
    defaults = dict(win_rate=0.5, n_markets=10, total_pnl=0.0,
                    age_days=30, bias_up=0.5, total_trades=20)
    return WalletProfile(**{**defaults, **kwargs})


def test_classify_insider():
    p = _profile(win_rate=0.72, n_markets=4, total_pnl=25_000.0)
    assert WalletClassifier.classify(p) == Classification.INSIDER


def test_classify_amm_bot():
    p = _profile(bias_up=0.50, total_trades=150)
    assert WalletClassifier.classify(p) == Classification.AMM_BOT


def test_classify_arbitrager():
    # avg_pos_val 없으므로 total_pnl 대비 n_markets으로 근사
    p = _profile(win_rate=0.9, n_markets=2, total_pnl=5_000.0, total_trades=5)
    assert WalletClassifier.classify(p) == Classification.ARBITRAGER


def test_classify_gambler():
    p = _profile(win_rate=0.15, total_trades=120, total_pnl=-15_000.0)
    assert WalletClassifier.classify(p) == Classification.GAMBLER


def test_classify_unknown():
    p = _profile()
    assert WalletClassifier.classify(p) == Classification.UNKNOWN


def test_insider_threshold_is_low_for_exploration():
    """탐색 모드: 낮은 임계값으로 재현율 우선"""
    p = _profile(win_rate=0.61, n_markets=9, total_pnl=5_001.0)
    assert WalletClassifier.classify(p) == Classification.INSIDER

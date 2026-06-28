"""WalletClassifier Domain Service 단위 테스트"""
from src.domain.wallet import Classification, WalletProfile
from src.domain.wallet_classifier import WalletClassifier


def _profile(**kwargs) -> WalletProfile:
    defaults = dict(win_rate=0.5, n_markets=10, total_pnl=0.0,
                    age_days=365, bias_up=0.5, total_trades=20)
    return WalletProfile(**{**defaults, **kwargs})


# ── INSIDER: 신규 계정 + 집중 베팅 ──────────────────────────────────────────

def test_classify_insider_new_account_few_trades():
    """신규 계정(<90일) + 마켓 3개 이하 + 거래 5건 이하 → INSIDER"""
    p = _profile(age_days=30, n_markets=2, total_trades=3)
    assert WalletClassifier.classify(p) == Classification.INSIDER


def test_classify_insider_boundary_age():
    """89일 = INSIDER, 90일 = 아님"""
    classify = WalletClassifier.classify
    assert classify(_profile(age_days=89, n_markets=1, total_trades=2)) == Classification.INSIDER
    assert classify(_profile(age_days=90, n_markets=1, total_trades=2)) != Classification.INSIDER


def test_classify_insider_boundary_trades():
    """거래 5건 = INSIDER, 6건 = 아님"""
    classify = WalletClassifier.classify
    assert classify(_profile(age_days=30, n_markets=2, total_trades=5)) == Classification.INSIDER
    assert classify(_profile(age_days=30, n_markets=2, total_trades=6)) != Classification.INSIDER


def test_classify_insider_boundary_markets():
    """마켓 3개 = INSIDER, 4개 = 아님"""
    classify = WalletClassifier.classify
    assert classify(_profile(age_days=30, n_markets=3, total_trades=3)) == Classification.INSIDER
    assert classify(_profile(age_days=30, n_markets=4, total_trades=3)) != Classification.INSIDER


# ── ARBITRAGER: 고승률 베테랑, 소수 마켓 집중 ─────────────────────────────

def test_classify_arbitrager():
    """베테랑(>=90일) + 극단적 승률(>85%) + 소수 마켓"""
    p = _profile(age_days=200, win_rate=0.9, n_markets=2, total_trades=8)
    assert WalletClassifier.classify(p) == Classification.ARBITRAGER


def test_arbitrager_not_confused_with_insider():
    """신규 계정은 승률 높아도 INSIDER 우선"""
    p = _profile(age_days=30, win_rate=0.95, n_markets=1, total_trades=2)
    assert WalletClassifier.classify(p) == Classification.INSIDER


# ── AMM_BOT ────────────────────────────────────────────────────────────────

def test_classify_amm_bot():
    p = _profile(bias_up=0.50, total_trades=150)
    assert WalletClassifier.classify(p) == Classification.AMM_BOT


# ── GAMBLER ────────────────────────────────────────────────────────────────

def test_classify_gambler():
    p = _profile(win_rate=0.15, total_trades=120, total_pnl=-15_000.0)
    assert WalletClassifier.classify(p) == Classification.GAMBLER


# ── UNKNOWN ────────────────────────────────────────────────────────────────

def test_classify_unknown():
    p = _profile()
    assert WalletClassifier.classify(p) == Classification.UNKNOWN

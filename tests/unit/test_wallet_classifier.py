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


# ── EXPERT: 베테랑 + 꾸준한 고승률 + 다양한 마켓 ─────────────────────────

def test_classify_expert():
    """베테랑(>=90일) + win_rate>0.60 + n_markets>5 + total_trades>=20 → EXPERT"""
    p = _profile(age_days=180, win_rate=0.65, n_markets=8, total_trades=30)
    assert WalletClassifier.classify(p) == Classification.EXPERT


def test_expert_boundary_age():
    """89일 계정 = EXPERT 아님"""
    p = _profile(age_days=89, win_rate=0.65, n_markets=8, total_trades=30)
    assert WalletClassifier.classify(p) != Classification.EXPERT


def test_expert_not_confused_with_arbitrager():
    """극단적 승률 + 균형 bias = ARBITRAGER, 보통 고승률 = EXPERT"""
    arb = _profile(age_days=200, win_rate=0.90, total_trades=40, bias_up=0.50)
    exp = _profile(age_days=200, win_rate=0.68, n_markets=10, total_trades=40)
    assert WalletClassifier.classify(arb) == Classification.ARBITRAGER
    assert WalletClassifier.classify(exp) == Classification.EXPERT


# ── ARBITRAGER: 극단적 승률 + 고빈도 + 균형 bias ─────────────────────────

def test_classify_arbitrager():
    """극단적 승률(>85%) + 고빈도(>=20) + 균형 bias → ARBITRAGER"""
    p = _profile(win_rate=0.9, total_trades=50, bias_up=0.50)
    assert WalletClassifier.classify(p) == Classification.ARBITRAGER


def test_arbitrager_not_confused_with_insider():
    """신규 계정은 승률 높아도 INSIDER 우선"""
    p = _profile(age_days=30, win_rate=0.95, n_markets=1, total_trades=2)
    assert WalletClassifier.classify(p) == Classification.INSIDER


def test_arbitrager_not_amm_bot():
    """승률 낮은 균형 bot은 AMM_BOT, 극단적 승률은 ARBITRAGER"""
    bot = _profile(win_rate=0.40, total_trades=150, bias_up=0.50)
    arb = _profile(win_rate=0.90, total_trades=50, bias_up=0.50)
    assert WalletClassifier.classify(bot) == Classification.AMM_BOT
    assert WalletClassifier.classify(arb) == Classification.ARBITRAGER


def test_arbitrager_requires_frequent_trades():
    """고승률이라도 거래 적으면 ARBITRAGER 아님"""
    p = _profile(win_rate=0.90, total_trades=10, bias_up=0.50)
    assert WalletClassifier.classify(p) != Classification.ARBITRAGER


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

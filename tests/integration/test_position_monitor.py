"""통합 테스트: 포지션 스냅샷 → 시그널 감지 → 알림 발송"""
import pytest

from src.application.ports import AlertPort, MarketRepo, PolymarketPort, WalletRepo
from src.application.position_monitor import PositionMonitor
from src.application.market_scan import MarketScanService
from src.domain.signal_detector import Position, SignalConfig
from src.domain.wallet import WalletProfile


class FakePolymarketPort:
    def __init__(self):
        self._markets: list[dict] = []
        self._positions: dict[str, list[Position]] = {}
        self._wallet_history: dict[str, list[dict]] = {}

    def fetch_active_markets(self) -> list[dict]:
        return list(self._markets)

    def fetch_positions(self, market_id: str) -> list[Position]:
        return list(self._positions.get(market_id, []))

    def fetch_wallet_history(self, address: str) -> list[dict]:
        return list(self._wallet_history.get(address, []))

    def fetch_wallet_created_at(self, address: str) -> int:
        return 0


class FakeAlertPort:
    def __init__(self):
        self.sent: list[str] = []

    def send(self, message: str) -> None:
        self.sent.append(message)


class FakeMarketRepo:
    def __init__(self):
        self._markets: list[dict] = []

    def get_watched(self) -> list[dict]:
        return list(self._markets)

    def add(self, market: dict) -> None:
        if not any(m["id"] == market["id"] for m in self._markets):
            self._markets.append(market)

    def remove(self, market_id: str) -> None:
        self._markets = [m for m in self._markets if m["id"] != market_id]


class FakeWalletRepo:
    def __init__(self):
        self._wallets: dict[str, WalletProfile] = {}

    def get(self, address: str) -> WalletProfile | None:
        return self._wallets.get(address)

    def save(self, wallet: WalletProfile, address: str) -> None:
        pass


assert isinstance(FakePolymarketPort(), PolymarketPort)
assert isinstance(FakeAlertPort(), AlertPort)
assert isinstance(FakeMarketRepo(), MarketRepo)
assert isinstance(FakeWalletRepo(), WalletRepo)


_INSIDER_PROFILE = WalletProfile(
    win_rate=0.72, n_markets=4, total_pnl=25_000.0,
    age_days=10, bias_up=0.6, total_trades=50,
)
_MACRO_MARKET = {"id": "mkt1", "question": "Will Trump win the 2024 election?", "yes_price": 0.45}


@pytest.fixture
def alert_port():
    return FakeAlertPort()


def test_insider_position_triggers_alert(alert_port):
    """인사이더 프로필 지갑의 신규 포지션 → TG 알림 발송"""
    wallet_addr = "0xinside"
    poly = FakePolymarketPort()
    poly._positions["mkt1"] = [Position(wallet_addr, "Yes", 0.45, 2_000.0)]

    wallet_repo = FakeWalletRepo()
    wallet_repo._wallets[wallet_addr] = _INSIDER_PROFILE

    market_repo = FakeMarketRepo()
    market_repo.add(_MACRO_MARKET)

    monitor = PositionMonitor(poly, alert_port, market_repo, wallet_repo)
    monitor.run_once()

    assert len(alert_port.sent) == 1
    assert wallet_addr in alert_port.sent[0]


def test_unknown_wallet_no_alert(alert_port):
    """알 수 없는 지갑의 소액 포지션 → 알림 없음"""
    poly = FakePolymarketPort()
    poly._positions["mkt1"] = [Position("0xunknown", "Yes", 0.45, 500.0)]  # below min

    market_repo = FakeMarketRepo()
    market_repo.add(_MACRO_MARKET)

    monitor = PositionMonitor(poly, alert_port, market_repo, FakeWalletRepo())
    monitor.run_once()

    assert alert_port.sent == []


def test_price_spike_triggers_alert(alert_port):
    """가격 임계값 이상 이동 → 알림 발송"""
    poly = FakePolymarketPort()
    poly._positions["mkt1"] = []

    market_repo = FakeMarketRepo()
    market_repo.add({**_MACRO_MARKET, "yes_price": 0.45})

    config = SignalConfig(price_alert_delta=0.04)
    monitor = PositionMonitor(poly, alert_port, market_repo, FakeWalletRepo(), config=config)
    # first tick: no prev price
    monitor.run_once()
    assert alert_port.sent == []

    # update market price → spike
    market_repo._markets[0]["yes_price"] = 0.50
    monitor.run_once()

    assert len(alert_port.sent) == 1
    assert "PRICE SPIKE" in alert_port.sent[0]


def test_new_macro_market_added_to_watchlist():
    """스캔에서 신규 매크로 마켓 발견 → watched_markets 추가"""
    poly = FakePolymarketPort()
    poly._markets = [
        {"id": "mkt-new", "question": "Federal Reserve rate cut in September?",
         "active": True, "closed": False, "yes_price": 0.4},
    ]
    market_repo = FakeMarketRepo()

    scanner = MarketScanService(poly, market_repo)
    scanner.run_once()

    watched = market_repo.get_watched()
    assert len(watched) == 1
    assert watched[0]["id"] == "mkt-new"


def test_whale_unknown_triggers_alert(alert_port):
    """고래 미지 지갑 (>= whale_min_usd) → 알림"""
    wallet_addr = "0xwhale_new"
    poly = FakePolymarketPort()
    poly._positions["mkt1"] = [Position(wallet_addr, "Yes", 0.45, 60_000.0)]

    market_repo = FakeMarketRepo()
    market_repo.add(_MACRO_MARKET)

    monitor = PositionMonitor(poly, alert_port, market_repo, FakeWalletRepo(),
                              whale_min_usd=50_000.0)
    monitor.run_once()

    assert len(alert_port.sent) == 1
    assert wallet_addr[:10] in alert_port.sent[0]
    assert "❓" in alert_port.sent[0]


def test_small_unknown_no_alert(alert_port):
    """소액 미지 지갑 → 알림 없음"""
    poly = FakePolymarketPort()
    poly._positions["mkt1"] = [Position("0xsmall", "Yes", 0.45, 3_000.0)]

    market_repo = FakeMarketRepo()
    market_repo.add(_MACRO_MARKET)

    monitor = PositionMonitor(poly, alert_port, market_repo, FakeWalletRepo(),
                              whale_min_usd=50_000.0)
    monitor.run_once()

    assert alert_port.sent == []


def test_expired_market_removed_from_watchlist():
    """마감된 마켓 → watched_markets 제거"""
    poly = FakePolymarketPort()
    poly._markets = [
        {"id": "mkt-old", "question": "Will inflation exceed 3%?",
         "active": False, "closed": True, "yes_price": 0.0},
    ]
    market_repo = FakeMarketRepo()
    market_repo.add({"id": "mkt-old", "question": "Will inflation exceed 3%?"})

    scanner = MarketScanService(poly, market_repo)
    scanner.run_once()

    assert market_repo.get_watched() == []

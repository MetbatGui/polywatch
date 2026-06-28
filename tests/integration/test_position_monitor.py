"""통합 테스트: 포지션 스냅샷 → 시그널 감지 → 알림 발송"""
import pytest

from src.application.ports import AlertPort, MarketRepo, PolymarketPort, WalletRepo
from src.domain.signal_detector import Position
from src.domain.wallet import WalletProfile


class FakePolymarketPort:
    def fetch_active_markets(self) -> list[dict]:
        return []

    def fetch_positions(self, market_id: str) -> list[Position]:
        return []

    def fetch_wallet_history(self, address: str) -> list[dict]:
        return []


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
        self._markets.append(market)

    def remove(self, market_id: str) -> None:
        self._markets = [m for m in self._markets if m.get("id") != market_id]


class FakeWalletRepo:
    def __init__(self):
        self._wallets: dict[str, WalletProfile] = {}

    def get(self, address: str) -> WalletProfile | None:
        return self._wallets.get(address)

    def save(self, wallet: WalletProfile) -> None:
        pass


assert isinstance(FakePolymarketPort(), PolymarketPort)
assert isinstance(FakeAlertPort(), AlertPort)
assert isinstance(FakeMarketRepo(), MarketRepo)
assert isinstance(FakeWalletRepo(), WalletRepo)


@pytest.fixture
def alert_port():
    return FakeAlertPort()


def test_insider_position_triggers_alert(alert_port):
    """인사이더 프로필 지갑의 신규 포지션 → TG 알림 발송"""
    # stub: PositionMonitor 구현 후 채워짐
    pass


def test_unknown_wallet_no_alert(alert_port):
    """일반 지갑 소액 포지션 → 알림 없음"""
    pass


def test_price_spike_triggers_alert(alert_port):
    """가격 임계값 이상 이동 → 알림 발송"""
    pass


def test_new_macro_market_added_to_watchlist():
    """스캔에서 신규 매크로 마켓 발견 → watched_markets 추가"""
    pass


def test_expired_market_removed_from_watchlist():
    """마감된 마켓 → watched_markets 제거"""
    pass

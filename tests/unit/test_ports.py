"""Port Protocol 단위 테스트 — 런타임 체크 가능 여부 검증"""
from src.application.ports import AlertPort, MarketRepo, PolymarketPort, WalletRepo


class _FakePolymarket:
    def fetch_active_markets(self) -> list:
        return []

    def fetch_positions(self, market_id: str) -> list:
        return []

    def fetch_wallet_history(self, address: str) -> list:
        return []


class _FakeAlert:
    def send(self, message: str) -> None:
        pass


class _FakeMarketRepo:
    def get_watched(self) -> list:
        return []

    def add(self, market) -> None:
        pass

    def remove(self, market_id: str) -> None:
        pass


class _FakeWalletRepo:
    def get(self, address: str):
        return None

    def save(self, wallet, address: str) -> None:
        pass


def test_polymarket_port_protocol():
    assert isinstance(_FakePolymarket(), PolymarketPort)


def test_alert_port_protocol():
    assert isinstance(_FakeAlert(), AlertPort)


def test_market_repo_protocol():
    assert isinstance(_FakeMarketRepo(), MarketRepo)


def test_wallet_repo_protocol():
    assert isinstance(_FakeWalletRepo(), WalletRepo)

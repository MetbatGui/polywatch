"""Outbound port interfaces (driven ports) — implemented by infrastructure adapters."""
from typing import Protocol, runtime_checkable

from src.domain.signal_detector import Position
from src.domain.wallet import WalletProfile


@runtime_checkable
class PolymarketPort(Protocol):
    def fetch_active_markets(self) -> list[dict]: ...
    def fetch_positions(self, market_id: str) -> list[Position]: ...
    def fetch_wallet_history(self, address: str) -> list[dict]: ...


@runtime_checkable
class AlertPort(Protocol):
    def send(self, message: str) -> None: ...


@runtime_checkable
class MarketRepo(Protocol):
    def get_watched(self) -> list[dict]: ...
    def add(self, market: dict) -> None: ...
    def remove(self, market_id: str) -> None: ...


@runtime_checkable
class WalletRepo(Protocol):
    def get(self, address: str) -> WalletProfile | None: ...
    def save(self, wallet: WalletProfile, address: str) -> None: ...

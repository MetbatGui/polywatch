"""SQLite repo 단위 테스트 — in-memory DB"""
import sqlite3

import pytest

from src.domain.wallet import WalletProfile
from src.infrastructure.sqlite_repos import SQLiteMarketRepo, SQLiteWalletRepo


@pytest.fixture
def market_repo():
    conn = sqlite3.connect(":memory:")
    repo = SQLiteMarketRepo(conn)
    repo.init_schema()
    return repo


@pytest.fixture
def wallet_repo():
    conn = sqlite3.connect(":memory:")
    repo = SQLiteWalletRepo(conn)
    repo.init_schema()
    return repo


def test_market_repo_add_and_get(market_repo):
    market_repo.add({"id": "mkt1", "question": "Will X?", "yes_price": 0.45})
    watched = market_repo.get_watched()
    assert len(watched) == 1
    assert watched[0]["id"] == "mkt1"
    assert watched[0]["yes_price"] == pytest.approx(0.45)


def test_market_repo_add_idempotent(market_repo):
    m = {"id": "mkt1", "question": "Will X?", "yes_price": 0.45}
    market_repo.add(m)
    market_repo.add(m)
    assert len(market_repo.get_watched()) == 1


def test_market_repo_remove(market_repo):
    market_repo.add({"id": "mkt1", "question": "Will X?", "yes_price": 0.4})
    market_repo.add({"id": "mkt2", "question": "Will Y?", "yes_price": 0.6})
    market_repo.remove("mkt1")
    watched = market_repo.get_watched()
    assert len(watched) == 1
    assert watched[0]["id"] == "mkt2"


def test_wallet_repo_save_and_get(wallet_repo):
    p = WalletProfile(win_rate=0.75, n_markets=5, total_pnl=30_000.0,
                      age_days=10, bias_up=0.6, total_trades=50)
    wallet_repo.save(p, address="0xabc")
    retrieved = wallet_repo.get("0xabc")
    assert retrieved is not None
    assert retrieved.win_rate == pytest.approx(0.75)
    assert retrieved.total_pnl == pytest.approx(30_000.0)


def test_wallet_repo_get_missing_returns_none(wallet_repo):
    assert wallet_repo.get("0xmissing") is None


def test_wallet_repo_save_overwrites(wallet_repo):
    p1 = WalletProfile(win_rate=0.5, n_markets=2, total_pnl=1000.0,
                       age_days=5, bias_up=0.5, total_trades=10)
    p2 = WalletProfile(win_rate=0.8, n_markets=3, total_pnl=9000.0,
                       age_days=20, bias_up=0.55, total_trades=30)
    wallet_repo.save(p1, address="0xabc")
    wallet_repo.save(p2, address="0xabc")
    retrieved = wallet_repo.get("0xabc")
    assert retrieved.win_rate == pytest.approx(0.8)

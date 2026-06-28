"""실제 SQLite DB와 애플리케이션 서비스 통합 테스트"""
import sqlite3
import pytest

from src.application.market_scan import MarketScanService
from src.application.position_monitor import PositionMonitor
from src.infrastructure.sqlite_repos import SQLiteMarketRepo, SQLiteWalletRepo
from src.domain.signal_detector import Position
from tests.integration.test_position_monitor import FakePolymarketPort, FakeAlertPort


def test_sqlite_integration_flow():
    # 1. 실제 SQLite DB 연결 및 스키마 초기화
    conn = sqlite3.connect(":memory:")
    market_repo = SQLiteMarketRepo(conn)
    wallet_repo = SQLiteWalletRepo(conn)
    market_repo.init_schema()
    wallet_repo.init_schema()

    import time
    poly = FakePolymarketPort()
    # 10일 전 타임스탬프를 반환하도록 모킹하여 age_days=10 조건으로 INSIDER 분류를 받도록 함
    poly.fetch_wallet_created_at = lambda addr: int(time.time()) - 10 * 86400
    alert = FakeAlertPort()

    # 2. 신규 마켓 추가 시나리오
    poly._markets = [
        {"id": "mkt-real-db", "question": "Is interest rate cut happening?",
         "active": True, "closed": False, "yes_price": 0.45}
    ]

    scanner = MarketScanService(poly, market_repo)
    scanner.run_once()

    # 실제 DB에 마켓이 삽입되었는지 검증
    watched = market_repo.get_watched()
    assert len(watched) == 1
    assert watched[0]["id"] == "mkt-real-db"

    # 3. PositionMonitor 통합 감시 흐름
    monitor = PositionMonitor(poly, alert, market_repo, wallet_repo)
    monitor.run_once()  # warmup tick

    # 신규 포지션 진입 시뮬레이션
    wallet_addr = "0xreal_user"
    poly._positions["mkt-real-db"] = [Position(wallet_addr, "Yes", 0.45, 10000.0)]
    
    # 지갑 히스토리를 통해 INSIDER로 분류되도록 데이터 세팅
    # age_days=10 (<90), n_markets=1 (<=3), total_trades=2 (<=5) -> INSIDER
    poly._wallet_history[wallet_addr] = [
        {"conditionId": "mkt-real-db", "outcome": "Yes", "cashPnl": 500.0, "avgPrice": 0.45},
        {"conditionId": "mkt-real-db", "outcome": "Yes", "cashPnl": 500.0, "avgPrice": 0.45},
    ]

    monitor.run_once()

    # 정상 검증 (Green state): 텔레그램 알림 1건 발송 검증
    assert len(alert.sent) == 1
    assert "0xreal_user" in alert.sent[0]

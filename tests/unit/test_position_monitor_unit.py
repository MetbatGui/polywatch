"""PositionMonitor 세부 비즈니스 로직 단위 테스트"""
import pytest
from src.application.position_monitor import PositionMonitor
from src.domain.signal_detector import Position
from src.domain.wallet import WalletProfile, Classification
from tests.integration.test_position_monitor import (
    FakePolymarketPort, FakeAlertPort, FakeMarketRepo, FakeWalletRepo
)


def test_wallet_api_error_isolation():
    """특정 지갑 조회 API가 에러를 던지더라도 다른 지갑들의 알림 처리가 정상 진행되는지 검증"""
    poly = FakePolymarketPort()
    alert = FakeAlertPort()
    market_repo = FakeMarketRepo()
    wallet_repo = FakeWalletRepo()

    market_repo.add({"id": "mkt1", "question": "Will X?", "yes_price": 0.5})

    monitor = PositionMonitor(poly, alert, market_repo, wallet_repo,
                              whale_min_usd=10000.0)
    monitor.run_once()  # warmup

    # 두 지갑의 신규 진입 포지션 설정 (둘 다 whale_min_usd 초과하여 알림 대상)
    poly._positions["mkt1"] = [
        Position("0xwallet_error", "Yes", 0.5, 20000.0),
        Position("0xwallet_ok", "Yes", 0.5, 30000.0),
    ]

    # 0xwallet_error 조회 시 예외 발생하도록 설정
    def raise_error_for_bad_wallet(address):
        if address == "0xwallet_error":
            raise Exception("API Connection Failed")
        return []

    poly.fetch_wallet_history = raise_error_for_bad_wallet

    # 모니터 실행
    # (에러 격리가 없다면 여기서 예외가 위로 터져서 테스트가 크래시되거나,
    #  ok 지갑에 대한 알림 메시지조차 생성되지 못하고 0개의 알림이 가게 됨)
    monitor.run_once()

    # Red 상태 유도: 에러가 격리되어 0xwallet_ok에 대한 알림이 1건 발송되어야 함
    # 하지만 현재 코드는 예외를 캐치하지 않으므로 크래시나 에러가 전파됨.
    assert len(alert.sent) == 1
    assert "0xwallet_ok" in alert.sent[0]
    # 에러가 발생한 지갑도 폴백 프로필로 처리되어 알림에 포함되어야 함
    assert "0xwallet_error" in alert.sent[0]


def test_top_n_sort_limit():
    """동시에 다수 지갑 진입 시 _TOP_N=3 에 따라 가치가 높은 순으로 정렬되고 3개로 제한되는지 검증"""
    poly = FakePolymarketPort()
    alert = FakeAlertPort()
    market_repo = FakeMarketRepo()
    wallet_repo = FakeWalletRepo()

    market_repo.add({"id": "mkt1", "question": "Will X?", "yes_price": 0.5})

    # UNKNOWN 지갑들도 알림 대상이 되도록 whale_min_usd=10000.0 으로 설정
    monitor = PositionMonitor(poly, alert, market_repo, wallet_repo,
                              whale_min_usd=10000.0)
    monitor.run_once()  # warmup

    # 4개의 지갑이 다 다른 가치로 신규 진입
    poly._positions["mkt1"] = [
        Position("0xwallet_10k", "Yes", 0.5, 10000.0),
        Position("0xwallet_40k", "Yes", 0.5, 40000.0),
        Position("0xwallet_30k", "Yes", 0.5, 30000.0),
        Position("0xwallet_20k", "Yes", 0.5, 20000.0),
    ]

    monitor.run_once()

    assert len(alert.sent) == 1
    msg = alert.sent[0]
    
    # 40k, 30k, 20k 순으로 노출되어야 하고, 10k는 탈락해야 함
    assert "0xwallet_40k" in msg
    assert "0xwallet_30k" in msg
    assert "0xwallet_20k" in msg
    assert "0xwallet_10k" not in msg

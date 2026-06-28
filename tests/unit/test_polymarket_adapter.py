"""PolymarketAdapter 단위 테스트 — requests 모킹"""
import pytest

from src.infrastructure.polymarket_adapter import PolymarketAdapter


def _mock_get(mocker, payload):
    resp = mocker.Mock()
    resp.json.return_value = payload
    resp.raise_for_status = mocker.Mock()
    mocker.patch("requests.get", return_value=resp)
    return resp


def test_fetch_active_markets_maps_fields(mocker):
    _mock_get(mocker, [
        {"conditionId": "0xabc", "question": "Will X happen?",
         "outcomePrices": '["0.45","0.55"]', "active": True, "closed": False},
    ])
    markets = PolymarketAdapter().fetch_active_markets()
    assert len(markets) == 1
    m = markets[0]
    assert m["id"] == "0xabc"
    assert m["question"] == "Will X happen?"
    assert m["yes_price"] == pytest.approx(0.45)
    assert m["active"] is True
    assert m["closed"] is False


def test_fetch_active_markets_outcome_prices_as_list(mocker):
    """API가 outcomePrices를 이미 list로 반환하는 경우"""
    _mock_get(mocker, [
        {"conditionId": "0xabc", "question": "Will X?",
         "outcomePrices": ["0.35", "0.65"], "active": True, "closed": False},
    ])
    markets = PolymarketAdapter().fetch_active_markets()
    assert markets[0]["yes_price"] == pytest.approx(0.35)


def test_fetch_positions_maps_to_position_objects(mocker):
    _mock_get(mocker, [
        {"positions": [
            {"proxyWallet": "0xwallet", "outcome": "Yes",
             "avgPrice": 0.42, "currentValue": 2500.0, "name": "Trader1"},
        ]}
    ])
    from src.domain.signal_detector import Position
    positions = PolymarketAdapter().fetch_positions("0xabc")
    assert len(positions) == 1
    p = positions[0]
    assert isinstance(p, Position)
    assert p.wallet == "0xwallet"
    assert p.outcome == "Yes"
    assert p.avg_price == pytest.approx(0.42)
    assert p.current_value == pytest.approx(2500.0)
    assert p.name == "Trader1"


def test_fetch_positions_empty_response(mocker):
    _mock_get(mocker, [])
    assert PolymarketAdapter().fetch_positions("0xnone") == []


def test_fetch_wallet_history_returns_list(mocker):
    _mock_get(mocker, [{"type": "BUY", "amount": 1000}])
    history = PolymarketAdapter().fetch_wallet_history("0xwallet")
    assert isinstance(history, list)
    assert history[0]["type"] == "BUY"


def test_fetch_active_markets_broken_outcome_prices(mocker):
    """outcomePrices가 깨진 포맷일 경우 yes_price가 0.0으로 복구되는지 검증"""
    _mock_get(mocker, [
        {"conditionId": "0xabc", "question": "Will X?",
         "outcomePrices": "invalid-json", "active": True, "closed": False},
        {"conditionId": "0xdef", "question": "Will Y?",
         "outcomePrices": [], "active": True, "closed": False},
        {"conditionId": "0xghi", "question": "Will Z?",
         "outcomePrices": None, "active": True, "closed": False},
    ])
    markets = PolymarketAdapter().fetch_active_markets()
    assert len(markets) == 3
    assert markets[0]["yes_price"] == pytest.approx(0.0)
    assert markets[1]["yes_price"] == pytest.approx(0.0)
    assert markets[2]["yes_price"] == pytest.approx(0.0)


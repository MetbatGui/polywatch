import json

import requests

from src.domain.signal_detector import Position

_GAMMA = "https://gamma-api.polymarket.com"
_DATA = "https://data-api.polymarket.com"


class PolymarketAdapter:
    def fetch_active_markets(self) -> list[dict]:
        resp = requests.get(
            f"{_GAMMA}/markets",
            params={"limit": 100, "order": "volume24hr", "ascending": "false", "active": "true"},
            timeout=10,
        )
        resp.raise_for_status()
        return [self._map_market(m) for m in resp.json()]

    def fetch_positions(self, market_id: str) -> list[Position]:
        resp = requests.get(
            f"{_DATA}/v1/market-positions",
            params={"market": market_id, "sortBy": "TOKENS", "status": "OPEN"},
            timeout=10,
        )
        resp.raise_for_status()
        positions: list[Position] = []
        for entry in resp.json():
            for pos in entry.get("positions", []):
                positions.append(Position(
                    wallet=pos.get("proxyWallet") or pos.get("user", ""),
                    outcome=pos.get("outcome", ""),
                    avg_price=float(pos.get("avgPrice", 0)),
                    current_value=float(pos.get("currentValue", 0)),
                ))
        return positions

    def fetch_wallet_history(self, address: str) -> list[dict]:
        resp = requests.get(
            f"{_DATA}/v1/positions",
            params={"user": address, "sizeThreshold": "0.01", "limit": 500},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _map_market(m: dict) -> dict:
        prices_raw = m.get("outcomePrices", '["0","1"]')
        try:
            prices = prices_raw if isinstance(prices_raw, list) else json.loads(prices_raw)
            yes_price = float(prices[0])
        except (json.JSONDecodeError, IndexError, TypeError, ValueError):
            yes_price = 0.0
        return {
            "id": m.get("conditionId", ""),
            "question": m.get("question", ""),
            "yes_price": yes_price,
            "active": m.get("active", False),
            "closed": m.get("closed", False),
        }

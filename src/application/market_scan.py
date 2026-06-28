from src.application.ports import MarketRepo, PolymarketPort
from src.domain.market_filter import MarketFilter


class MarketScanService:
    def __init__(self, polymarket: PolymarketPort, market_repo: MarketRepo) -> None:
        self._poly = polymarket
        self._markets = market_repo

    def run_once(self) -> None:
        active = self._poly.fetch_active_markets()
        active_ids = {m["id"] for m in active if not m.get("closed")}

        # remove closed/expired from watchlist
        for m in self._markets.get_watched():
            if m["id"] not in active_ids:
                self._markets.remove(m["id"])

        # add new macro markets
        watched_ids = {m["id"] for m in self._markets.get_watched()}
        for m in active:
            if m.get("closed"):
                continue
            if m["id"] not in watched_ids and MarketFilter.is_macro(m.get("question", "")):
                self._markets.add(m)

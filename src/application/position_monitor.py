from src.application.ports import AlertPort, MarketRepo, PolymarketPort, WalletRepo
from src.domain.signal_detector import SignalConfig, SignalDetector, SignalType
from src.domain.wallet import Classification
from src.domain.wallet_classifier import WalletClassifier


class PositionMonitor:
    def __init__(
        self,
        polymarket: PolymarketPort,
        alert: AlertPort,
        market_repo: MarketRepo,
        wallet_repo: WalletRepo,
        config: SignalConfig = SignalConfig(),
    ) -> None:
        self._poly = polymarket
        self._alert = alert
        self._markets = market_repo
        self._wallets = wallet_repo
        self._config = config
        # market_id → {wallet → Position}
        self._prev_snapshots: dict[str, dict] = {}
        self._prev_prices: dict[str, float] = {}

    def run_once(self) -> None:
        for market in self._markets.get_watched():
            market_id = market["id"]
            yes_price = float(market.get("yes_price", 0.0))

            positions = self._poly.fetch_positions(market_id)
            curr = {p.wallet: p for p in positions}
            prev = self._prev_snapshots.get(market_id, {})
            prev_price = self._prev_prices.get(market_id)

            signals = SignalDetector.detect(
                prev=prev, curr=curr,
                yes_price=yes_price,
                prev_yes_price=prev_price,
                config=self._config,
            )

            for signal in signals:
                if signal.type == SignalType.PRICE_SPIKE:
                    self._alert.send(
                        f"[PRICE_SPIKE] {market['question']} | yes={signal.yes_price:.2f}"
                    )
                else:
                    profile = self._wallets.get(signal.wallet)
                    if profile is None:
                        continue
                    if WalletClassifier.classify(profile) == Classification.INSIDER:
                        self._alert.send(
                            f"[{signal.type.name}] wallet={signal.wallet}"
                            f" outcome={signal.outcome} val={signal.current_value:.0f}"
                            f" price={signal.avg_price:.2f}"
                        )

            self._prev_snapshots[market_id] = curr
            self._prev_prices[market_id] = yes_price

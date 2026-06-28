from src.application.ports import AlertPort, MarketRepo, PolymarketPort, WalletRepo
from src.domain.signal_detector import Signal, SignalConfig, SignalDetector, SignalType
from src.domain.wallet import Classification
from src.domain.wallet_classifier import WalletClassifier
from src.domain.wallet_profiler import WalletProfiler


class PositionMonitor:
    def __init__(
        self,
        polymarket: PolymarketPort,
        alert: AlertPort,
        market_repo: MarketRepo,
        wallet_repo: WalletRepo,
        config: SignalConfig = SignalConfig(),
        explore: bool = True,
    ) -> None:
        self._poly = polymarket
        self._alert = alert
        self._markets = market_repo
        self._wallets = wallet_repo
        self._config = config
        self._explore = explore
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

            if signals:
                msg = self._build_market_message(market, signals, yes_price)
                if msg:
                    self._alert.send(msg)

            self._prev_snapshots[market_id] = curr
            self._prev_prices[market_id] = yes_price

    def _classify_wallet(self, address: str) -> Classification:
        profile = self._wallets.get(address)
        if profile is None:
            history = self._poly.fetch_wallet_history(address)
            profile = WalletProfiler.from_history(history)
            self._wallets.save(profile, address)
        return WalletClassifier.classify(profile)

    def _build_market_message(
        self, market: dict, signals: list[Signal], yes_price: float
    ) -> str:
        lines: list[str] = [
            f"[{market['question']}]",
            f"yes={yes_price:.3f}",
        ]

        price_spikes = [s for s in signals if s.type == SignalType.PRICE_SPIKE]
        pos_signals = [s for s in signals if s.type != SignalType.PRICE_SPIKE]

        if price_spikes:
            lines.append(f"PRICE_SPIKE → yes={price_spikes[0].yes_price:.3f}")

        if pos_signals:
            entries: list[str] = []
            for sig in sorted(pos_signals, key=lambda s: -s.current_value):
                label = self._classify_wallet(sig.wallet)
                if label == Classification.INSIDER or self._explore:
                    tag = label.name
                    entries.append(
                        f"  [{tag}] {sig.wallet}  {sig.outcome}"
                        f"  ${sig.current_value:,.0f}  @{sig.avg_price:.3f}"
                    )
            if entries:
                lines.append(f"\n포지션 ({len(entries)}):")
                lines.extend(entries)

        # only send if there's more than just the header + price line
        has_content = price_spikes or any(
            s.type != SignalType.PRICE_SPIKE for s in signals
        )
        if has_content and len(lines) > 2:
            return "\n".join(lines)
        return ""

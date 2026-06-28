from datetime import datetime, timezone

from src.application.ports import AlertPort, MarketRepo, PolymarketPort, WalletRepo
from src.domain.signal_detector import Signal, SignalConfig, SignalDetector, SignalType
from src.domain.wallet import Classification
from src.domain.wallet_classifier import WalletClassifier
from src.domain.wallet_profiler import WalletProfiler

_TOP_N = 3


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
        # cache: wallet → created_at epoch
        self._created_cache: dict[str, int] = {}

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
                total_value = sum(p.current_value for p in curr.values())
                msg = self._build_market_message(market, signals, yes_price, curr, total_value)
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

    def _created_date(self, address: str) -> str:
        if address not in self._created_cache:
            ts = self._poly.fetch_wallet_created_at(address)
            self._created_cache[address] = ts
        ts = self._created_cache[address]
        if not ts:
            return "?"
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")

    def _build_market_message(
        self,
        market: dict,
        signals: list[Signal],
        yes_price: float,
        curr_positions: dict,
        total_value: float,
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
            # label + filter
            labeled: list[tuple[Signal, Classification]] = []
            for sig in pos_signals:
                label = self._classify_wallet(sig.wallet)
                if label == Classification.INSIDER or self._explore:
                    labeled.append((sig, label))

            # top N by value
            top = sorted(labeled, key=lambda x: -x[0].current_value)[:_TOP_N]

            if top:
                lines.append(f"\n상위 {len(top)}개 포지션:")
                for sig, label in top:
                    pos = curr_positions.get(sig.wallet)
                    display_name = (pos.name or sig.wallet[:10]) if pos else sig.wallet[:10]
                    share = (sig.current_value / total_value * 100) if total_value else 0
                    created = self._created_date(sig.wallet)
                    lines.append(
                        f"  [{label.name}] {display_name}"
                        f"  {sig.outcome}  ${sig.current_value:,.0f} ({share:.0f}%)"
                        f"  가입 {created}"
                    )

        if len(lines) > 2:
            return "\n".join(lines)
        return ""

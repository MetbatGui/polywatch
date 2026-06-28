import dataclasses
from datetime import datetime, timezone

from src.application.ports import AlertPort, MarketRepo, PolymarketPort, WalletRepo
from src.domain.signal_detector import Signal, SignalConfig, SignalDetector, SignalType
from src.domain.wallet import Classification
from src.domain.wallet_classifier import WalletClassifier
from src.domain.wallet_profiler import WalletProfiler

_TOP_N = 3

_LABEL_EMOJI = {
    "INSIDER":    "🎯",
    "EXPERT":     "🧠",
    "UNKNOWN":    "❓",
    "GAMBLER":    "🎲",
    "AMM_BOT":    "🤖",
    "ARBITRAGER": "⚡",
}


class PositionMonitor:
    def __init__(
        self,
        polymarket: PolymarketPort,
        alert: AlertPort,
        market_repo: MarketRepo,
        wallet_repo: WalletRepo,
        config: SignalConfig = SignalConfig(),
        whale_min_usd: float = 50_000.0,
    ) -> None:
        self._poly = polymarket
        self._alert = alert
        self._markets = market_repo
        self._wallets = wallet_repo
        self._config = config
        self._whale_min_usd = whale_min_usd
        self._prev_snapshots: dict[str, dict] = {}
        self._prev_prices: dict[str, float] = {}
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

    def _is_notable(self, sig: Signal, label: Classification) -> bool:
        if label == Classification.INSIDER:
            return True
        if label in (Classification.GAMBLER, Classification.AMM_BOT):
            return False
        if sig.type == SignalType.POSITION_INCREASE:
            return True
        return sig.current_value >= self._whale_min_usd

    def _resolve_wallet(self, address: str) -> tuple[Classification, int]:
        """Returns (classification, active_bets_count)."""
        profile = self._wallets.get(address)
        if profile is None:
            history = self._poly.fetch_wallet_history(address)
            profile = WalletProfiler.from_history(history)
            age = self._fetch_age_days(address)
            profile = dataclasses.replace(profile, age_days=age)
            self._wallets.save(profile, address)
        return WalletClassifier.classify(profile), profile.n_markets

    def _fetch_age_days(self, address: str) -> int:
        if address not in self._created_cache:
            ts = self._poly.fetch_wallet_created_at(address)
            self._created_cache[address] = ts
        ts = self._created_cache[address]
        if not ts:
            return 9999
        return (datetime.now(tz=timezone.utc) - datetime.fromtimestamp(ts, tz=timezone.utc)).days

    def _age_days(self, address: str) -> str:
        days = self._fetch_age_days(address)
        return "?" if days == 9999 else f"{days}일"

    def _build_market_message(
        self,
        market: dict,
        signals: list[Signal],
        yes_price: float,
        curr_positions: dict,
        total_value: float,
    ) -> str:
        price_spikes = [s for s in signals if s.type == SignalType.PRICE_SPIKE]
        pos_signals = [s for s in signals if s.type != SignalType.PRICE_SPIKE]

        question = market["question"]
        sep = "━" * 28

        if price_spikes:
            return (
                f"⚡ <b>PRICE SPIKE</b>\n"
                f"{sep}\n"
                f"<b>{question}</b>\n"
                f"💹 yes → <b>{yes_price:.3f}</b>"
            )

        if not pos_signals:
            return ""

        labeled: list[tuple[Signal, Classification, int]] = []
        for sig in pos_signals:
            label, n_bets = self._resolve_wallet(sig.wallet)
            if self._is_notable(sig, label):
                labeled.append((sig, label, n_bets))

        top = sorted(labeled, key=lambda x: -x[0].current_value)[:_TOP_N]
        if not top:
            return ""

        has_insider = any(lbl == Classification.INSIDER for _, lbl, _ in top)
        header_icon = "🚨" if has_insider else "📊"
        sig_type = pos_signals[0].type.name.replace("_", " ")

        lines = [
            f"{header_icon} <b>{question}</b>",
            f"{sep}",
            f"💲 yes = <b>{yes_price:.3f}</b>  ·  <i>{sig_type}</i>",
            "",
        ]

        rank_emoji = ["1️⃣", "2️⃣", "3️⃣"]
        for i, (sig, label, n_bets) in enumerate(top):
            pos = curr_positions.get(sig.wallet)
            name = (pos.name or sig.wallet[:14]) if pos else sig.wallet[:14]
            share = (sig.current_value / total_value * 100) if total_value else 0
            age = self._age_days(sig.wallet)
            tag = _LABEL_EMOJI.get(label.name, "❓")
            outcome_icon = "🟢" if sig.outcome == "Yes" else "🔴"
            lines += [
                f"{rank_emoji[i]} {tag} <b>{name}</b>  {outcome_icon} {sig.outcome}",
                f"   💵 <b>${sig.current_value:,.0f}</b>  ·  {share:.0f}%"
                f"  ·  🎰 {n_bets}건  ·  👤 {age}",
                "",
            ]

        return "\n".join(lines).rstrip()

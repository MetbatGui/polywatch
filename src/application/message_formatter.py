from dataclasses import dataclass

from src.domain.wallet import Classification, WalletProfile

_LABEL_EMOJI = {
    "INSIDER":    "🎯",
    "EXPERT":     "🧠",
    "UNKNOWN":    "❓",
    "GAMBLER":    "🎲",
    "AMM_BOT":    "🤖",
    "ARBITRAGER": "⚡",
}

_SEP = "━" * 28
_RANK = ["1️⃣", "2️⃣", "3️⃣"]


@dataclass
class WalletEntry:
    name: str
    label: Classification
    profile: WalletProfile
    outcome: str
    current_value: float
    share_pct: float
    age_days: int


class MessageFormatter:
    @staticmethod
    def price_spike(question: str, yes_price: float) -> str:
        return (
            f"⚡ <b>PRICE SPIKE</b>  <b>{question}</b>\n"
            f"💹 yes → <b>{yes_price:.3f}</b>"
        )

    @staticmethod
    def position_alert(
        question: str,
        yes_price: float,
        sig_type: str,
        entries: list[WalletEntry],
    ) -> str:
        has_insider = any(e.label == Classification.INSIDER for e in entries)
        header = "🚨" if has_insider else "📊"

        lines = [
            f"{header} <b>{question}</b>",
            f"💲 yes <b>{yes_price:.3f}</b>  ·  <i>{sig_type}</i>",
            _SEP,
        ]

        for i, e in enumerate(entries):
            outcome_icon = "🟢" if e.outcome == "Yes" else "🔴"
            tag = _LABEL_EMOJI.get(e.label.name, "❓")
            age = "?" if e.age_days == 9999 else f"{e.age_days}d"
            lines += [
                f"{_RANK[i]} {tag} <b>{e.name}</b>",
                f"   {outcome_icon} {e.outcome}  "
                f"<b>${e.current_value:,.0f}</b>  ({e.share_pct:.0f}%)",
                f"   📈 승률 <b>{e.profile.win_rate * 100:.0f}%</b>"
                f"  ·  🗂 {e.profile.n_markets}건",
                f"   🕐 {age}",
                "",
            ]

        return "\n".join(lines).rstrip()

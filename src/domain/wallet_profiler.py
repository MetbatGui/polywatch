from datetime import datetime, timezone

from src.domain.wallet import WalletProfile


class WalletProfiler:
    @staticmethod
    def from_history(activity: list[dict]) -> WalletProfile:
        if not activity:
            return WalletProfile(win_rate=0.5, n_markets=0, total_pnl=0.0,
                                 age_days=0, bias_up=0.5, total_trades=0)

        total_trades = len(activity)

        market_ids = {a.get("market") or a.get("conditionId", "") for a in activity}
        n_markets = len(market_ids - {""})

        buy_trades = [a for a in activity if a.get("side") == "BUY"]
        yes_buys = sum(1 for a in buy_trades if a.get("outcome", "") in ("Yes", "Up"))
        bias_up = yes_buys / len(buy_trades) if buy_trades else 0.5

        total_pnl = sum(float(a.get("cashPnl") or a.get("profitLoss") or 0) for a in activity)

        sell_trades = [a for a in activity if a.get("side") == "SELL"]
        profitable = sum(
            1 for a in sell_trades
            if float(a.get("cashPnl") or a.get("profitLoss") or 0) > 0
        )
        win_rate = profitable / len(sell_trades) if sell_trades else 0.5

        timestamps = [a.get("timestamp") or a.get("createdAt") for a in activity]
        timestamps = [t for t in timestamps if t]
        age_days = 0
        if timestamps:
            oldest = min(timestamps)
            if isinstance(oldest, (int, float)):
                first_dt = datetime.fromtimestamp(float(oldest), tz=timezone.utc)
            else:
                first_dt = datetime.fromisoformat(str(oldest).replace("Z", "+00:00"))
            age_days = (datetime.now(tz=timezone.utc) - first_dt).days

        return WalletProfile(
            win_rate=win_rate,
            n_markets=n_markets,
            total_pnl=total_pnl,
            age_days=age_days,
            bias_up=bias_up,
            total_trades=total_trades,
        )

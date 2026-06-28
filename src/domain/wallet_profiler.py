"""positions 응답에서 WalletProfile 계산.

positions 필드: conditionId, cashPnl, outcome, size, avgPrice, curPrice
"""
from src.domain.wallet import WalletProfile


class WalletProfiler:
    @staticmethod
    def from_history(positions: list[dict]) -> WalletProfile:
        if not positions:
            return WalletProfile(win_rate=0.5, n_markets=0, total_pnl=0.0,
                                 age_days=0, bias_up=0.5, total_trades=0)

        total_trades = len(positions)
        n_markets = len({p.get("conditionId", "") for p in positions} - {""})

        yes_count = sum(1 for p in positions if p.get("outcome", "") in ("Yes", "Up"))
        bias_up = yes_count / total_trades

        total_pnl = sum(float(p.get("cashPnl") or 0) for p in positions)

        profitable = sum(1 for p in positions if float(p.get("cashPnl") or 0) > 0)
        win_rate = profitable / total_trades

        return WalletProfile(
            win_rate=win_rate,
            n_markets=n_markets,
            total_pnl=total_pnl,
            age_days=0,  # positions API에 타임스탬프 없음
            bias_up=bias_up,
            total_trades=total_trades,
        )

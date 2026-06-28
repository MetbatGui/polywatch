from dataclasses import dataclass
from enum import Enum, auto


class Classification(Enum):
    INSIDER = auto()
    EXPERT = auto()
    AMM_BOT = auto()
    ARBITRAGER = auto()
    GAMBLER = auto()
    UNKNOWN = auto()


@dataclass(frozen=True)
class WalletProfile:
    win_rate: float
    n_markets: int
    total_pnl: float
    age_days: int
    bias_up: float
    total_trades: int

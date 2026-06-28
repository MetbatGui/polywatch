from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class SignalType(Enum):
    NEW_POSITION = auto()
    POSITION_INCREASE = auto()
    PRICE_SPIKE = auto()


@dataclass(frozen=True)
class SignalConfig:
    min_position_usd: float = 1_000.0
    uncertain_low: float = 0.2
    uncertain_high: float = 0.7
    price_alert_delta: float = 0.04
    position_increase_ratio: float = 1.5
    position_increase_min_usd: float = 500.0


@dataclass
class Signal:
    type: SignalType
    wallet: str = ""
    outcome: str = ""
    avg_price: float = 0.0
    current_value: float = 0.0
    yes_price: float = 0.0


class SignalDetector:
    @staticmethod
    def detect(
        prev: dict[str, Any],
        curr: dict[str, Any],
        yes_price: float = 0.0,
        prev_yes_price: float | None = None,
        config: SignalConfig = SignalConfig(),
    ) -> list[Signal]:
        signals: list[Signal] = []

        # 가격 급변
        if prev_yes_price is not None:
            if abs(yes_price - prev_yes_price) >= config.price_alert_delta:
                signals.append(Signal(type=SignalType.PRICE_SPIKE, yes_price=yes_price))

        for wallet, pos in curr.items():
            val = pos.current_value
            avg = pos.avg_price
            outcome = pos.outcome

            if val < config.min_position_usd:
                continue

            # 불확실 구간 체크 (Yes: avg 직접, No: 1-avg)
            effective_avg = avg if outcome == "Yes" else 1.0 - avg
            if not (config.uncertain_low <= effective_avg <= config.uncertain_high):
                continue

            prev_pos = prev.get(wallet)

            if prev_pos is None:
                signals.append(Signal(
                    type=SignalType.NEW_POSITION,
                    wallet=wallet, outcome=outcome,
                    avg_price=avg, current_value=val, yes_price=yes_price,
                ))
            else:
                prev_val = prev_pos.current_value
                increased = (
                    val >= prev_val * config.position_increase_ratio
                    and val - prev_val >= config.position_increase_min_usd
                )
                if increased:
                    signals.append(Signal(
                        type=SignalType.POSITION_INCREASE,
                        wallet=wallet, outcome=outcome,
                        avg_price=avg, current_value=val, yes_price=yes_price,
                    ))

        return signals

"""SignalDetector Domain Service 단위 테스트"""
from dataclasses import dataclass

import pytest

from src.domain.signal_detector import SignalDetector, SignalConfig, SignalType


@dataclass(frozen=True)
class PositionSnapshot:
    wallet: str
    outcome: str
    avg_price: float
    current_value: float


DEFAULT_CONFIG = SignalConfig(
    min_position_usd=1_000.0,
    uncertain_low=0.2,
    uncertain_high=0.7,
    price_alert_delta=0.04,
    position_increase_ratio=1.5,
    position_increase_min_usd=500.0,
)


def test_no_signals_when_nothing_changed():
    snap = {"w1": PositionSnapshot("w1", "Yes", 0.5, 2_000.0)}
    signals = SignalDetector.detect(prev=snap, curr=snap, yes_price=0.5, config=DEFAULT_CONFIG)
    assert signals == []


def test_new_large_position_in_uncertain_zone_emits_signal():
    prev = {}
    curr = {"w1": PositionSnapshot("w1", "Yes", 0.45, 2_000.0)}
    signals = SignalDetector.detect(prev=prev, curr=curr, yes_price=0.55, config=DEFAULT_CONFIG)
    assert len(signals) == 1
    assert signals[0].type == SignalType.NEW_POSITION
    assert signals[0].wallet == "w1"


def test_small_position_ignored():
    prev = {}
    curr = {"w1": PositionSnapshot("w1", "Yes", 0.45, 500.0)}
    signals = SignalDetector.detect(prev=prev, curr=curr, yes_price=0.55, config=DEFAULT_CONFIG)
    assert signals == []


def test_position_outside_uncertain_zone_ignored():
    prev = {}
    curr = {"w1": PositionSnapshot("w1", "Yes", 0.05, 5_000.0)}
    signals = SignalDetector.detect(prev=prev, curr=curr, yes_price=0.55, config=DEFAULT_CONFIG)
    assert signals == []


def test_price_spike_emits_signal():
    signals = SignalDetector.detect(
        prev={}, curr={},
        yes_price=0.65, prev_yes_price=0.60,
        config=DEFAULT_CONFIG,
    )
    assert len(signals) == 1
    assert signals[0].type == SignalType.PRICE_SPIKE


def test_price_change_below_threshold_no_signal():
    signals = SignalDetector.detect(
        prev={}, curr={},
        yes_price=0.62, prev_yes_price=0.60,
        config=DEFAULT_CONFIG,
    )
    assert signals == []


def test_position_increase_emits_signal():
    prev = {"w1": PositionSnapshot("w1", "Yes", 0.45, 1_000.0)}
    curr = {"w1": PositionSnapshot("w1", "Yes", 0.45, 2_000.0)}
    signals = SignalDetector.detect(prev=prev, curr=curr, yes_price=0.55, config=DEFAULT_CONFIG)
    assert len(signals) == 1
    assert signals[0].type == SignalType.POSITION_INCREASE

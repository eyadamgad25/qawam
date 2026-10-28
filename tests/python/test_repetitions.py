from __future__ import annotations

import math

import pytest

from qawam_ml.repetitions import RepCounter


def test_counts_only_completed_low_high_low_cycles() -> None:
    counter = RepCounter(low_threshold=30, high_threshold=90)
    observations = [110, 30, 60, 90, 75, 30, 25, 90, 30]
    assert [counter.update(value) for value in observations] == [
        0,
        0,
        0,
        0,
        0,
        1,
        1,
        1,
        2,
    ]


def test_missing_observation_does_not_advance_or_reset_state() -> None:
    counter = RepCounter(low_threshold=20, high_threshold=80)
    assert counter.update(20) == 0
    assert counter.update(80) == 0
    assert counter.update(None) == 0
    assert counter.update(20) == 1


def test_repeated_samples_in_a_phase_count_only_once_per_cycle() -> None:
    counter = RepCounter(low_threshold=20, high_threshold=80)
    for value in [20, 20, 90, 90, 90, 20, 20]:
        counter.update(value)
    assert counter.count == 1


def test_reset_clears_count_and_requires_start_phase_again() -> None:
    counter = RepCounter(low_threshold=20, high_threshold=80)
    for value in [20, 80, 20]:
        counter.update(value)
    counter.reset()
    assert counter.count == 0
    assert counter.update(80) == 0
    assert counter.update(20) == 0
    assert counter.update(80) == 0
    assert counter.update(20) == 1


@pytest.mark.parametrize(
    ("low", "high"),
    [
        (30, 30),
        (40, 20),
        (math.nan, 80),
        (20, math.inf),
        (True, 80),
    ],
)
def test_invalid_thresholds_raise_value_error(
    low: object, high: object
) -> None:
    with pytest.raises(ValueError):
        RepCounter(low, high)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [math.nan, -math.inf, math.inf, "bad"])
def test_invalid_observation_raises_value_error(value: object) -> None:
    counter = RepCounter(low_threshold=20, high_threshold=80)
    with pytest.raises(ValueError, match="angle"):
        counter.update(value)  # type: ignore[arg-type]

from __future__ import annotations

import math
import sys

import pytest

from qawam_ml.smoothing import moving_average


def test_moving_average_is_causal_and_preserves_length() -> None:
    assert moving_average([10, 20, 30, 40], 3) == pytest.approx([10, 15, 20, 30])


def test_moving_average_warmup_and_window_larger_than_input() -> None:
    assert moving_average([2, 4], 5) == pytest.approx([2, 3])


def test_moving_average_empty_input() -> None:
    assert moving_average([], 2) == []


@pytest.mark.parametrize("window_size", [0, -1, 1.5, True])
def test_invalid_window_size_raises_value_error(window_size: object) -> None:
    with pytest.raises(ValueError, match="window_size"):
        moving_average([1, 2], window_size)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, "bad"])
def test_invalid_sample_raises_value_error(value: object) -> None:
    with pytest.raises(ValueError, match=r"values\[1\]"):
        moving_average([1, value, 3], 2)  # type: ignore[list-item]


def test_large_finite_samples_do_not_overflow_while_averaging() -> None:
    largest = sys.float_info.max
    assert moving_average([largest, largest], 2) == pytest.approx([largest, largest])

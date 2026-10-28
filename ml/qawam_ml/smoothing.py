"""Causal signal-smoothing helpers with no exercise-specific parameters."""

from __future__ import annotations

import math
from collections.abc import Sequence


def moving_average(values: Sequence[float], window_size: int) -> list[float]:
    """Return a trailing moving average with the same length as ``values``.

    During warm-up, each output averages all available preceding values. The
    trailing window is causal: it never uses future samples.
    """
    if isinstance(window_size, bool) or not isinstance(window_size, int) or window_size <= 0:
        raise ValueError("window_size must be a positive integer")

    samples = [_finite_value(value, index) for index, value in enumerate(values)]
    return [
        math.fsum(value / (index - start + 1) for value in samples[start : index + 1])
        for index, start in (
            (index, max(0, index - window_size + 1))
            for index in range(len(samples))
        )
    ]


def _finite_value(value: float, index: int) -> float:
    try:
        sample = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"values[{index}] must be numeric") from exc
    if not math.isfinite(sample):
        raise ValueError(f"values[{index}] must be finite")
    return sample

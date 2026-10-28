"""Compare one repetition's angle curve with a physio-recorded reference.

Dynamic time warping (DTW) aligns the two curves so a slower or faster rep
is compared shape-for-shape. Outputs are descriptive metrics in degrees and
ratios; deciding what counts as "too different" is a per-patient tolerance
set by the physiotherapist, never a constant in this module.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class RepComparison:
    rom_rep_deg: float
    rom_reference_deg: float
    rom_ratio: float
    peak_difference_deg: float
    tempo_ratio: float
    dtw_mean_abs_deg: float
    path_length: int


def _curve(values: Sequence[float], name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or array.size < 2:
        raise ValueError(f"{name} must be a 1-D sequence of at least 2 samples")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be finite; let the confidence gate abstain on gaps")
    return array


def dtw_path(
    a: Sequence[float],
    b: Sequence[float],
    window: int | None = None,
) -> tuple[float, list[tuple[int, int]]]:
    """Classic DTW with absolute difference cost and an optional Sakoe-Chiba band.

    Returns the total cost and the optimal warping path as (i, j) pairs.
    """
    x, y = _curve(a, "a"), _curve(b, "b")
    n, m = x.size, y.size
    band = max(window if window is not None else max(n, m), abs(n - m))
    cost = np.full((n + 1, m + 1), np.inf)
    cost[0, 0] = 0.0
    for i in range(1, n + 1):
        lo, hi = max(1, i - band), min(m, i + band)
        for j in range(lo, hi + 1):
            step = abs(x[i - 1] - y[j - 1])
            cost[i, j] = step + min(cost[i - 1, j], cost[i, j - 1], cost[i - 1, j - 1])
    path: list[tuple[int, int]] = []
    i, j = n, m
    while i > 0 and j > 0:
        path.append((i - 1, j - 1))
        moves = (cost[i - 1, j - 1], cost[i - 1, j], cost[i, j - 1])
        best = int(np.argmin(moves))
        if best == 0:
            i, j = i - 1, j - 1
        elif best == 1:
            i -= 1
        else:
            j -= 1
    path.reverse()
    return float(cost[n, m]), path


def compare_to_reference(
    rep: Sequence[float],
    reference: Sequence[float],
    window: int | None = None,
) -> RepComparison:
    """Metrics for one rep against the reference rep (same angle, same units)."""
    x, y = _curve(rep, "rep"), _curve(reference, "reference")
    total, path = dtw_path(x, y, window)
    rom_rep = float(x.max() - x.min())
    rom_ref = float(y.max() - y.min())
    return RepComparison(
        rom_rep_deg=rom_rep,
        rom_reference_deg=rom_ref,
        rom_ratio=rom_rep / rom_ref if rom_ref > 0 else math.nan,
        peak_difference_deg=float(x.max() - y.max()),
        tempo_ratio=x.size / y.size,
        dtw_mean_abs_deg=total / len(path),
        path_length=len(path),
    )


def symmetry_index(involved: float, uninvolved: float) -> float:
    """100 * involved / uninvolved (e.g. range of motion of the injured side)."""
    if not math.isfinite(involved) or not math.isfinite(uninvolved):
        raise ValueError("values must be finite")
    if uninvolved <= 0:
        raise ValueError("uninvolved side value must be positive")
    return 100.0 * involved / uninvolved

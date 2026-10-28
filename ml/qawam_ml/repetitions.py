"""Configurable repetition-counting state machine without clinical defaults."""

from __future__ import annotations

import math


class RepCounter:
    """Count completed low-to-high-to-low cycles using caller-supplied bounds.

    A cycle starts only after observing ``angle <= low_threshold``, reaches
    its high phase at ``angle >= high_threshold``, and counts on return to the
    low phase. ``None`` represents an unavailable observation and leaves state
    unchanged.
    """

    def __init__(self, low_threshold: float, high_threshold: float) -> None:
        self._low_threshold = _finite_threshold(low_threshold, "low_threshold")
        self._high_threshold = _finite_threshold(high_threshold, "high_threshold")
        if self._low_threshold >= self._high_threshold:
            raise ValueError("low_threshold must be less than high_threshold")
        self.reset()

    @property
    def count(self) -> int:
        """Number of completed cycles since initialization or reset."""
        return self._count

    def update(self, angle: float | None) -> int:
        """Consume one angle observation and return the completed count."""
        if angle is None:
            return self._count
        value = _finite_threshold(angle, "angle")

        if self._phase == "seek_low":
            if value <= self._low_threshold:
                self._phase = "ready"
        elif self._phase == "ready":
            if value >= self._high_threshold:
                self._phase = "seek_return"
        elif value <= self._low_threshold:
            self._count += 1
            self._phase = "ready"

        return self._count

    def reset(self) -> None:
        """Clear the count and require a new low-phase observation."""
        self._count = 0
        self.reset_cycle()

    def reset_cycle(self) -> None:
        """Discard a partial cycle while retaining completed repetitions."""
        self._phase = "seek_low"


def _finite_threshold(value: float, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number")
    return result

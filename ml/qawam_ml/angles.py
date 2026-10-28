"""Pure two-dimensional geometry helpers; no exercise or clinical thresholds."""

from __future__ import annotations

import math
from collections.abc import Sequence

Point2D = Sequence[float]


def angle_degrees(point_a: Point2D, vertex: Point2D, point_c: Point2D) -> float | None:
    """Return the smaller in-plane angle at ``vertex`` in degrees.

    Returns ``None`` when either arm has zero length, because the angle is
    undefined. Each point must contain two finite numeric coordinates.
    """
    ax, ay = _point(point_a, "point_a")
    vx, vy = _point(vertex, "vertex")
    cx, cy = _point(point_c, "point_c")

    arm_a_x, arm_a_y = ax - vx, ay - vy
    arm_c_x, arm_c_y = cx - vx, cy - vy
    if not all(
        math.isfinite(value)
        for value in (arm_a_x, arm_a_y, arm_c_x, arm_c_y)
    ):
        raise ValueError("coordinate differences must be finite")
    length_a = math.hypot(arm_a_x, arm_a_y)
    length_c = math.hypot(arm_c_x, arm_c_y)
    if not math.isfinite(length_a) or not math.isfinite(length_c):
        raise ValueError("arm lengths must be finite")
    if length_a == 0 or length_c == 0:
        return None

    unit_a_x, unit_a_y = arm_a_x / length_a, arm_a_y / length_a
    unit_c_x, unit_c_y = arm_c_x / length_c, arm_c_y / length_c
    cross = unit_a_x * unit_c_y - unit_a_y * unit_c_x
    dot = unit_a_x * unit_c_x + unit_a_y * unit_c_y
    return math.degrees(math.atan2(abs(cross), dot))


def _point(point: Point2D, name: str) -> tuple[float, float]:
    if len(point) != 2:
        raise ValueError(f"{name} must contain exactly two coordinates")
    try:
        x, y = float(point[0]), float(point[1])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} coordinates must be numeric") from exc
    if not math.isfinite(x) or not math.isfinite(y):
        raise ValueError(f"{name} coordinates must be finite")
    return x, y

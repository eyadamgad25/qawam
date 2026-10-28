from __future__ import annotations

import math
import sys

import pytest

from qawam_ml.angles import angle_degrees


@pytest.mark.parametrize(
    ("point_a", "vertex", "point_c", "expected"),
    [
        ((1, 0), (0, 0), (0, 1), 90.0),
        ((-1, 0), (0, 0), (1, 0), 180.0),
        ((1, 0), (0, 0), (2, 0), 0.0),
        ((1, 1), (0, 0), (-1, -1), 180.0),
    ],
)
def test_angle_degrees_known_geometries(
    point_a: tuple[int, int],
    vertex: tuple[int, int],
    point_c: tuple[int, int],
    expected: float,
) -> None:
    assert angle_degrees(point_a, vertex, point_c) == pytest.approx(expected)


def test_angle_is_invariant_to_translation_and_uniform_scale() -> None:
    angle = angle_degrees((2, 1), (1, 1), (1, 4))
    transformed = angle_degrees((14, 12), (10, 12), (10, 24))
    assert transformed == pytest.approx(angle)


@pytest.mark.parametrize(
    ("point_a", "vertex", "point_c"),
    [
        ((0, 0), (0, 0), (1, 0)),
        ((1, 0), (0, 0), (0, 0)),
    ],
)
def test_degenerate_arm_returns_none(
    point_a: tuple[int, int],
    vertex: tuple[int, int],
    point_c: tuple[int, int],
) -> None:
    assert angle_degrees(point_a, vertex, point_c) is None


@pytest.mark.parametrize(
    ("point_a", "vertex", "point_c"),
    [
        ((1,), (0, 0), (0, 1)),
        ((1, 0), (0, 0), (0, 1, 2)),
        ((math.nan, 0), (0, 0), (0, 1)),
        ((1, 0), (0, math.inf), (0, 1)),
        (("x", 0), (0, 0), (0, 1)),
        ((sys.float_info.max, 0), (-sys.float_info.max, 0), (0, 1)),
    ],
)
def test_invalid_points_raise_value_error(
    point_a: tuple[object, ...],
    vertex: tuple[object, ...],
    point_c: tuple[object, ...],
) -> None:
    with pytest.raises(ValueError):
        angle_degrees(point_a, vertex, point_c)  # type: ignore[arg-type]

"""Row-level REHAB24-6 quality and camera-view helpers. Standard library only."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, TypeVar

Row = TypeVar("Row")

FILTER_NAMES = frozenset({"none", "gt_quality", "label_quality"})
CAMERAS = frozenset({17, 18})


def _field(row: Any, name: str) -> Any:
    if isinstance(row, Mapping):
        return row[name]
    return getattr(row, name)


def _int_field(row: Any, name: str) -> int:
    return int(_field(row, name))


def _camera(cam: int) -> int:
    camera = int(cam)
    if camera not in CAMERAS:
        raise ValueError(f"cam must be 17 or 18, got {cam!r}")
    return camera


def gt_quality(row: Any, cam: int) -> bool:
    """mocap_erroneous==0 and lights_on==1 and extra_person_in_cam{cam}==0."""
    camera = _camera(cam)
    extra = f"extra_person_in_cam{camera}"
    return (
        _int_field(row, "mocap_erroneous") == 0
        and _int_field(row, "lights_on") == 1
        and _int_field(row, extra) == 0
    )


def label_quality(row: Any, cam: int) -> bool:
    """lights_on==1 and extra_person_in_cam{cam}==0 (ignores mocap_erroneous)."""
    camera = _camera(cam)
    extra = f"extra_person_in_cam{camera}"
    return _int_field(row, "lights_on") == 1 and _int_field(row, extra) == 0


def apply_filter(rows: Iterable[Row], name: str, cam: int) -> list[Row]:
    """Keep rows matching none | gt_quality | label_quality for one camera."""
    if name not in FILTER_NAMES:
        raise ValueError(f"unknown filter {name!r}; expected one of {sorted(FILTER_NAMES)}")
    items = list(rows)
    if name == "none":
        _camera(cam)
        return items
    predicate = gt_quality if name == "gt_quality" else label_quality
    return [row for row in items if predicate(row, cam)]


def view_for_camera(cam17_orientation: str, cam: int) -> str:
    """Camera17 keeps the CSV view; Camera18 swaps front<->profile.

    ``side`` is normalized to ``profile`` before the swap. ``half-profile``
    is unchanged for both cameras.
    """
    camera = _camera(cam)
    view = str(cam17_orientation).strip().lower()
    if view == "side":
        view = "profile"
    if camera == 17:
        return view
    if view == "front":
        return "profile"
    if view == "profile":
        return "front"
    return view

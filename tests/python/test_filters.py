from __future__ import annotations

import pytest

from qawam_ml.filters import apply_filter, gt_quality, label_quality, view_for_camera


def _row(
    *,
    mocap_erroneous: int = 0,
    lights_on: int = 1,
    extra17: int = 0,
    extra18: int = 0,
) -> dict[str, int]:
    return {
        "mocap_erroneous": mocap_erroneous,
        "lights_on": lights_on,
        "extra_person_in_cam17": extra17,
        "extra_person_in_cam18": extra18,
    }


def test_gt_quality_requires_mocap_lights_and_cam_extra() -> None:
    good = _row()
    assert gt_quality(good, 17) is True
    assert gt_quality(good, 18) is True
    assert gt_quality(_row(mocap_erroneous=1), 17) is False
    assert gt_quality(_row(lights_on=0), 17) is False
    assert gt_quality(_row(extra17=1), 17) is False
    assert gt_quality(_row(extra17=1), 18) is True
    assert gt_quality(_row(extra18=2), 18) is False
    assert gt_quality(_row(extra18=2), 17) is True


def test_label_quality_ignores_mocap_erroneous() -> None:
    dirty_mocap = _row(mocap_erroneous=1)
    assert label_quality(dirty_mocap, 17) is True
    assert gt_quality(dirty_mocap, 17) is False
    assert label_quality(_row(lights_on=0), 17) is False
    assert label_quality(_row(extra18=1), 18) is False
    assert label_quality(_row(extra18=1), 17) is True


def test_apply_filter_names_none_gt_and_label() -> None:
    rows = [
        _row(),
        _row(mocap_erroneous=1),
        _row(lights_on=0),
        _row(extra17=3),
    ]
    assert len(apply_filter(rows, "none", 17)) == 4
    gt17 = apply_filter(rows, "gt_quality", 17)
    assert gt17 == [rows[0]]
    label17 = apply_filter(rows, "label_quality", 17)
    assert label17 == [rows[0], rows[1]]


def test_apply_filter_rejects_unknown_name() -> None:
    with pytest.raises(ValueError, match="unknown filter"):
        apply_filter([], "clean", 17)


def test_view_for_camera_swaps_front_profile_and_normalizes_side() -> None:
    assert view_for_camera("front", 17) == "front"
    assert view_for_camera("front", 18) == "profile"
    assert view_for_camera("profile", 17) == "profile"
    assert view_for_camera("profile", 18) == "front"
    assert view_for_camera("half-profile", 17) == "half-profile"
    assert view_for_camera("half-profile", 18) == "half-profile"
    assert view_for_camera("side", 17) == "profile"
    assert view_for_camera("side", 18) == "front"
    assert view_for_camera(" SIDE ", 17) == "profile"

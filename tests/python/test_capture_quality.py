from __future__ import annotations

import math

import pytest

from qawam_ml.capture_quality import assess_capture_quality


def test_all_required_landmarks_above_cutoff_are_ready_for_analysis() -> None:
    result = assess_capture_quality(
        ["hip", "knee", "ankle"],
        {"hip": 0.9, "knee": 0.8, "ankle": 0.7, "nose": 0.1},
        min_visibility=0.7,
    )
    assert result.status == "READY_FOR_ANALYSIS"
    assert result.reason_codes == ()
    assert result.failed_landmarks == ()


def test_visibility_equal_to_cutoff_passes() -> None:
    result = assess_capture_quality(["knee"], {"knee": 0.7}, min_visibility=0.7)
    assert result.status == "READY_FOR_ANALYSIS"


def test_missing_and_low_visibility_landmarks_return_reason_codes() -> None:
    result = assess_capture_quality(
        ["hip", "knee", "ankle"],
        {"hip": 0.4, "knee": None},
        min_visibility=0.7,
    )
    assert result.status == "CANNOT_ASSESS"
    assert result.reason_codes == (
        "REQUIRED_LANDMARK_MISSING",
        "LOW_REQUIRED_LANDMARK_VISIBILITY",
    )
    assert result.failed_landmarks == ("knee", "ankle", "hip")


@pytest.mark.parametrize(
    ("required", "visibility", "cutoff"),
    [
        ([], {}, 0.5),
        (["hip", "hip"], {"hip": 1.0}, 0.5),
        ([""], {"": 1.0}, 0.5),
        (["hip"], {"hip": 0.5}, math.nan),
        (["hip"], {"hip": 0.5}, math.inf),
        (["hip"], {"hip": 1.1}, 0.5),
        (["hip"], {"hip": -0.1}, 0.5),
        (["hip"], {"hip": math.nan}, 0.5),
        (["hip"], {"hip": math.inf}, 0.5),
        (["hip"], {"hip": True}, 0.5),
        (["hip"], {"hip": "uncertain"}, 0.5),
    ],
)
def test_invalid_configuration_or_visibility_raises_value_error(
    required: list[str],
    visibility: dict[str, object],
    cutoff: object,
) -> None:
    with pytest.raises(ValueError):
        assess_capture_quality(required, visibility, cutoff)  # type: ignore[arg-type]

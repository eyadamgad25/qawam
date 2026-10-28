from __future__ import annotations

import math

import pytest

from qawam_ml.angle_pipeline import AngleRepPipeline

LANDMARKS = ("a", "vertex", "c")
VISIBLE = {"a": 0.9, "vertex": 0.9, "c": 0.9}


def frame_for_angle(degrees: float) -> dict[str, tuple[float, float]]:
    radians = math.radians(degrees)
    return {
        "a": (0.0, 0.0),
        "vertex": (0.0, 1.0),
        "c": (math.sin(radians), 1.0 - math.cos(radians)),
    }


def make_pipeline(window: int = 1) -> AngleRepPipeline:
    return AngleRepPipeline(
        required_landmarks=LANDMARKS,
        angle_landmarks=LANDMARKS,
        min_visibility=0.5,
        smoothing_window=window,
        low_threshold=30,
        high_threshold=70,
    )


def test_pipeline_computes_angle_smoothing_and_completed_rep() -> None:
    pipeline = make_pipeline()

    low = pipeline.update(frame_for_angle(20), VISIBLE)
    high = pipeline.update(frame_for_angle(80), VISIBLE)
    returned = pipeline.update(frame_for_angle(20), VISIBLE)

    assert low.angle_degrees == pytest.approx(20)
    assert high.smoothed_angle_degrees == pytest.approx(80)
    assert returned.repetition_count == 1
    assert returned.status == "READY_FOR_ANALYSIS"


def test_low_visibility_refuses_analysis_and_breaks_partial_cycle() -> None:
    pipeline = make_pipeline()
    pipeline.update(frame_for_angle(20), VISIBLE)
    pipeline.update(frame_for_angle(80), VISIBLE)

    result = pipeline.update(
        frame_for_angle(20), {**VISIBLE, "vertex": 0.1}
    )
    assert result.status == "CANNOT_ASSESS"
    assert result.reason_codes == ("LOW_REQUIRED_LANDMARK_VISIBILITY",)
    assert result.failed_landmarks == ("vertex",)
    assert result.repetition_count == 0

    pipeline.update(frame_for_angle(20), VISIBLE)
    pipeline.update(frame_for_angle(80), VISIBLE)
    assert pipeline.update(frame_for_angle(20), VISIBLE).repetition_count == 1


def test_missing_coordinates_cannot_pass_visibility_gate() -> None:
    pipeline = make_pipeline()
    coordinates = frame_for_angle(20)
    del coordinates["vertex"]

    result = pipeline.update(coordinates, VISIBLE)
    assert result.status == "CANNOT_ASSESS"
    assert result.reason_codes == ("REQUIRED_LANDMARK_MISSING",)
    assert result.failed_landmarks == ("vertex",)


def test_undefined_angle_refuses_and_breaks_cycle() -> None:
    pipeline = make_pipeline()
    pipeline.update(frame_for_angle(20), VISIBLE)
    pipeline.update(frame_for_angle(80), VISIBLE)
    collapsed = {"a": (0.0, 0.0), "vertex": (0.0, 0.0), "c": (0.0, 1.0)}

    result = pipeline.update(collapsed, VISIBLE)
    assert result.status == "CANNOT_ASSESS"
    assert result.reason_codes == ("ANGLE_UNDEFINED",)

    pipeline.update(frame_for_angle(20), VISIBLE)
    pipeline.update(frame_for_angle(80), VISIBLE)
    assert pipeline.update(frame_for_angle(20), VISIBLE).repetition_count == 1


def test_smoothing_window_is_applied_to_streamed_angles() -> None:
    pipeline = make_pipeline(window=2)
    pipeline.update(frame_for_angle(20), VISIBLE)
    result = pipeline.update(frame_for_angle(80), VISIBLE)
    assert result.angle_degrees == pytest.approx(80)
    assert result.smoothed_angle_degrees == pytest.approx(50)
    assert result.repetition_count == 0


def test_reset_clears_sequence_state() -> None:
    pipeline = make_pipeline()
    for angle in (20, 80, 20):
        pipeline.update(frame_for_angle(angle), VISIBLE)
    pipeline.reset()
    result = pipeline.update(frame_for_angle(80), VISIBLE)
    assert result.repetition_count == 0
    assert result.smoothed_angle_degrees == pytest.approx(80)


def test_pipeline_rejects_unknown_angle_landmark() -> None:
    with pytest.raises(ValueError, match="angle_landmarks"):
        AngleRepPipeline(
            required_landmarks=LANDMARKS,
            angle_landmarks=("a", "vertex", "other"),
            min_visibility=0.5,
            smoothing_window=1,
            low_threshold=30,
            high_threshold=70,
        )

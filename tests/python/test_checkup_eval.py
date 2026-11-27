"""Tests for ml/eval/checkup_eval.py: agreement statistics and conversion of both datasets to the app's frames."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ml" / "eval"))
import checkup_eval as c  # noqa: E402


def test_icc_is_one_for_identical_and_lower_for_an_offset():
    ref = np.array([8.0, 10.0, 12.5, 15.0, 20.0])
    assert abs(c.icc21(ref, ref) - 1.0) < 1e-12
    assert c.icc21(ref + 2.0, ref) < c.icc21(ref + 0.2, ref) < 1.0


def test_agreement_reports_bias_and_limits():
    ref = [8.0, 10.0, 12.0, 14.0, 16.0, 18.0]
    out = c.agreement([r + 0.5 for r in ref], ref, n_boot=50)
    assert out["bias_s"] == 0.5 and out["mae_s"] == 0.5
    assert out["limits_of_agreement_s"] == [0.5, 0.5]


def test_openpose_points_land_on_mediapipe_joints():
    points = np.zeros((2, 75))
    points[0, 9 * 3:9 * 3 + 3] = [100, 200, 0.9]  # right hip
    points[0, 14 * 3:14 * 3 + 3] = [50, 400, 0.8]  # left ankle
    frames = c.stanford_frames(points, 30.0, 500.0, 500.0)
    assert frames[0]["landmarks"][24] == {"x": 0.2, "y": 0.4, "visibility": 0.9}
    assert frames[0]["landmarks"][27]["visibility"] == 0.8
    assert frames[1]["landmarks"] is None and frames[1]["timeSeconds"] == 1 / 30


def _person(heights: list[float]) -> list[dict]:
    """Frames with only the left hip and ankle seen; height = hip above the ankle in pixels."""
    out = []
    for k, h in enumerate(heights):
        marks = c.empty_landmarks()
        marks[23] = {"x": 0.5, "y": (400 - h) / 480, "visibility": 0.9}
        marks[27] = {"x": 0.5, "y": 400 / 480, "visibility": 0.9}
        out.append({"timeSeconds": k / 30, "width": 640, "height": 480, "landmarks": marks})
    return out


def test_starts_standing_only_when_the_first_half_second_is_high():
    seated_first = [100.0] * 30 + [200.0] * 30 + [100.0] * 30
    standing_first = [200.0] * 30 + [100.0] * 30 + [200.0] * 30
    assert not c.starts_standing(_person(seated_first))
    assert c.starts_standing(_person(standing_first))


def test_count_exact_counts_stand_ups_between_the_marks_only():
    ref = {"a": (1.0, 10.0), "b": (1.0, 10.0)}
    ups = {"a": [2, 4, 6, 8, 9.5, 12], "b": [2, 4, 6, 8]}  # a: a 6th rise after the end is fine; b: one missed
    assert c.count_exact(ups, ref) == 0.5


def test_kinect_front_view_becomes_a_side_view_with_the_hip_above_the_ankle(tmp_path):
    folder = tmp_path / "skel"
    folder.mkdir()
    for k, z in enumerate((3.0, 2.5)):
        (folder / f"{63690937586078 + k * 33}.txt").write_text(
            f"HipLeft Tracked 0.1 0.0 {z} 1 1\nKneeLeft Tracked 0.1 -0.45 {z} 1 1\nAnkleLeft Inferred 0.1 -0.9 {z} 1 1\n",
            encoding="utf-8",
        )
    frames = c.kinecal_side_frames(c.read_kinecal(folder))
    hip, ankle = frames[0]["landmarks"][23], frames[0]["landmarks"][27]
    assert hip["y"] < ankle["y"] and ankle["visibility"] == 0.5
    assert frames[1]["landmarks"][23]["x"] < hip["x"]  # walking toward the camera moves across the side view
    assert abs(frames[1]["timeSeconds"] - 0.033) < 1e-9  # names are milliseconds

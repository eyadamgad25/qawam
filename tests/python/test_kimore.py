import math

import numpy as np
from qawam_ml.kimore import (
    J,
    body_yaw_deg,
    frontalness,
    joint_angle,
    plane_view,
    read_joint_csv,
    segment_reps,
    virtual_view,
)


def _skeleton(frames: int = 120, knee_deg: np.ndarray | None = None, yaw_deg: float = 0.0) -> np.ndarray:
    """Synthetic standing person facing the camera (Kinect axes: x right, y up, z away)."""
    xyz = np.zeros((frames, 25, 3))
    knee = np.zeros(frames) if knee_deg is None else knee_deg
    for side, x in (("left", -0.15), ("right", 0.15)):
        xyz[:, J[f"{side}_shoulder"]] = [x * 1.3, 0.5, 0]
        xyz[:, J[f"{side}_elbow"]] = [x * 1.4, 0.2, 0]
        xyz[:, J[f"{side}_hip"]] = [x, 0.0, 0]
        xyz[:, J[f"{side}_knee"]] = [x, -0.45, 0]
        flex = np.radians(knee)
        # shank swings backwards (+z away from the camera) in the sagittal plane
        xyz[:, J[f"{side}_ankle"], 0] = x
        xyz[:, J[f"{side}_ankle"], 1] = -0.45 - 0.45 * np.cos(flex)
        xyz[:, J[f"{side}_ankle"], 2] = 0.45 * np.sin(flex)
    xyz[:, J["spine_base"]] = [0, 0, 0]
    xyz[..., 2] += 3.0
    if yaw_deg:
        t = math.radians(yaw_deg)
        c, s = math.cos(t), math.sin(t)
        centre = xyz[:, J["spine_base"]][:, None, :].copy()
        p = xyz - centre
        x = c * p[..., 0] + s * p[..., 2]
        z = -s * p[..., 0] + c * p[..., 2]
        xyz = np.stack([x, p[..., 1], z], axis=-1) + centre
    return xyz


def test_side_view_reads_sagittal_knee_flexion_and_front_view_does_not():
    knee = 60 * (1 - np.cos(np.linspace(0, 6 * math.pi, 120))) / 2
    xyz = _skeleton(knee_deg=knee)
    truth = joint_angle(plane_view(xyz, "sagittal"), "knee_flexion", "left")
    side = joint_angle(virtual_view(xyz, 90), "knee_flexion", "left")
    front = joint_angle(virtual_view(xyz, 0), "knee_flexion", "left")
    assert np.max(np.abs(truth - knee)) < 1e-6
    assert np.max(np.abs(side - knee)) < 3.0
    # perspective leaks a little depth into the image, but most of the bend is invisible
    assert np.max(front) < 15.0


def test_virtual_view_removes_the_subjects_own_yaw():
    xyz = _skeleton(yaw_deg=25)
    assert abs(abs(body_yaw_deg(xyz)) - 25) < 1e-6
    assert np.median(frontalness(virtual_view(xyz, 0))) > 0.6
    assert np.median(frontalness(virtual_view(xyz, 90))) < 0.05


def test_segment_reps_counts_three_squats():
    knee = 60 * (1 - np.cos(np.linspace(0, 6 * math.pi, 180))) / 2
    assert len(segment_reps(knee)) == 3


def test_read_joint_csv_skips_empty_rows(tmp_path):
    row = ",".join(["0.1,0.2,3.0,2"] * 25)
    path = tmp_path / "JointPosition.csv"
    path.write_text(f"{row},\n\n{row},\n")
    xyz, tracked = read_joint_csv(path)
    assert xyz.shape == (2, 25, 3)
    assert np.all(tracked == 2)

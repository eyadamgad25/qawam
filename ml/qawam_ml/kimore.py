"""KIMORE loader and virtual-camera projection.

KIMORE (Capecci et al., IEEE TNSRE 2019) records patients and healthy people
with a Kinect v2 while they perform five low-back-pain rehab exercises, and
gives a clinician score per exercise. We use the 3D skeleton as ground truth
and project it into virtual phone cameras to ask a question the dataset was
not built for: how accurate is a *single 2D phone camera*, from which
placement, and does Qawam's view gate catch the bad placements?

Data stays local under ``data/raw/kimore`` (git-ignored). Only aggregate
numbers leave this module.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# Kinect v2 joint order (25 joints; each row: x, y, z, tracking state).
JOINTS = (
    "spine_base", "spine_mid", "neck", "head",
    "left_shoulder", "left_elbow", "left_wrist", "left_hand",
    "right_shoulder", "right_elbow", "right_wrist", "right_hand",
    "left_hip", "left_knee", "left_ankle", "left_foot",
    "right_hip", "right_knee", "right_ankle", "right_foot",
    "spine_shoulder", "left_hand_tip", "left_thumb", "right_hand_tip", "right_thumb",
)
J = {name: i for i, name in enumerate(JOINTS)}

GROUPS = {"Parkinson": "P", "Stroke": "S", "BackPain": "B", "Expert": "E", "NotExpert": "N"}


@dataclass(frozen=True)
class Recording:
    group: str
    subject: str
    exercise: int
    xyz: np.ndarray  # (frames, 25, 3) metres, camera coordinates
    tracked: np.ndarray  # (frames, 25) Kinect tracking state (2 tracked, 1 inferred)


def read_joint_csv(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Read one JointPosition CSV; rows the Kinect left empty are dropped."""
    rows: list[list[float]] = []
    for line in path.read_text().splitlines():
        parts = [p for p in line.strip().split(",") if p != ""]
        if len(parts) < 100:
            continue
        try:
            rows.append([float(p) for p in parts[:100]])
        except ValueError:
            continue
    if not rows:
        return np.zeros((0, 25, 3)), np.zeros((0, 25))
    data = np.asarray(rows).reshape(-1, 25, 4)
    return data[..., :3], data[..., 3]


def _pick_csv(raw: Path) -> Path | None:
    """Some folders hold a duplicate or an aborted take; keep the longest file."""
    files = sorted(
        (p for p in raw.glob("JointPosition*.csv") if "(" not in p.name),
        key=lambda p: p.stat().st_size,
        reverse=True,
    )
    return files[0] if files else None


def iter_recordings(root: Path, exercise: int | None = None) -> Iterator[Recording]:
    """Yield every recording under ``root`` (a folder holding GPP and/or CG)."""
    for es in sorted(root.rglob(f"Es{exercise if exercise else '*'}")):
        raw = es / "Raw"
        if not raw.is_dir():
            continue
        csv = _pick_csv(raw)
        if csv is None:
            continue
        subject = es.parent.name
        group = es.parent.parent.name
        xyz, tracked = read_joint_csv(csv)
        if len(xyz) < 30:
            continue
        yield Recording(group, subject, int(es.name[2:]), xyz, tracked)


def read_scores(root: Path) -> dict[str, dict[str, float]]:
    """Clinical scores per subject: TS (total, 0-50), PO (0-15), CF (0-35) per exercise."""
    import pandas as pd

    scores: dict[str, dict[str, float]] = {}
    for path in root.rglob("ClinicalAssessment_*.xlsx"):
        subject = re.sub(r"^ClinicalAssessment_", "", path.stem)
        if subject in scores:
            continue
        frame = pd.read_excel(path)
        row = frame.iloc[0]
        values: dict[str, float] = {}
        for column in frame.columns:
            match = re.match(r"clinical (TS|PO|CF) Ex#(\d)", str(column))
            if match and row[column] == row[column]:
                values[f"{match.group(1)}{match.group(2)}"] = float(row[column])
        scores[subject] = values
    return scores


# ---------------------------------------------------------------- geometry


def interior_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray:
    """Angle ABC in degrees for arrays of 2D or 3D points (last axis = coords)."""
    u, v = a - b, c - b
    nu, nv = np.linalg.norm(u, axis=-1), np.linalg.norm(v, axis=-1)
    cos = np.sum(u * v, axis=-1) / np.maximum(nu * nv, 1e-9)
    return np.degrees(np.arccos(np.clip(cos, -1.0, 1.0)))


def body_yaw_deg(xyz: np.ndarray) -> float:
    """Median direction the subject faces, relative to the Kinect (0 = facing it).

    The shoulder line's angle in the floor (x-z) plane; 0 when the shoulders are
    parallel to the image plane.
    """
    d = xyz[:, J["right_shoulder"]] - xyz[:, J["left_shoulder"]]
    return float(np.degrees(np.median(np.arctan2(d[:, 2], d[:, 0]))))


def virtual_view(xyz: np.ndarray, yaw_deg: float, distance_m: float = 2.5,
                 pitch_deg: float = 0.0) -> np.ndarray:
    """Project the skeleton into a pinhole camera placed at ``yaw_deg`` around the subject.

    The skeleton is first turned to face the camera squarely (removing the
    subject's own yaw), so ``yaw_deg = 0`` is a true front view and 90 a true
    side view. The camera sits ``distance_m`` from the pelvis at chest height,
    optionally tilted by ``pitch_deg`` (phone propped low and looking up is
    positive). Returns (frames, 25, 2) image-plane coordinates, y pointing down.
    """
    centre = np.median(xyz[:, J["spine_base"]], axis=0)
    p = xyz - centre
    total = math.radians(yaw_deg - body_yaw_deg(xyz))
    c, s = math.cos(total), math.sin(total)
    x = c * p[..., 0] - s * p[..., 2]
    z = s * p[..., 0] + c * p[..., 2]
    y = p[..., 1] - 0.25  # camera at roughly chest height above the pelvis
    if pitch_deg:
        cp, sp = math.cos(math.radians(pitch_deg)), math.sin(math.radians(pitch_deg))
        y, z = cp * y - sp * z, sp * y + cp * z
    depth = distance_m + z
    return np.stack([x / depth, -y / depth], axis=-1)


def plane_view(xyz: np.ndarray, plane: str) -> np.ndarray:
    """Goniometer ground truth: the body-aligned skeleton projected orthographically
    onto an anatomical plane ("sagittal" or "frontal").

    A clinician measures shoulder flexion in the sagittal plane and abduction in
    the frontal plane; the raw 3D interior angle mixes the two (an arm hanging
    slightly out to the side already reads ~30°), so it is not the right target.
    """
    p = xyz - np.median(xyz[:, J["spine_base"]], axis=0)
    t = math.radians(-body_yaw_deg(xyz))
    c, s = math.cos(t), math.sin(t)
    x = c * p[..., 0] - s * p[..., 2]
    z = s * p[..., 0] + c * p[..., 2]
    horizontal = z if plane == "sagittal" else x
    return np.stack([horizontal, -p[..., 1]], axis=-1)


def frontalness(points2d: np.ndarray) -> np.ndarray:
    """Qawam's view feature: |shoulder x gap| / torso length (same as the web gate)."""
    ls, rs = points2d[:, J["left_shoulder"]], points2d[:, J["right_shoulder"]]
    lh, rh = points2d[:, J["left_hip"]], points2d[:, J["right_hip"]]
    torso = np.linalg.norm((ls + rs) / 2 - (lh + rh) / 2, axis=-1)
    return np.abs(ls[:, 0] - rs[:, 0]) / np.maximum(torso, 1e-9)


# ---------------------------------------------------------------- exercises

# Angle triplets in KIMORE joint names, mirroring Qawam's packs.
ANGLES = {
    "knee_flexion": (("hip", "knee", "ankle"), "flexion"),
    "hip_flexion": (("shoulder", "hip", "knee"), "flexion"),
    "shoulder_elevation": (("hip", "shoulder", "elbow"), "interior"),
}


def joint_angle(points: np.ndarray, angle: str, side: str) -> np.ndarray:
    (a, b, c), transform = ANGLES[angle]
    value = interior_angle(
        points[:, J[f"{side}_{a}"]], points[:, J[f"{side}_{b}"]], points[:, J[f"{side}_{c}"]]
    )
    return 180.0 - value if transform == "flexion" else value


def smooth(signal: np.ndarray, window: int = 5) -> np.ndarray:
    if signal.size < window:
        return signal.copy()
    kernel = np.ones(window) / window
    padded = np.pad(signal, window // 2, mode="edge")
    return np.convolve(padded, kernel, mode="valid")[: signal.size]


def segment_reps(signal: np.ndarray, enter: float = 0.5, leave: float = 0.2,
                 min_frames: int = 10) -> list[tuple[int, int]]:
    """Hysteresis segmentation like the web coach: base = p10, range = p95 - p10."""
    s = smooth(signal)
    base, top = np.nanpercentile(s, 10), np.nanpercentile(s, 95)
    span = top - base
    if not np.isfinite(span) or span < 10:
        return []
    hi, lo = base + enter * span, base + leave * span
    reps: list[tuple[int, int]] = []
    start: int | None = None
    inside = False
    last_low = 0
    for i, v in enumerate(s):
        if not inside and v <= lo:
            last_low = i
        if not inside and v >= hi:
            inside, start = True, last_low
        elif inside and v <= lo:
            if i - start >= min_frames:
                reps.append((start, i))
            inside = False
            last_low = i
    return reps

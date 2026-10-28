"""Train-only GT overlay spike. No MediaPipe. Does not load validation or test."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from qawam_ml.filters import view_for_camera
from qawam_ml.rehab24 import (
    JOINT_NAMES,
    REPO_ROOT,
    Repetition,
    load_repetitions,
)

OUT_DIR = REPO_ROOT / "data" / "derived" / "overlay"

# Name-based side colours only. Left/right correctness vs the image is UNVERIFIED.
LEFT_IDX = frozenset({6, 7, 8, 9, 10, 16, 17, 18, 19, 20})
RIGHT_IDX = frozenset({11, 12, 13, 14, 15, 21, 22, 23, 24, 25})
BONES: tuple[tuple[int, int], ...] = (
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),
    (4, 5),
    (3, 6),
    (6, 7),
    (7, 8),
    (8, 9),
    (9, 10),
    (3, 11),
    (11, 12),
    (12, 13),
    (13, 14),
    (14, 15),
    (0, 16),
    (16, 17),
    (17, 18),
    (18, 19),
    (19, 20),
    (0, 21),
    (21, 22),
    (22, 23),
    (23, 24),
    (24, 25),
)
# Hypothesis (UNVERIFIED): RightArm=shoulder, RightForeArm=elbow, RightHand=wrist,
# RightUpLeg=hip, RightLeg=knee, RightFoot=ankle.
LABELS = {
    12: "Right shoulder(12)",
    13: "Right elbow(13)",
    14: "Right wrist(14)",
    21: "Right hip(21)",
    22: "Right knee(22)",
    23: "Right ankle(23)",
}
C18_MODES = ("asis", "swapxy", "rot90cw", "rot90ccw")


def _bgr(index: int) -> tuple[int, int, int]:
    if index in LEFT_IDX:
        return (255, 0, 0)
    if index in RIGHT_IDX:
        return (0, 0, 255)
    return (0, 255, 0)


def _mid_frame(first_frame: int, last_frame: int) -> int:
    return first_frame + (last_frame - first_frame) // 2


def _read_bgr_frame(path: Path, frame_index: int) -> np.ndarray:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        cap.release()
        raise RuntimeError(f"cannot open video: {path}")
    cap.set(cv2.CAP_PROP_POS_FRAMES, float(frame_index))
    ok, frame = cap.read()
    nframes = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    if not ok or frame is None:
        raise RuntimeError(f"cannot read frame {frame_index} from {path}")
    print(f"video={path.name} nframes={nframes} size={width}x{height} (WxH)")
    return frame


def _transform_xy(xy: np.ndarray, mode: str, orig_w: float, orig_h: float) -> np.ndarray:
    x = xy[:, 0]
    y = xy[:, 1]
    if mode == "asis":
        return np.stack([x, y], axis=1)
    if mode == "swapxy":
        return np.stack([y, x], axis=1)
    if mode == "rot90cw":
        return np.stack([orig_h - y, x], axis=1)
    if mode == "rot90ccw":
        return np.stack([y, orig_w - x], axis=1)
    raise ValueError(f"unknown mode {mode!r}")


def _inside_fraction(xy: np.ndarray, width: int, height: int) -> float:
    x = xy[:, 0]
    y = xy[:, 1]
    inside = (x >= 0) & (x < width) & (y >= 0) & (y < height)
    return float(inside.mean())


def _draw(frame: np.ndarray, xy: np.ndarray) -> np.ndarray:
    canvas = frame.copy()
    pts = np.round(xy).astype(int)
    for a, b in BONES:
        pa = (int(pts[a, 0]), int(pts[a, 1]))
        pb = (int(pts[b, 0]), int(pts[b, 1]))
        if a in LEFT_IDX and b in LEFT_IDX:
            color = (255, 0, 0)
        elif a in RIGHT_IDX and b in RIGHT_IDX:
            color = (0, 0, 255)
        else:
            color = (0, 255, 0)
        cv2.line(canvas, pa, pb, color, 2, cv2.LINE_AA)
    for i, (px, py) in enumerate(pts):
        cv2.circle(canvas, (int(px), int(py)), 5, _bgr(i), -1, cv2.LINE_AA)
    for i, text in LABELS.items():
        px, py = int(pts[i, 0]), int(pts[i, 1])
        cv2.putText(
            canvas,
            text,
            (px + 8, py - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 0, 255),
            1,
            cv2.LINE_AA,
        )
    return canvas


def _report_xy(tag: str, xy: np.ndarray, width: int, height: int) -> None:
    print(
        f"mode={tag} inside={_inside_fraction(xy, width, height):.3f} "
        f"min_x={xy[:, 0].min():.3f} max_x={xy[:, 0].max():.3f} "
        f"min_y={xy[:, 1].min():.3f} max_y={xy[:, 1].max():.3f} "
        f"frame={width}x{height}"
    )


def _save_overlay(
    *,
    row: Repetition,
    camera: int,
    mode: str,
    xy: np.ndarray,
    frame: np.ndarray,
) -> None:
    frame_index = _mid_frame(row.first_frame, row.last_frame)
    height, width = frame.shape[:2]
    _report_xy(mode, xy, width, height)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"Ex{row.exercise_id}_{row.video_id}_rep{row.repetition_number}_f{frame_index}"
    output = OUT_DIR / f"cam{camera}_{mode}_{stem}.png"
    if not cv2.imwrite(str(output), _draw(frame, xy)):
        raise RuntimeError(f"failed to write overlay: {output}")
    print(f"wrote {output} (frame={width}x{height})")


def main() -> int:
    train_cam17 = load_repetitions(
        "train",
        filter_name="gt_quality",
        cam=17,
        caller="ml/spike/overlay_check.py",
    )
    train_cam18 = load_repetitions(
        "train",
        filter_name="gt_quality",
        cam=18,
        caller="ml/spike/overlay_check.py",
    )
    cam18_keys = {
        (row.video_id, row.repetition_number, row.exercise_id)
        for row in train_cam18
    }
    ex1 = next(
        (
            row
            for row in train_cam17
            if row.exercise_id == 1
            and row.cam17_orientation == "front"
            and (row.video_id, row.repetition_number, row.exercise_id) in cam18_keys
        ),
        None,
    )
    ex6 = next(
        (
            row
            for row in train_cam18
            if row.exercise_id == 6 and row.cam17_orientation == "front"
        ),
        None,
    )
    if ex1 is None:
        raise SystemExit("no train Ex1 front repetition passing gt_quality for both cameras")
    if ex6 is None:
        raise SystemExit("no train Ex6 front repetition passing gt_quality(18)")

    print("hypothesis UNVERIFIED: LeftArm=shoulder LeftForeArm=elbow LeftHand=wrist")
    print("LeftUpLeg=hip LeftLeg=knee LeftFoot=ankle (Right* mirrors).")
    print("Left=blue Right=red central=green; do not treat overlay as a left/right decision.")
    print("joints:", ", ".join(f"{i}:{name}" for i, name in enumerate(JOINT_NAMES)))

    for row, camera in ((ex1, 17), (ex1, 18), (ex6, 18)):
        frame_index = _mid_frame(row.first_frame, row.last_frame)
        print(
            f"split=train person_id={row.person_id} video_id={row.video_id} "
            f"rep={row.repetition_number} exercise_id={row.exercise_id} "
            f"cam17_orientation={row.cam17_orientation} camera={camera} "
            f"camera_view={view_for_camera(row.cam17_orientation, camera)} "
            f"frames=[{row.first_frame},{row.last_frame}] mid={frame_index}"
        )
        joints_path = row.joints_c17_30fps if camera == 17 else row.joints_c18_30fps
        video_path = (
            row.video_c17_30fps if camera == 17 else row.video_c18_30fps_transposed
        )
        joints = np.load(joints_path)
        if joints.ndim != 3 or joints.shape[1:] != (26, 2):
            raise ValueError(f"expected frames x 26 x 2 joints, got {joints.shape}: {joints_path}")
        if frame_index < 0 or frame_index >= joints.shape[0]:
            raise IndexError(f"frame {frame_index} outside joints array: {joints_path}")
        print(f"npy shape={joints.shape} dtype={joints.dtype} path={joints_path}")
        xy = joints[frame_index]
        frame = _read_bgr_frame(video_path, frame_index)
        if camera == 17:
            _save_overlay(
                row=row,
                camera=17,
                mode="asis",
                xy=xy,
                frame=frame,
            )
            continue

        height, width = frame.shape[:2]
        orig_w = float(height)
        orig_h = float(width)
        print(
            f"c18 orig_w=frame_height={orig_w} orig_h=frame_width={orig_h} "
            "(mapping UNVERIFIED)"
        )
        for mode in C18_MODES:
            transformed = _transform_xy(xy, mode, orig_w=orig_w, orig_h=orig_h)
            _report_xy(mode, transformed, width, height)
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            stem = (
                f"Ex{row.exercise_id}_{row.video_id}_rep{row.repetition_number}_"
                f"f{frame_index}"
            )
            output = OUT_DIR / f"cam18_{mode}_{stem}.png"
            if not cv2.imwrite(str(output), _draw(frame, transformed)):
                raise RuntimeError(f"failed to write overlay: {output}")
            print(f"wrote {output} (frame={width}x{height})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

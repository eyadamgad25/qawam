"""Compare MediaPipe landmarks with selected train-only REHAB24-6 frames."""

from __future__ import annotations

import math
import time
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python.components.containers import NormalizedLandmark

from qawam_ml.rehab24 import REPO_ROOT, Repetition, load_repetitions

MODEL_PATH = REPO_ROOT / "data" / "derived" / "models" / "pose_landmarker_lite.task"
OUT_DIR = REPO_ROOT / "data" / "derived" / "mediapipe"

# These correspondences follow the overlay hypothesis and remain UNVERIFIED.
GT_INDICES = {
    "left": (
        ("shoulder", 7),
        ("elbow", 8),
        ("wrist", 9),
        ("hip", 16),
        ("knee", 17),
        ("ankle", 18),
    ),
    "right": (
        ("shoulder", 12),
        ("elbow", 13),
        ("wrist", 14),
        ("hip", 21),
        ("knee", 22),
        ("ankle", 23),
    ),
}
MP_INDICES = {
    "left": (
        ("shoulder", 11),
        ("elbow", 13),
        ("wrist", 15),
        ("hip", 23),
        ("knee", 25),
        ("ankle", 27),
    ),
    "right": (
        ("shoulder", 12),
        ("elbow", 14),
        ("wrist", 16),
        ("hip", 24),
        ("knee", 26),
        ("ankle", 28),
    ),
}


def _first_samples() -> list[tuple[Repetition, int]]:
    train17 = load_repetitions(
        "train",
        filter_name="gt_quality",
        cam=17,
        caller="ml/spike/mediapipe_check.py",
    )
    train18 = load_repetitions(
        "train",
        filter_name="gt_quality",
        cam=18,
        caller="ml/spike/mediapipe_check.py",
    )
    cam18_keys = {
        (row.video_id, row.repetition_number, row.exercise_id) for row in train18
    }
    ex1 = next(
        (
            row
            for row in train17
            if row.exercise_id == 1
            and row.cam17_orientation == "front"
            and (row.video_id, row.repetition_number, row.exercise_id) in cam18_keys
        ),
        None,
    )
    ex6 = next(
        (
            row
            for row in train18
            if row.exercise_id == 6 and row.cam17_orientation == "front"
        ),
        None,
    )
    if ex1 is None or ex6 is None:
        raise RuntimeError("could not find the train-only gt_quality overlay samples")
    return [(ex1, 17), (ex1, 18), (ex6, 18)]


def _frame_at(path: Path, frame_index: int) -> np.ndarray:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        cap.release()
        raise RuntimeError(f"cannot open video: {path}")
    try:
        cap.set(cv2.CAP_PROP_POS_FRAMES, float(frame_index))
        ok, frame = cap.read()
    finally:
        cap.release()
    if not ok or frame is None:
        raise RuntimeError(f"cannot read frame {frame_index} from {path}")
    return frame


def _ground_truth(row: Repetition, camera: int, frame_index: int) -> dict[str, np.ndarray]:
    path = row.joints_c17_30fps if camera == 17 else row.joints_c18_30fps
    joints = np.load(path)
    if joints.ndim != 3 or joints.shape[1:] != (26, 2):
        raise ValueError(f"expected frames x 26 x 2 joints, got {joints.shape}: {path}")
    if frame_index < 0 or frame_index >= joints.shape[0]:
        raise IndexError(f"frame {frame_index} outside joints array: {path}")
    return {
        side: np.asarray([joints[frame_index, index] for _, index in entries])
        for side, entries in GT_INDICES.items()
    }


def _model_points(
    landmarks: list[NormalizedLandmark],
    width: int,
    height: int,
) -> tuple[dict[str, np.ndarray], dict[str, list[float | None]]]:
    points: dict[str, np.ndarray] = {}
    confidences: dict[str, list[float | None]] = {}
    for side, entries in MP_INDICES.items():
        points[side] = np.asarray(
            [(landmarks[index].x * width, landmarks[index].y * height) for _, index in entries],
            dtype=np.float64,
        )
        confidences[side] = [
            landmarks[index].visibility for _, index in entries
        ]
    return points, confidences


def _mean_error(
    ground_truth: dict[str, np.ndarray],
    model_points: dict[str, np.ndarray],
    *,
    swap_sides: bool,
    diagonal: float,
) -> tuple[float, float]:
    errors: list[float] = []
    for side in ("left", "right"):
        model_side = ("right" if side == "left" else "left") if swap_sides else side
        distances = np.linalg.norm(ground_truth[side] - model_points[model_side], axis=1)
        errors.extend(float(distance) for distance in distances)
    mean_pixels = sum(errors) / len(errors)
    return mean_pixels, mean_pixels / diagonal


def _draw_comparison(
    frame: np.ndarray,
    ground_truth: dict[str, np.ndarray],
    model_points: dict[str, np.ndarray],
) -> np.ndarray:
    canvas = frame.copy()
    for side in ("left", "right"):
        color = (255, 0, 0) if side == "left" else (0, 0, 255)
        for point_index, (joint_name, gt_index) in enumerate(GT_INDICES[side]):
            gt = tuple(np.rint(ground_truth[side][point_index]).astype(int))
            mp_point = tuple(np.rint(model_points[side][point_index]).astype(int))
            cv2.circle(canvas, gt, 6, color, -1, cv2.LINE_AA)
            cv2.circle(canvas, mp_point, 8, (0, 255, 255), 2, cv2.LINE_AA)
            cv2.line(canvas, gt, mp_point, (0, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(
                canvas,
                f"GT {gt_index}/{joint_name}",
                (gt[0] + 6, gt[1] - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                color,
                1,
                cv2.LINE_AA,
            )
    cv2.putText(
        canvas,
        "GT dots vs MediaPipe rings (direct side labels; not a clinical assessment)",
        (12, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (0, 255, 255),
        1,
        cv2.LINE_AA,
    )
    return canvas


def _check_sample(
    landmarker: mp.tasks.vision.PoseLandmarker,
    row: Repetition,
    camera: int,
) -> None:
    frame_index = row.first_frame + (row.last_frame - row.first_frame) // 2
    video = row.video_c17_30fps if camera == 17 else row.video_c18_30fps_transposed
    joints = row.joints_c17_30fps if camera == 17 else row.joints_c18_30fps
    frame = _frame_at(video, frame_index)
    height, width = frame.shape[:2]
    ground_truth = _ground_truth(row, camera, frame_index)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

    started = time.perf_counter()
    result = landmarker.detect(image)
    elapsed_ms = (time.perf_counter() - started) * 1000
    stem = (
        f"cam{camera}_Ex{row.exercise_id}_{row.video_id}_"
        f"rep{row.repetition_number}_f{frame_index}"
    )
    print(
        f"split=train person_id={row.person_id} exercise=Ex{row.exercise_id} "
        f"camera={camera} video={video.name} joints={joints.name} "
        f"rep={row.repetition_number} frame={frame_index} frame_size={width}x{height} "
        f"poses={len(result.pose_landmarks)} inference_ms={elapsed_ms:.1f}"
    )

    if not result.pose_landmarks:
        print("pose=not_detected; no landmark errors computed")
        return

    model_points, confidences = _model_points(result.pose_landmarks[0], width, height)
    diagonal = math.hypot(width, height)
    for side_mapping, swap_sides in (("direct", False), ("swapped", True)):
        mean_pixels, normalized = _mean_error(
            ground_truth,
            model_points,
            swap_sides=swap_sides,
            diagonal=diagonal,
        )
        print(
            f"side_mapping={side_mapping} mean_pixel_error={mean_pixels:.1f} "
            f"mean_frame_diagonal_fraction={normalized:.5f}"
        )
    for side in ("left", "right"):
        values = [value for value in confidences[side] if value is not None]
        mean_confidence = f"{sum(values) / len(values):.3f}" if values else "unavailable"
        print(f"mp_visibility_{side}_mean={mean_confidence}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUT_DIR / f"{stem}.png"
    if not cv2.imwrite(str(output), _draw_comparison(frame, ground_truth, model_points)):
        raise RuntimeError(f"failed to write comparison overlay: {output}")
    print(f"wrote {output}")


def main() -> int:
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            "Pose Landmarker model missing. Download the official Lite task model "
            f"to {MODEL_PATH}; see docs/experiments.md."
        )

    options = mp.tasks.vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(MODEL_PATH)),
        running_mode=mp.tasks.vision.RunningMode.IMAGE,
        num_poses=1,
    )
    print(f"model={MODEL_PATH} size_bytes={MODEL_PATH.stat().st_size}")
    print("Camera18 uses asis coordinates only; orientation/mapping remains UNVERIFIED.")
    print("Landmark correspondences and side mapping are hypotheses, not clinical rules.")
    with mp.tasks.vision.PoseLandmarker.create_from_options(options) as landmarker:
        for row, camera in _first_samples():
            _check_sample(landmarker, row, camera)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

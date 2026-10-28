"""Compare pose detection and 2D landmarks across train/validation camera views."""

from __future__ import annotations

import argparse
import csv
import math
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python.components.containers import NormalizedLandmark

from qawam_ml.filters import view_for_camera
from qawam_ml.rehab24 import (
    REPO_ROOT,
    Repetition,
    SplitName,
    load_repetitions,
)

MODEL_PATH = REPO_ROOT / "data" / "derived" / "models" / "pose_landmarker_lite.task"
OUT_DIR = REPO_ROOT / "data" / "derived" / "view-robustness"
MAX_REPETITIONS_PER_SUBJECT_VIEW = 5
SAMPLE_FRACTIONS = (0.0, 0.25, 0.5, 0.75, 1.0)

# Joint indices follow the still-UNVERIFIED correspondence used by angle_check.py.
EXERCISE_JOINTS: dict[int, dict[str, tuple[int, int, int]]] = {
    1: {
        "left": (7, 8, 9),
        "right": (12, 13, 14),
    },
    5: {
        "left": (16, 17, 18),
        "right": (21, 22, 23),
    },
    6: {
        "left": (16, 17, 18),
        "right": (21, 22, 23),
    },
}
MODEL_JOINTS: dict[int, dict[str, tuple[int, int, int]]] = {
    1: {
        "left": (11, 13, 15),
        "right": (12, 14, 16),
    },
    5: {
        "left": (23, 25, 27),
        "right": (24, 26, 28),
    },
    6: {
        "left": (23, 25, 27),
        "right": (24, 26, 28),
    },
}


def _sample_frames(row: Repetition) -> list[int]:
    span = row.last_frame - row.first_frame
    return list(
        dict.fromkeys(
            row.first_frame + round(span * fraction) for fraction in SAMPLE_FRACTIONS
        )
    )


def _select_repetitions(
    rows: list[Repetition],
    camera: int,
) -> list[Repetition]:
    grouped: dict[tuple[int, str, int], list[Repetition]] = defaultdict(list)
    for row in rows:
        if row.exercise_id not in EXERCISE_JOINTS:
            continue
        view = view_for_camera(row.cam17_orientation, camera)
        grouped[(row.exercise_id, view, row.person_id)].append(row)

    selected: list[Repetition] = []
    for key in sorted(grouped):
        candidates = sorted(
            grouped[key],
            key=lambda row: (row.video_id, row.repetition_number),
        )
        selected.extend(candidates[:MAX_REPETITIONS_PER_SUBJECT_VIEW])
    return sorted(
        selected,
        key=lambda row: (
            row.exercise_id,
            view_for_camera(row.cam17_orientation, camera),
            row.person_id,
            row.video_id,
            row.repetition_number,
        ),
    )


def _read_sampled_frames(path: Path, frame_indices: list[int]) -> dict[int, np.ndarray]:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        capture.release()
        raise RuntimeError(f"cannot open video: {path}")
    frames: dict[int, np.ndarray] = {}
    try:
        for frame_index in frame_indices:
            capture.set(cv2.CAP_PROP_POS_FRAMES, float(frame_index))
            ok, frame = capture.read()
            if not ok or frame is None:
                raise RuntimeError(f"cannot read frame {frame_index} from {path}")
            frames[frame_index] = frame
    finally:
        capture.release()
    return frames


def _model_points(
    landmarks: list[NormalizedLandmark],
    width: int,
    height: int,
    exercise_id: int,
) -> tuple[dict[str, np.ndarray], list[float]]:
    indices_by_side = MODEL_JOINTS[exercise_id]
    points = {
        side: np.asarray(
            [(landmarks[index].x * width, landmarks[index].y * height) for index in indices],
            dtype=np.float64,
        )
        for side, indices in indices_by_side.items()
    }
    visibility = [
        landmark.visibility
        for indices in indices_by_side.values()
        for index in indices
        if (landmark := landmarks[index]).visibility is not None
    ]
    return points, visibility


def _keypoint_error(
    ground_truth: dict[str, np.ndarray],
    model_points: dict[str, np.ndarray],
    *,
    swap_sides: bool,
    diagonal: float,
) -> float:
    distances: list[float] = []
    for side in ("left", "right"):
        model_side = side
        if swap_sides:
            model_side = "right" if side == "left" else "left"
        distances.extend(
            float(distance) / diagonal
            for distance in np.linalg.norm(
                ground_truth[side] - model_points[model_side],
                axis=1,
            )
        )
    return sum(distances) / len(distances)


def _ground_truth(
    joints: np.ndarray,
    frame_index: int,
    exercise_id: int,
) -> dict[str, np.ndarray]:
    if joints.ndim != 3 or joints.shape[1:] != (26, 2):
        raise ValueError(f"expected frames x 26 x 2 joints, got {joints.shape}")
    if frame_index < 0 or frame_index >= joints.shape[0]:
        raise IndexError(f"sample frame {frame_index} outside joints array")
    return {
        side: joints[frame_index, list(indices)].astype(np.float64, copy=False)
        for side, indices in EXERCISE_JOINTS[exercise_id].items()
    }


def _summarize(results: list[dict[str, Any]]) -> None:
    grouped: dict[tuple[int, int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        grouped[(row["exercise_id"], row["camera"], row["view"])].append(row)

    for (exercise_id, camera, view), rows in sorted(grouped.items()):
        repetitions: dict[tuple[int, str, int], list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            repetitions[(row["person_id"], row["video_id"], row["repetition_number"])].append(row)
        per_subject_rates: dict[int, list[float]] = defaultdict(list)
        for (person_id, _, _), rep_rows in repetitions.items():
            per_subject_rates[person_id].append(
                sum(row["pose_detected"] for row in rep_rows) / len(rep_rows)
            )
        subject_rates = [
            sum(rates) / len(rates) for rates in per_subject_rates.values()
        ]
        detected_rows = [row for row in rows if row["pose_detected"]]
        visibility_values = [
            row["mean_visibility"] for row in detected_rows
            if row["mean_visibility"] is not None
        ]
        direct_errors = [
            row["direct_error_diagonal_fraction"]
            for row in detected_rows
            if row["direct_error_diagonal_fraction"] is not None
        ]
        swapped_errors = [
            row["swapped_error_diagonal_fraction"]
            for row in detected_rows
            if row["swapped_error_diagonal_fraction"] is not None
        ]

        def percentage(values: list[float]) -> str:
            return f"{100 * sum(values) / len(values):.2f}" if values else "unavailable"

        mean_visibility = (
            f"{sum(visibility_values) / len(visibility_values):.3f}"
            if visibility_values
            else "unavailable"
        )
        print(
            f"Ex{exercise_id} cam{camera} view={view} "
            f"subjects={len(per_subject_rates)} repetitions={len(repetitions)} "
            f"frames={len(rows)} detected={sum(row['pose_detected'] for row in rows)}/"
            f"{len(rows)} detection_rate_pct={percentage([row['pose_detected'] for row in rows])} "
            f"subject_macro_detection_rate_pct={percentage(subject_rates)} "
            f"mean_visibility={mean_visibility} "
            f"direct_error_frame_diagonal_pct={percentage(direct_errors)} "
            f"swapped_error_frame_diagonal_pct={percentage(swapped_errors)}"
        )


def _analyze(split: SplitName) -> Path:
    rows_by_camera = {
        camera: load_repetitions(
            split,
            filter_name="gt_quality",
            cam=camera,
            caller="ml/spike/view_robustness_check.py",
        )
        for camera in (17, 18)
    }
    repetitions = [
        (row, camera)
        for camera, rows in rows_by_camera.items()
        for row in _select_repetitions(rows, camera)
    ]
    if not repetitions:
        raise RuntimeError(f"no eligible repetitions in {split}")
    print(
        f"split={split} selected_repetitions={len(repetitions)} "
        f"subjects={sorted({row.person_id for row, _ in repetitions})} "
        f"max_reps_per_subject_exercise_view_camera="
        f"{MAX_REPETITIONS_PER_SUBJECT_VIEW}"
    )
    print(
        "Five evenly spaced frames per repetition; gt_quality by matching camera; "
        "no test split, tuning, or clinical thresholds."
    )
    print(
        "Camera18 coordinates use as-is; side labels, joint mappings, and "
        "Camera18 alignment remain UNVERIFIED."
    )

    options = mp.tasks.vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(MODEL_PATH)),
        running_mode=mp.tasks.vision.RunningMode.IMAGE,
        num_poses=1,
    )
    results: list[dict[str, Any]] = []
    frame_count = 0
    with mp.tasks.vision.PoseLandmarker.create_from_options(options) as landmarker:
        for row, camera in repetitions:
            exercise_id = row.exercise_id
            frame_indices = _sample_frames(row)
            video_path = (
                row.video_c17_30fps
                if camera == 17
                else row.video_c18_30fps_transposed
            )
            joints_path = (
                row.joints_c17_30fps if camera == 17 else row.joints_c18_30fps
            )
            joints = np.load(joints_path)
            frames = _read_sampled_frames(video_path, frame_indices)
            for frame_index, frame in frames.items():
                frame_count += 1
                height, width = frame.shape[:2]
                image = mp.Image(
                    image_format=mp.ImageFormat.SRGB,
                    data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
                )
                started = time.perf_counter()
                detection = landmarker.detect(image)
                elapsed_ms = (time.perf_counter() - started) * 1000
                detected = bool(detection.pose_landmarks)
                gt_points = _ground_truth(joints, frame_index, exercise_id)
                row_result: dict[str, Any] = {
                    "split": split,
                    "exercise_id": exercise_id,
                    "camera": camera,
                    "view": view_for_camera(row.cam17_orientation, camera),
                    "person_id": row.person_id,
                    "video_id": row.video_id,
                    "repetition_number": row.repetition_number,
                    "frame": frame_index,
                    "width": width,
                    "height": height,
                    "pose_detected": int(detected),
                    "inference_ms": f"{elapsed_ms:.3f}",
                    "mean_visibility": None,
                    "direct_error_diagonal_fraction": None,
                    "swapped_error_diagonal_fraction": None,
                }
                if detected:
                    model_points, visibility = _model_points(
                        detection.pose_landmarks[0],
                        width,
                        height,
                        exercise_id,
                    )
                    diagonal = math.hypot(width, height)
                    row_result["mean_visibility"] = (
                        sum(visibility) / len(visibility) if visibility else None
                    )
                    row_result["direct_error_diagonal_fraction"] = _keypoint_error(
                        gt_points,
                        model_points,
                        swap_sides=False,
                        diagonal=diagonal,
                    )
                    row_result["swapped_error_diagonal_fraction"] = _keypoint_error(
                        gt_points,
                        model_points,
                        swap_sides=True,
                        diagonal=diagonal,
                    )
                results.append(row_result)
                if frame_count % 50 == 0:
                    print(f"processed_frames={frame_count}")

    _summarize(results)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUT_DIR / f"{split}_view_robustness.csv"
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    print(f"wrote {output_path}")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare MediaPipe pose detection across camera views on train or "
            "validation subjects; test is intentionally unavailable."
        )
    )
    parser.add_argument(
        "--split",
        choices=("train", "validation"),
        default="train",
        help="subject split; test is intentionally unavailable",
    )
    args = parser.parse_args()
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            "Pose Landmarker model missing. Download the official Lite task model "
            f"to {MODEL_PATH}; see ml/README.md."
        )
    split: SplitName = "validation" if args.split == "validation" else "train"
    _analyze(split)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

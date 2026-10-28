"""Compare MediaPipe and GT 2D angles across selected train-only reps."""

from __future__ import annotations

import argparse
import csv
import math
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python.components.containers import NormalizedLandmark

from qawam_ml.rehab24 import REPO_ROOT, Repetition, SplitName, load_repetitions

MODEL_PATH = REPO_ROOT / "data" / "derived" / "models" / "pose_landmarker_lite.task"
OUT_DIR = REPO_ROOT / "data" / "derived" / "angles"
SAMPLE_FRACTIONS = (0.0, 0.25, 0.5, 0.75, 1.0)


@dataclass(frozen=True)
class AngleCheckConfig:
    camera: int
    metric: str
    view: str
    gt_triplets: dict[str, tuple[int, int, int]]
    mp_triplets: dict[str, tuple[int, int, int]]


LEG_TRIPLETS = {
    "left": (16, 17, 18),
    "right": (21, 22, 23),
}
MP_LEG_TRIPLETS = {
    "left": (23, 25, 27),
    "right": (24, 26, 28),
}
EXERCISE_CONFIG = {
    1: AngleCheckConfig(
        camera=17,
        metric="elbow",
        view="front",
        gt_triplets={"left": (7, 8, 9), "right": (12, 13, 14)},
        mp_triplets={"left": (11, 13, 15), "right": (12, 14, 16)},
    ),
    5: AngleCheckConfig(
        camera=18,
        metric="knee",
        view="profile",
        gt_triplets=LEG_TRIPLETS,
        mp_triplets=MP_LEG_TRIPLETS,
    ),
    6: AngleCheckConfig(
        camera=18,
        metric="knee",
        view="profile",
        gt_triplets=LEG_TRIPLETS,
        mp_triplets=MP_LEG_TRIPLETS,
    ),
}


def _find_repetitions(
    split: SplitName,
    exercise_id: int,
    camera: int,
) -> list[Repetition]:
    rows = load_repetitions(
        split,
        filter_name="gt_quality",
        cam=camera,
        caller="ml/spike/angle_check.py",
    )
    repetitions = [
        repetition
        for repetition in rows
        if repetition.exercise_id == exercise_id
        and repetition.cam17_orientation == "front"
    ]
    if not repetitions:
        raise RuntimeError(
            f"no {split} Ex{exercise_id} front repetition passing "
            f"gt_quality({camera})"
        )
    return repetitions


def _angle_degrees(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float | None:
    first = a - b
    second = c - b
    first_norm = float(np.linalg.norm(first))
    second_norm = float(np.linalg.norm(second))
    if first_norm == 0 or second_norm == 0:
        return None
    cosine = float(np.dot(first, second)) / (first_norm * second_norm)
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def _sample_frames(row: Repetition) -> list[int]:
    span = row.last_frame - row.first_frame
    return list(
        dict.fromkeys(
            row.first_frame + round(span * fraction) for fraction in SAMPLE_FRACTIONS
        )
    )


def _read_frame(path: Path, index: int) -> np.ndarray:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        capture.release()
        raise RuntimeError(f"cannot open video: {path}")
    try:
        capture.set(cv2.CAP_PROP_POS_FRAMES, float(index))
        ok, frame = capture.read()
    finally:
        capture.release()
    if not ok or frame is None:
        raise RuntimeError(f"cannot read frame {index} from {path}")
    return frame


def _mp_points(
    landmarks: list[NormalizedLandmark],
    width: int,
    height: int,
    triplets: dict[str, tuple[int, int, int]],
) -> dict[str, np.ndarray]:
    points = np.asarray(
        [(landmark.x * width, landmark.y * height) for landmark in landmarks],
        dtype=np.float64,
    )
    return {
        side: points[list(indices)]
        for side, indices in triplets.items()
    }


def _triplet_angles(points: dict[str, np.ndarray]) -> dict[str, float | None]:
    return {
        side: _angle_degrees(points[side][0], points[side][1], points[side][2])
        for side in ("left", "right")
    }


def _csv_path(split: str, exercise_id: int, camera: int, metric: str) -> Path:
    return OUT_DIR / f"{split}_ex{exercise_id}_cam{camera}_{metric}_angles.csv"


def _analyze(
    repetitions: list[Repetition],
    split: SplitName,
    exercise_id: int,
    config: AngleCheckConfig,
) -> Path:
    camera = config.camera
    metric = config.metric
    gt_triplets = config.gt_triplets
    mp_triplets = config.mp_triplets
    results: list[dict[str, object]] = []
    errors: dict[str, list[float]] = {"direct": [], "swapped": []}
    repetition_errors: dict[str, dict[tuple[str, int], list[float]]] = {
        "direct": {},
        "swapped": {},
    }
    pose_count = 0
    frame_count = 0
    options = mp.tasks.vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(MODEL_PATH)),
        running_mode=mp.tasks.vision.RunningMode.IMAGE,
        num_poses=1,
    )
    with mp.tasks.vision.PoseLandmarker.create_from_options(options) as landmarker:
        for row in repetitions:
            frame_indices = _sample_frames(row)
            joints_path = (
                row.joints_c17_30fps if camera == 17 else row.joints_c18_30fps
            )
            video_path = (
                row.video_c17_30fps
                if camera == 17
                else row.video_c18_30fps_transposed
            )
            joints = np.load(joints_path)
            if joints.ndim != 3 or joints.shape[1:] != (26, 2):
                raise ValueError(
                    f"expected frames x 26 x 2 joints, got {joints.shape}: "
                    f"{joints_path}"
                )
            if min(frame_indices) < 0 or max(frame_indices) >= joints.shape[0]:
                raise IndexError(f"sample frames outside joints array: {joints_path}")
            repetition_key = (row.video_id, row.repetition_number)
            for mapping in repetition_errors:
                repetition_errors[mapping][repetition_key] = []

            for frame_index in frame_indices:
                frame_count += 1
                frame = _read_frame(video_path, frame_index)
                height, width = frame.shape[:2]
                gt_points = {
                    side: joints[frame_index, list(indices)]
                    for side, indices in gt_triplets.items()
                }
                gt_angles = _triplet_angles(gt_points)
                image = mp.Image(
                    image_format=mp.ImageFormat.SRGB,
                    data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
                )
                started = time.perf_counter()
                result = landmarker.detect(image)
                elapsed_ms = (time.perf_counter() - started) * 1000
                detected = bool(result.pose_landmarks)
                pose_count += int(detected)
                print(
                    f"split={split} person_id={row.person_id} video={row.video_id} "
                    f"rep={row.repetition_number} frame={frame_index} "
                    f"size={width}x{height} poses={len(result.pose_landmarks)} "
                    f"inference_ms={elapsed_ms:.1f}"
                )

                mp_angles: dict[str, float | None] = {"left": None, "right": None}
                visibility: dict[str, float | None] = {"left": None, "right": None}
                if detected:
                    mp_points = _mp_points(
                        result.pose_landmarks[0],
                        width,
                        height,
                        mp_triplets,
                    )
                    mp_angles = _triplet_angles(mp_points)
                    for side, indices in mp_triplets.items():
                        values = [
                            result.pose_landmarks[0][index].visibility
                            for index in indices
                        ]
                        available = [value for value in values if value is not None]
                        visibility[side] = (
                            sum(available) / len(available) if available else None
                        )

                row_result: dict[str, object] = {
                    "split": split,
                    "person_id": row.person_id,
                    "exercise_id": row.exercise_id,
                    "cam17_orientation": row.cam17_orientation,
                    f"camera{camera}_view": "front" if camera == 17 else "profile",
                    "camera": camera,
                    "metric": metric,
                    "video_id": row.video_id,
                    "repetition_number": row.repetition_number,
                    "frame": frame_index,
                    "pose_detected": int(detected),
                    "inference_ms": f"{elapsed_ms:.3f}",
                }
                for side in ("left", "right"):
                    row_result[f"gt_{side}_{metric}_deg"] = (
                        "" if gt_angles[side] is None else f"{gt_angles[side]:.3f}"
                    )
                    row_result[f"mp_{side}_{metric}_deg"] = (
                        "" if mp_angles[side] is None else f"{mp_angles[side]:.3f}"
                    )
                    row_result[f"mp_{side}_visibility_mean"] = (
                        "" if visibility[side] is None else f"{visibility[side]:.4f}"
                    )
                for mapping in ("direct", "swapped"):
                    for side in ("left", "right"):
                        model_side = (
                            side
                            if mapping == "direct"
                            else ("right" if side == "left" else "left")
                        )
                        gt_angle = gt_angles[side]
                        mp_angle = mp_angles[model_side]
                        error = (
                            None
                            if gt_angle is None or mp_angle is None
                            else abs(gt_angle - mp_angle)
                        )
                        row_result[f"{mapping}_{side}_abs_error_deg"] = (
                            "" if error is None else f"{error:.3f}"
                        )
                        if error is not None:
                            errors[mapping].append(error)
                            repetition_errors[mapping][repetition_key].append(error)
                results.append(row_result)

    for mapping, values in errors.items():
        repetition_maes = [
            sum(rep_values) / len(rep_values)
            for rep_values in repetition_errors[mapping].values()
            if rep_values
        ]
        pooled_mae = sum(values) / len(values) if values else None
        macro_mae = (
            sum(repetition_maes) / len(repetition_maes) if repetition_maes else None
        )
        median_mae = (
            float(np.median(repetition_maes)) if repetition_maes else None
        )
        print(
            f"side_mapping={mapping} pooled_{metric}_angle_mae_deg="
            f"{'unavailable' if pooled_mae is None else f'{pooled_mae:.3f}'} "
            f"macro_repetition_mae_deg="
            f"{'unavailable' if macro_mae is None else f'{macro_mae:.3f}'} "
            f"median_repetition_mae_deg="
            f"{'unavailable' if median_mae is None else f'{median_mae:.3f}'} "
            f"valid_comparisons={len(values)} repetitions={len(repetition_maes)}"
        )
        for repetition_key, rep_values in repetition_errors[mapping].items():
            rep_mae = sum(rep_values) / len(rep_values) if rep_values else None
            print(
                f"side_mapping={mapping} video={repetition_key[0]} "
                f"rep={repetition_key[1]} "
                f"mae_deg={'unavailable' if rep_mae is None else f'{rep_mae:.3f}'} "
                f"comparisons={len(rep_values)}"
            )
    print(f"pose_detection={pose_count}/{frame_count} sampled frames")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = _csv_path(split, exercise_id, camera, metric)
    columns = list(results[0])
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(results)
    print(f"wrote {output_path}")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare MediaPipe and GT joint angles on train or validation reps."
    )
    parser.add_argument(
        "--split",
        choices=("train", "validation"),
        default="train",
        help="subject split to evaluate; test is intentionally unavailable",
    )
    parser.add_argument(
        "--exercise",
        type=int,
        choices=tuple(EXERCISE_CONFIG),
        default=6,
        help="exercise ID: Ex1 elbow angle (Camera17 front), Ex5/Ex6 knee angle (Camera18 profile)",
    )
    args = parser.parse_args()
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            "Pose Landmarker model missing. Download the official Lite task model "
            f"to {MODEL_PATH}; see ml/README.md."
        )
    split: SplitName = "validation" if args.split == "validation" else "train"
    config = EXERCISE_CONFIG[args.exercise]
    camera = config.camera
    metric = config.metric
    repetitions = _find_repetitions(split, args.exercise, camera)
    print(
        f"sample=Ex{args.exercise} split={split} gt_quality({camera}), "
        f"repetitions={len(repetitions)} "
        f"subjects={sorted({row.person_id for row in repetitions})} "
        f"recordings={len({row.video_id for row in repetitions})} "
        f"camera={camera} view={config.view} metric={metric}"
    )
    print(
        f"Five evenly spaced frames per repetition; 2D image-plane {metric} "
        "angles; both side mappings reported; no thresholds or clinical interpretation."
    )
    if camera == 18:
        print("Camera18 asis coordinate relationship remains UNVERIFIED.")
    _analyze(repetitions, split, args.exercise, config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

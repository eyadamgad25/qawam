"""Render the explicitly authorized PM_039 and PM_101 train samples."""

from __future__ import annotations

import math
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO_ROOT / "data" / "derived" / "overlay"
AUTHORIZED_CLIPS = {
    "PM_039": {
        "video": REPO_ROOT
        / "data"
        / "raw"
        / "rehab24-6"
        / "Ex1"
        / "PM_039-Camera18-30fps-transposed.mp4",
        "joints": REPO_ROOT
        / "data"
        / "raw"
        / "rehab24-6"
        / "Ex1"
        / "PM_039-c18-30fps.npy",
        "frames": {
            94: "profile",
            95: "profile",
            96: "profile",
            2539: "half-profile",
            2540: "half-profile",
            2541: "half-profile",
        },
    },
    "PM_101": {
        "video": REPO_ROOT
        / "data"
        / "raw"
        / "rehab24-6"
        / "Ex1"
        / "PM_101-Camera18-30fps-transposed.mp4",
        "joints": REPO_ROOT
        / "data"
        / "raw"
        / "rehab24-6"
        / "Ex1"
        / "PM_101-c18-30fps.npy",
        "frames": {
            34: "half-profile",
            35: "half-profile",
            36: "half-profile",
        },
    },
}
JOINT_NAMES = (
    "Hips",
    "Spine",
    "Spine1",
    "Neck",
    "Head",
    "Head_end",
    "LeftShoulder",
    "LeftArm",
    "LeftForeArm",
    "LeftHand",
    "LeftHand_end",
    "RightShoulder",
    "RightArm",
    "RightForeArm",
    "RightHand",
    "RightHand_end",
    "LeftUpLeg",
    "LeftLeg",
    "LeftFoot",
    "LeftToeBase",
    "LeftToeBase_end",
    "RightUpLeg",
    "RightLeg",
    "RightFoot",
    "RightToeBase",
    "RightToeBase_end",
)
JOINT_EDGES = (
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
LITE_MODEL_PATH = OUTPUT_DIR / "pose_landmarker_lite.task"
MAPPING_CANDIDATES = {
    "documented_hypothesis": (
        (7, 11),
        (8, 13),
        (9, 15),
        (12, 12),
        (13, 14),
        (14, 16),
        (16, 23),
        (17, 25),
        (18, 27),
        (21, 24),
        (22, 26),
        (23, 28),
    ),
    "adjacent_arm_joint_shift": (
        (6, 11),
        (7, 13),
        (8, 15),
        (11, 12),
        (12, 14),
        (13, 16),
        (16, 23),
        (17, 25),
        (18, 27),
        (21, 24),
        (22, 26),
        (23, 28),
    ),
    "documented_hypothesis_side_swapped": (
        (7, 12),
        (8, 14),
        (9, 16),
        (12, 11),
        (13, 13),
        (14, 15),
        (16, 24),
        (17, 26),
        (18, 28),
        (21, 23),
        (22, 25),
        (23, 27),
    ),
}


def main() -> int:
    if not LITE_MODEL_PATH.is_file():
        raise FileNotFoundError(
            f"download the official Lite task model to {LITE_MODEL_PATH}"
        )
    options = vision.PoseLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=str(LITE_MODEL_PATH)),
        running_mode=vision.RunningMode.IMAGE,
        num_poses=1,
    )
    landmarker = vision.PoseLandmarker.create_from_options(options)
    candidate_errors: dict[tuple[str, str], dict[str, list[float]]] = {}
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        for clip_name, clip in AUTHORIZED_CLIPS.items():
            joints = np.load(clip["joints"], mmap_mode="r", allow_pickle=False)
            if joints.ndim != 3 or joints.shape[1:] != (len(JOINT_NAMES), 2):
                raise ValueError(
                    f"unexpected joint array shape for {clip_name}: {joints.shape}"
                )
            capture = cv2.VideoCapture(str(clip["video"]))
            if not capture.isOpened():
                raise OSError(f"could not open authorized video for {clip_name}")
            try:
                video_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
                width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
                if video_frames != joints.shape[0]:
                    print(
                        f"warning: {clip_name} video has {video_frames} frames; "
                        f"joint array has {joints.shape[0]} rows"
                    )
                if (width, height) != (1080, 1920):
                    raise ValueError(
                        f"unexpected {clip_name} dimensions: {width}x{height}"
                    )

                for frame_index, view in clip["frames"].items():
                    if frame_index >= min(video_frames, joints.shape[0]):
                        raise ValueError(
                            f"requested frame outside {clip_name} video: {frame_index}"
                        )
                    capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                    ok, frame = capture.read()
                    if not ok:
                        raise OSError(
                            f"could not decode {clip_name} frame {frame_index}"
                        )
                    cv2.putText(
                        frame,
                        "GT green/red   MediaPipe Lite cyan",
                        (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (255, 255, 255),
                        2,
                        cv2.LINE_AA,
                    )
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    inference = landmarker.detect(
                        mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                    )
                    if len(inference.pose_landmarks) != 1:
                        raise ValueError(
                            f"expected one pose on {clip_name} frame {frame_index}, "
                            f"found {len(inference.pose_landmarks)}"
                        )
                    pose = inference.pose_landmarks[0]
                    pose_points = np.asarray(
                        [[point.x * width, point.y * height] for point in pose],
                        dtype=np.float64,
                    )
                    points = np.asarray(joints[frame_index], dtype=np.float64)
                    if not np.isfinite(points).all():
                        raise ValueError(
                            f"non-finite coordinates on {clip_name} frame {frame_index}"
                        )

                    for connection in vision.PoseLandmarksConnections.POSE_LANDMARKS:
                        p1 = tuple(
                            np.rint(pose_points[connection.start]).astype(int)
                        )
                        p2 = tuple(
                            np.rint(pose_points[connection.end]).astype(int)
                        )
                        cv2.line(frame, p1, p2, (255, 180, 0), 2, cv2.LINE_AA)
                    for landmark_index, (x_value, y_value) in enumerate(pose_points):
                        x, y = int(round(x_value)), int(round(y_value))
                        cv2.circle(frame, (x, y), 4, (255, 180, 0), thickness=-1)
                        cv2.putText(
                            frame,
                            f"M{landmark_index}",
                            (x + 4, y + 12),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.3,
                            (255, 255, 255),
                            1,
                            cv2.LINE_AA,
                        )

                    for start, end in JOINT_EDGES:
                        p1 = tuple(np.rint(points[start]).astype(int))
                        p2 = tuple(np.rint(points[end]).astype(int))
                        cv2.line(frame, p1, p2, (0, 220, 0), 2, cv2.LINE_AA)
                    for joint_index, (x_value, y_value) in enumerate(points):
                        x, y = int(round(x_value)), int(round(y_value))
                        cv2.circle(frame, (x, y), 7, (0, 0, 255), thickness=-1)
                        label_origin = (x + 8, y - 8)
                        cv2.putText(
                            frame,
                            str(joint_index),
                            label_origin,
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.42,
                            (0, 0, 0),
                            3,
                            cv2.LINE_AA,
                        )
                        cv2.putText(
                            frame,
                            str(joint_index),
                            label_origin,
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.42,
                            (255, 255, 255),
                            1,
                            cv2.LINE_AA,
                        )

                    output_path = (
                        OUTPUT_DIR / f"{clip_name}_c18_frame_{frame_index:04d}.png"
                    )
                    if not cv2.imwrite(str(output_path), frame):
                        raise OSError(f"could not write overlay: {output_path}")
                    key = (clip_name, view)
                    candidate_errors.setdefault(
                        key, {name: [] for name in MAPPING_CANDIDATES}
                    )
                    diagonal = math.hypot(width, height)
                    for name, pairs in MAPPING_CANDIDATES.items():
                        candidate_errors[key][name].extend(
                            float(
                                np.linalg.norm(points[gt_index] - pose_points[mp_index])
                            )
                            / diagonal
                            * 100
                            for gt_index, mp_index in pairs
                        )
                    print(
                        f"wrote {output_path.relative_to(REPO_ROOT)} "
                        f"({width}x{height}, GT green/red + Lite landmarks cyan)"
                    )
            finally:
                capture.release()

        print("Candidate mean normalized pixel error (%) by recording/view:")
        for (clip_name, view), candidates in sorted(candidate_errors.items()):
            print(f"  {clip_name} {view}:")
            for name, errors in candidates.items():
                print(f"    {name}: {sum(errors) / len(errors):.3f}")
        print("Combined cross-clip sample:")
        for name in MAPPING_CANDIDATES:
            errors = [
                error
                for candidates in candidate_errors.values()
                for error in candidates[name]
            ]
            print(f"  {name}: {sum(errors) / len(errors):.3f}")
    finally:
        landmarker.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

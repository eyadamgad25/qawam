"""Laptop version of notebooks/fit3d_extract_colab.ipynb: Fit3D videos -> MediaPipe landmarks + Vicon truth.

The Fit3D download needs the browser login, so the archive is downloaded by
hand (fit3d.imar.ro -> Download -> Training Set, about 18 GB). This script
unpacks only the exercises our packs cover (videos, 3D joints, camera
parameters), runs MediaPipe Pose Lite with the same setup as angle_eval.py,
and writes one .npz per subject x action x camera for fit3d_gate_eval.py.
Videos already done are skipped, so it can be stopped and restarted.

  py -3.14 ml\\eval\\fit3d_extract.py --archive C:\\path\\to\\fit3d_train.tar.gz
  py -3.14 ml\\eval\\fit3d_gate_eval.py

Fit3D is non-commercial research data licensed to one person: keep the
archive and outputs local (data/ is git-ignored).
"""

from __future__ import annotations

import argparse
import json
import sys
import tarfile
import time
from collections.abc import Sequence
from pathlib import Path

import numpy as np

EVAL_DIR = Path(__file__).resolve().parent
ML_ROOT = EVAL_DIR.parent
for path in (str(ML_ROOT), str(EVAL_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

from angle_eval import DEFAULT_MODEL, _landmarker, landmark_array  # noqa: E402
from fit3d_gate_eval import DEFAULT_FEATURES, pack_for_action  # noqa: E402
from qawam_ml.rehab24 import REPO_ROOT  # noqa: E402

DEFAULT_WORK = REPO_ROOT / "data" / "raw" / "fit3d"
NEEDED_PARTS = ("/videos/", "/joints3d_25/", "/camera_parameters/")


def wanted(member_name: str) -> bool:
    """Archive members we need: the three parts, for actions a pack measures."""
    if not any(part in member_name for part in NEEDED_PARTS):
        return False
    action = Path(member_name).stem
    return pack_for_action(action) is not None


def project(points3d: np.ndarray, intrinsics: dict) -> np.ndarray:
    """Camera-frame 3D points to pixels with lens distortion (official Fit3D tools, dataset_util.py)."""
    p = np.asarray(intrinsics["p"])[:, [1, 0]]
    x = points3d[:, :2] / points3d[:, 2:3]
    r2 = np.sum(x**2, axis=1)
    radial = 1 + np.transpose(np.matmul(np.asarray(intrinsics["k"]), np.array([r2, r2**2, r2**3])))
    tan = np.matmul(x, np.transpose(p))
    xx = x * (tan + radial) + r2[:, None] * p
    return np.asarray(intrinsics["f"]) * xx + np.asarray(intrinsics["c"])


def unpack(archive: Path, work: Path) -> Path:
    """Extract only the needed members (one pass over the archive); returns the train/ folder."""
    if not any(work.rglob("train")):
        print(f"unpacking needed files from {archive} (one pass over the archive, a few minutes)...")
        with tarfile.open(archive, "r:*") as tar:
            members = [m for m in tar if m.isfile() and wanted(m.name)]
            tar.extractall(work, members=members, filter="data")
        print(f"unpacked {len(members)} files")
    return next(p for p in work.rglob("train") if p.is_dir())


def extract_video(train: Path, subject: str, action: str, camera: str, model: Path, step: int) -> dict:
    import cv2

    joints = np.asarray(json.loads((train / subject / "joints3d_25" / f"{action}.json").read_text())["joints3d_25"], dtype=float)
    params = json.loads((train / subject / "camera_parameters" / camera / f"{action}.json").read_text())
    rotation, translation = np.asarray(params["extrinsics"]["R"]), np.asarray(params["extrinsics"]["T"])
    capture = cv2.VideoCapture(str(train / subject / "videos" / camera / f"{action}.mp4"))
    fps = capture.get(cv2.CAP_PROP_FPS) or 50.0
    width, height = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    mp, landmarker = _landmarker(model)
    frames, marks, gt2d, gt3d = [], [], [], []
    try:
        for i in range(len(joints)):
            ok, bgr = capture.read()
            if not ok:
                break
            if i % step:
                continue
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
            result = landmarker.detect_for_video(image, int(i * 1000 / fps))
            marks.append(landmark_array(result.pose_landmarks[0], width, height) if result.pose_landmarks else np.full((33, 5), np.nan))
            frames.append(i)
            gt3d.append(joints[i])
            gt2d.append(project(np.matmul(joints[i] - translation, np.transpose(rotation)), params["intrinsics_w_distortion"]))
    finally:
        capture.release()
        landmarker.close()
    meta = {"subject": subject, "action": action, "camera": camera, "fps": fps / step, "width": width, "height": height}
    return {
        "frames": np.asarray(frames),
        "marks": np.asarray(marks, dtype=np.float32),
        "gt2d": np.asarray(gt2d, dtype=np.float32),
        "gt3d": np.asarray(gt3d, dtype=np.float32),
        "meta": json.dumps(meta),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--archive", type=Path, help="fit3d_train.tar.gz (skip once unpacked)")
    parser.add_argument("--work", type=Path, default=DEFAULT_WORK, help="where the needed files are unpacked")
    parser.add_argument("--out", type=Path, default=DEFAULT_FEATURES)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--step", type=int, default=3, help="use every Nth frame (Fit3D is 50 fps)")
    args = parser.parse_args(argv)
    if args.archive is None and not any(args.work.rglob("train")):
        print("give --archive the first time (nothing unpacked yet)", file=sys.stderr)
        return 1
    train = unpack(args.archive, args.work) if args.archive else next(p for p in args.work.rglob("train") if p.is_dir())
    jobs = [
        (subject.name, video.stem, camera.name)
        for subject in sorted(p for p in train.iterdir() if p.is_dir())
        for camera in sorted((subject / "videos").iterdir())
        for video in sorted(camera.glob("*.mp4"))
        if pack_for_action(video.stem)
    ]
    print(f"{len(jobs)} videos; actions: {sorted({a for _, a, _ in jobs})}")
    args.out.mkdir(parents=True, exist_ok=True)
    start, done = time.time(), 0
    for n, (subject, action, camera) in enumerate(jobs, 1):
        target = args.out / f"{subject}_{action.replace(' ', '_')}_{camera}.npz"
        if target.exists():
            continue
        np.savez_compressed(target, **extract_video(train, subject, action, camera, args.model, args.step))
        done += 1
        left = (time.time() - start) / done * (len(jobs) - n)
        print(f"{n}/{len(jobs)} {subject} {action} {camera}, about {left / 60:.0f} min left")
    print(f"done: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Full-frame joint-angle baseline on REHAB24-6 for the exercise packs.

For every frame of every repetition (train / validation only, unless
--final), runs MediaPipe Pose Landmarker in VIDEO mode, computes the pack's
angles from MediaPipe and from the dataset's 2D ground truth, and writes:

  frames.csv   one row per frame x side x angle
  reps.csv     one row per repetition x camera x side (the unit the
               confidence gate is calibrated on)
  summary.md   error by exercise / camera / view, per subject, and the
               calibrated confidence gate (train -> validation)
  summary.json the same numbers for the docs and the deck

Ground truth is the dataset's projected 2D skeleton, so errors are 2D
angle disagreements, not clinical accuracy. Nothing here sets a clinical
threshold: --tolerance-deg only defines what the evaluation calls a wrong
measurement, and is reported with every result.

Run from the repo root (Windows PowerShell):
  .\\.venv\\Scripts\\python.exe ml\\eval\\angle_eval.py --exercises 6
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
import time
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

ML_ROOT = Path(__file__).resolve().parents[1]
if str(ML_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_ROOT))

from qawam_ml.filters import view_for_camera  # noqa: E402
from qawam_ml.packs import (  # noqa: E402
    MEDIAPIPE_INDEX,
    REHAB24_JOINT_FOR_LANDMARK,
    ResolvedPack,
    compute_angle,
    load_packs,
    resolve_pack,
)
from qawam_ml.rehab24 import REPO_ROOT, Repetition, load_repetitions  # noqa: E402
from qawam_ml.selective import apply_threshold, calibrate_threshold, risk_coverage_curve  # noqa: E402

DEFAULT_MODEL = REPO_ROOT / "data" / "derived" / "models" / "pose_landmarker_lite.task"
DEFAULT_OUT = REPO_ROOT / "data" / "derived" / "angle-eval"
FPS = 30.0


@dataclass(frozen=True)
class FrameRow:
    split: str
    person_id: int
    exercise_id: int
    pack_id: str
    video_id: str
    repetition_number: int
    correctness: int
    camera: int
    view: str
    side: str
    angle: str
    frame: int
    detected: int
    in_frame: int
    visibility_min: float
    gt_deg: float | None
    mp_deg: float | None
    inference_ms: float

    @property
    def abs_error(self) -> float | None:
        if self.gt_deg is None or self.mp_deg is None:
            return None
        return abs(self.mp_deg - self.gt_deg)


# ---------------------------------------------------------------- pure helpers


def pack_for_exercise(packs: Mapping[str, Mapping[str, Any]], exercise_id: int) -> Mapping[str, Any]:
    for pack in packs.values():
        if pack.get("datasetMapping", {}).get("rehab24_6_exercise_id") == exercise_id:
            return pack
    raise KeyError(f"no pack maps to REHAB24-6 exercise {exercise_id}")


def sides_for_rep(pack: Mapping[str, Any], exercise_subtype: str) -> list[str]:
    """Which side(s) to evaluate: both for squat, the labelled leg otherwise."""
    if pack["sides"] == "both":
        return ["left", "right"]
    subtype = exercise_subtype.lower()
    if "left" in subtype:
        return ["left"]
    if "right" in subtype:
        return ["right"]
    return ["left", "right"]


def needed_frames(reps: Iterable[Repetition], n_frames: int) -> dict[int, list[Repetition]]:
    """Frame index -> repetitions covering it (inclusive bounds, clipped)."""
    frames: dict[int, list[Repetition]] = defaultdict(list)
    for rep in reps:
        for index in range(max(0, rep.first_frame), min(rep.last_frame, n_frames - 1) + 1):
            frames[index].append(rep)
    return dict(frames)


def gt_points(joints_frame: np.ndarray) -> dict[str, tuple[float, float]]:
    return {
        name: (float(joints_frame[index, 0]), float(joints_frame[index, 1]))
        for name, index in REHAB24_JOINT_FOR_LANDMARK.items()
    }


def mp_points(landmarks: Sequence[Any], width: int, height: int) -> tuple[dict[str, tuple[float, float]], dict[str, float], dict[str, bool]]:
    points: dict[str, tuple[float, float]] = {}
    visibility: dict[str, float] = {}
    inside: dict[str, bool] = {}
    for name, index in MEDIAPIPE_INDEX.items():
        mark = landmarks[index]
        points[name] = (float(mark.x) * width, float(mark.y) * height)
        vis = getattr(mark, "visibility", None)
        visibility[name] = float(vis) if vis is not None else 0.0
        inside[name] = 0.0 <= float(mark.x) <= 1.0 and 0.0 <= float(mark.y) <= 1.0
    return points, visibility, inside


def percentile(values: Sequence[float], q: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=float), q)) if values else math.nan


def rep_units(rows: Sequence[FrameRow], primary: Mapping[str, str], tolerance_deg: float) -> list[dict[str, Any]]:
    """Aggregate the primary angle per (rep, camera, side) into gate units."""
    groups: dict[tuple, list[FrameRow]] = defaultdict(list)
    for row in rows:
        if row.angle != primary[row.pack_id]:
            continue
        key = (row.split, row.person_id, row.exercise_id, row.pack_id, row.video_id, row.repetition_number, row.camera, row.view, row.side, row.correctness)
        groups[key].append(row)
    units: list[dict[str, Any]] = []
    for key, items in sorted(groups.items()):
        split, person, exercise, pack_id, video, rep, camera, view, side, correctness = key
        errors = [r.abs_error for r in items if r.abs_error is not None]
        gt = [r.gt_deg for r in items if r.gt_deg is not None]
        mp = [r.mp_deg for r in items if r.mp_deg is not None]
        detected = sum(r.detected for r in items) / len(items)
        confidence = statistics.fmean(r.visibility_min if r.detected and r.in_frame else 0.0 for r in items)
        mae = statistics.fmean(errors) if errors else math.nan
        rom_error = (max(mp) - min(mp)) - (max(gt) - min(gt)) if mp and gt else math.nan
        wrong = int(not errors or mae > tolerance_deg or detected < 0.5)
        units.append(
            {
                "split": split,
                "person_id": person,
                "exercise_id": exercise,
                "pack_id": pack_id,
                "video_id": video,
                "repetition_number": rep,
                "correctness": correctness,
                "camera": camera,
                "view": view,
                "side": side,
                "frames": len(items),
                "detection_rate": round(detected, 4),
                "confidence": round(confidence, 4),
                "mae_deg": round(mae, 3) if errors else "",
                "rom_gt_deg": round(max(gt) - min(gt), 3) if gt else "",
                "rom_error_deg": round(rom_error, 3) if not math.isnan(rom_error) else "",
                "wrong": wrong,
            }
        )
    return units


def error_table(rows: Sequence[FrameRow], primary: Mapping[str, str]) -> list[dict[str, Any]]:
    groups: dict[tuple, list[float]] = defaultdict(list)
    detected: dict[tuple, list[int]] = defaultdict(list)
    for row in rows:
        if row.angle != primary[row.pack_id]:
            continue
        key = (row.split, row.exercise_id, row.camera, row.view)
        detected[key].append(row.detected)
        if row.abs_error is not None:
            groups[key].append(row.abs_error)
    table = []
    for key in sorted(detected):
        errs = groups.get(key, [])
        split, exercise, camera, view = key
        table.append(
            {
                "split": split,
                "exercise_id": exercise,
                "camera": camera,
                "view": view,
                "frames": len(detected[key]),
                "detected_pct": round(100 * statistics.fmean(detected[key]), 1),
                "mae_deg": round(statistics.fmean(errs), 2) if errs else None,
                "median_deg": round(statistics.median(errs), 2) if errs else None,
                "p90_deg": round(percentile(errs, 90), 2) if errs else None,
            }
        )
    return table


def subject_table(units: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple, list[float]] = defaultdict(list)
    for unit in units:
        if unit["mae_deg"] != "":
            groups[(unit["split"], unit["person_id"], unit["exercise_id"])].append(float(unit["mae_deg"]))
    return [
        {"split": s, "person_id": p, "exercise_id": e, "reps": len(v), "rep_mae_deg": round(statistics.fmean(v), 2)}
        for (s, p, e), v in sorted(groups.items())
    ]


def gate_report(units: Sequence[Mapping[str, Any]], alpha: float, delta: float) -> dict[str, Any]:
    train = [u for u in units if u["split"] == "train"]
    val = [u for u in units if u["split"] == "validation"]
    report: dict[str, Any] = {"alpha": alpha, "delta": delta}
    if not train:
        return report | {"note": "no train units; gate not calibrated"}
    calibration = calibrate_threshold([u["confidence"] for u in train], [u["wrong"] for u in train], alpha, delta)
    report["threshold"] = calibration.threshold
    report["train"] = {
        "units": len(train),
        "always_speak_risk": round(statistics.fmean(u["wrong"] for u in train), 4),
        "coverage": round(calibration.coverage, 4),
        "risk": None if calibration.abstain_always else round(calibration.empirical_risk, 4),
    }
    if val:
        point = apply_threshold([u["confidence"] for u in val], [u["wrong"] for u in val], calibration.threshold)
        report["validation"] = {
            "units": len(val),
            "always_speak_risk": round(statistics.fmean(u["wrong"] for u in val), 4),
            "coverage": round(point.coverage, 4),
            "risk": None if point.accepted == 0 else round(point.risk, 4),
        }
    return report


# ------------------------------------------------------------------ inference


def _landmarker(model: Path):
    import mediapipe as mp

    options = mp.tasks.vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),
        running_mode=mp.tasks.vision.RunningMode.VIDEO,
        num_poses=1,
    )
    return mp, mp.tasks.vision.PoseLandmarker.create_from_options(options)


def evaluate_video(
    split: str,
    camera: int,
    reps: list[Repetition],
    packs: Mapping[str, Mapping[str, Any]],
    model: Path,
) -> list[FrameRow]:
    import cv2

    first = reps[0]
    video_path = first.video_c17_30fps if camera == 17 else first.video_c18_30fps_transposed
    joints_path = first.joints_c17_30fps if camera == 17 else first.joints_c18_30fps
    joints = np.load(joints_path)
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"cannot open video: {video_path}")
    n_video = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    frames = needed_frames(reps, min(n_video, joints.shape[0]))
    resolved: dict[tuple[str, str], ResolvedPack] = {}
    rows: list[FrameRow] = []
    mp, landmarker = _landmarker(model)
    try:
        last = max(frames) if frames else -1
        index = 0
        while index <= last:
            if index not in frames:
                if not capture.grab():
                    break
                index += 1
                continue
            ok, frame = capture.read()
            if not ok or frame is None:
                break
            height, width = frame.shape[:2]
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            started = time.perf_counter()
            result = landmarker.detect_for_video(image, int(round(index * 1000 / FPS)))
            elapsed = (time.perf_counter() - started) * 1000
            detected = bool(result.pose_landmarks)
            if detected:
                mp_pts, vis, inside = mp_points(result.pose_landmarks[0], width, height)
            gt_pts = gt_points(joints[index])
            for rep in frames[index]:
                pack = pack_for_exercise(packs, rep.exercise_id)
                view = view_for_camera(rep.cam17_orientation, camera)
                for side in sides_for_rep(pack, rep.exercise_subtype):
                    key = (pack["packId"], side)
                    if key not in resolved:
                        resolved[key] = resolve_pack(pack, side)  # type: ignore[arg-type]
                    rp = resolved[key]
                    for angle in rp.angles:
                        names = angle.landmarks
                        rows.append(
                            FrameRow(
                                split=split,
                                person_id=rep.person_id,
                                exercise_id=rep.exercise_id,
                                pack_id=rp.pack_id,
                                video_id=rep.video_id,
                                repetition_number=rep.repetition_number,
                                correctness=rep.correctness,
                                camera=camera,
                                view=view,
                                side=side,
                                angle=angle.name,
                                frame=index,
                                detected=int(detected),
                                in_frame=int(detected and all(inside[n] for n in names)),
                                visibility_min=min(vis[n] for n in names) if detected else 0.0,
                                gt_deg=compute_angle(gt_pts, angle),
                                mp_deg=compute_angle(mp_pts, angle) if detected else None,
                                inference_ms=elapsed,
                            )
                        )
            index += 1
    finally:
        landmarker.close()
        capture.release()
    return rows


# ------------------------------------------------------------------------ CLI


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _markdown(table: Sequence[Mapping[str, Any]]) -> str:
    if not table:
        return "_none_\n"
    keys = list(table[0])
    lines = ["| " + " | ".join(keys) + " |", "| " + " | ".join("---" for _ in keys) + " |"]
    lines += ["| " + " | ".join("" if row[k] is None else str(row[k]) for k in keys) + " |" for row in table]
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--exercises", type=int, nargs="+", default=[6], help="REHAB24-6 exercise ids (4 leg abduction, 5 lunge, 6 squat)")
    parser.add_argument("--splits", nargs="+", default=["train", "validation"], choices=["train", "validation", "test"])
    parser.add_argument("--cameras", type=int, nargs="+", default=[17, 18], choices=[17, 18])
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--dataset-root", type=Path, default=None)
    parser.add_argument("--tolerance-deg", type=float, default=10.0, help="evaluation-only: a rep whose mean angle error exceeds this counts as a wrong measurement")
    parser.add_argument("--alpha", type=float, default=0.1, help="target false-cue rate for the gate")
    parser.add_argument("--delta", type=float, default=0.1, help="allowed probability that the guarantee fails")
    parser.add_argument("--max-videos", type=int, default=None, help="quick smoke run")
    parser.add_argument("--final", action="store_true", help="required to touch the sealed test split; access is logged")
    args = parser.parse_args(argv)

    if not args.model.exists():
        parser.error(f"model not found: {args.model}")
    packs = load_packs()
    primary = {pid: p["primaryAngle"] for pid, p in packs.items()}
    rows: list[FrameRow] = []
    videos_done = 0
    for split in args.splits:
        for camera in args.cameras:
            reps = load_repetitions(
                split,  # type: ignore[arg-type]
                dataset_root=args.dataset_root,
                filter_name="gt_quality",
                cam=camera,
                final=args.final,
                caller="ml/eval/angle_eval.py",
            )
            reps = [r for r in reps if r.exercise_id in args.exercises]
            by_video: dict[str, list[Repetition]] = defaultdict(list)
            for rep in reps:
                by_video[rep.video_id].append(rep)
            for video_id, video_reps in sorted(by_video.items()):
                if args.max_videos is not None and videos_done >= args.max_videos:
                    break
                started = time.perf_counter()
                new_rows = evaluate_video(split, camera, video_reps, packs, args.model)
                rows.extend(new_rows)
                videos_done += 1
                print(f"{split} cam{camera} {video_id}: {len(video_reps)} reps, {len(new_rows)} rows, {time.perf_counter() - started:.1f}s", flush=True)

    args.out.mkdir(parents=True, exist_ok=True)
    frame_dicts = [
        {**{k: getattr(r, k) for k in FrameRow.__dataclass_fields__}, "abs_error": r.abs_error}
        for r in rows
    ]
    _write_csv(args.out / "frames.csv", frame_dicts)
    units = rep_units(rows, primary, args.tolerance_deg)
    _write_csv(args.out / "reps.csv", units)
    errors = error_table(rows, primary)
    subjects = subject_table(units)
    gate = gate_report(units, args.alpha, args.delta)
    curves = {
        split: [p.__dict__ for p in risk_coverage_curve([u["confidence"] for u in units if u["split"] == split], [u["wrong"] for u in units if u["split"] == split])]
        for split in {u["split"] for u in units}
    }
    latency = [r.inference_ms for r in rows]
    summary = {
        "model": args.model.name,
        "exercises": args.exercises,
        "splits": args.splits,
        "tolerance_deg": args.tolerance_deg,
        "frames": len({(r.video_id, r.camera, r.frame) for r in rows}),
        "units": len(units),
        "median_inference_ms": round(statistics.median(latency), 1) if latency else None,
        "error_by_view": errors,
        "subjects": subjects,
        "gate": gate,
        "risk_coverage": curves,
    }
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    md = [
        "# Joint-angle baseline (generated by ml/eval/angle_eval.py)\n",
        f"Model `{args.model.name}`, exercises {args.exercises}, splits {args.splits}, every frame of every `gt_quality` repetition. Primary angle of each pack; 2D angle vs the dataset's projected 2D skeleton. Not a clinical accuracy claim.\n",
        "## Error by exercise, camera and view (frames)\n",
        _markdown(errors),
        "## Per subject (mean of rep MAE)\n",
        _markdown(subjects),
        f"## Confidence gate (calibrated on train, applied to validation)\n\nUnit = repetition x camera x side. Wrong = rep mean error > {args.tolerance_deg} deg (evaluation tolerance, not clinical) or pose detected on < 50% of frames. Target false-cue rate alpha = {args.alpha}, delta = {args.delta}.\n",
        "```json\n" + json.dumps(gate, indent=2) + "\n```\n",
        f"Median inference: {summary['median_inference_ms']} ms per frame on this machine.\n",
    ]
    (args.out / "summary.md").write_text("\n".join(md), encoding="utf-8")
    print(f"wrote {args.out / 'summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Personal vs universal reference on REHAB26-ViewAngles MediaPipe skeletons.

REHAB26-ViewAngles (Zenodo 23018128, CC BY-NC 4.0) films 5 people with 3
synchronised cameras while they stand at orientations 0-90 deg, giving
viewing angles from frontal (0) to profile (+/-90). It ships MediaPipe Pose
landmarks per camera and labels each rep correct (1) or incorrect (5) with
the intended error type.

This repeats ``reference_eval.py`` on real pose-estimator output instead of
motion capture, leave-one-person-out, and breaks results down by viewing
angle and by error type. The viewing-angle table is what the setup wizard
should follow.

2D landmarks are normalised; they are scaled by --width/--height (default
1920x1080, an assumption to confirm against the videos) before angles are
computed.

  py -3.14 ml\\eval\\rehab26_eval.py --root C:\\path\\to\\rehab26
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

EVAL_DIR = Path(__file__).resolve().parent
ML_ROOT = EVAL_DIR.parent
for path in (str(ML_ROOT), str(EVAL_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

from qawam_ml.packs import MEDIAPIPE_INDEX, compute_angle, load_packs, resolve_pack  # noqa: E402
from reference_eval import METHODS, RepCurves, roc_auc, score_reps, subject_bootstrap  # noqa: E402

DEFAULT_OUT = ML_ROOT.parent / "data" / "derived" / "rehab26-eval"


@dataclass(frozen=True)
class Rehab26Rep:
    """Duck-types the fields reference_eval uses from a REHAB24-6 Repetition."""

    video_id: str
    person_id: str
    exercise_id: int
    repetition_number: int
    first_frame: int
    last_frame: int
    orientation: int
    correctness: int
    error: str
    exercise_subtype: str

    @property
    def cam17_orientation(self) -> str:  # grouping key used by reference_eval
        return str(self.orientation)


def viewing_angle(orientation: int, camera: int) -> int:
    """Signed viewing angle per the dataset: cam1 -o, cam2 45-o, cam3 90-o."""
    return {1: -orientation, 2: 45 - orientation, 3: 90 - orientation}[camera]


def view_bucket(angle: int) -> str:
    a = abs(angle)
    if a <= 15:
        return "frontal 0-15"
    if a <= 35:
        return "oblique 20-35"
    if a <= 55:
        return "half-profile 40-55"
    if a <= 75:
        return "oblique 60-75"
    return "profile 80-90"


def read_reps(root: Path, exercise_id: int) -> list[Rehab26Rep]:
    reps = []
    with (root / "Segmentation.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            if int(row["exercise_id"]) != exercise_id:
                continue
            reps.append(
                Rehab26Rep(
                    video_id=row["video_id"],
                    person_id=row["person"],
                    exercise_id=exercise_id,
                    repetition_number=int(row["repetition_number"]),
                    first_frame=int(row["first_frame"]),
                    last_frame=int(row["last_frame"]),
                    orientation=int(row["person_orientation"]),
                    correctness=1 if row["correctness_score"].strip() == "1" else 0,
                    error=row["error_description"].strip() or "CORRECT",
                    exercise_subtype=row["exercise_subtype"].strip(),
                )
            )
    return reps


def build_curves(
    root: Path,
    pack: Mapping[str, Any],
    exercise_id: int,
    width: float,
    height: float,
    min_visibility: float,
) -> list[RepCurves]:
    reps = read_reps(root, exercise_id)
    folder = root / "mp" / "mediapipe" / f"ex{exercise_id}"
    sides = ["left", "right"] if pack["sides"] == "both" else None
    items: list[RepCurves] = []
    cache: dict[Path, np.ndarray] = {}
    for rep in reps:
        rep_sides = sides or (["left"] if "left" in rep.exercise_subtype else ["right"])
        for camera in (1, 2, 3):
            path = folder / f"{rep.video_id}_cam{camera}_2d.npy"
            if path not in cache:
                cache[path] = np.load(path)
            marks = cache[path]
            last = min(rep.last_frame, marks.shape[0] - 1)
            if last - rep.first_frame < 5:
                continue
            angle_value = viewing_angle(rep.orientation, camera)
            item = RepCurves("loso", rep, camera, view_bucket(angle_value), pack["packId"], pack["primaryAngle"])  # type: ignore[arg-type]
            item.viewing_angle = angle_value  # type: ignore[attr-defined]
            visibility = []
            for side in rep_sides:
                resolved = resolve_pack(pack, side)  # type: ignore[arg-type]
                for angle in resolved.angles:
                    idx = [MEDIAPIPE_INDEX[n] for n in angle.landmarks]
                    segment = marks[rep.first_frame : last + 1][:, idx, :]
                    visibility.append(float(segment[:, :, 3].min(axis=1).mean()))
                    values = []
                    for frame in segment:
                        points = {n: (frame[k, 0] * width, frame[k, 1] * height) for k, n in enumerate(angle.landmarks)}
                        values.append(compute_angle(points, angle))
                    if any(v is None for v in values):
                        continue
                    label = side if pack["sides"] == "both" else "moving"
                    item.curves[f"{label}:{angle.name}"] = np.asarray(values, dtype=float)
            item.visibility = float(np.mean(visibility)) if visibility else 0.0  # type: ignore[attr-defined]
            if item.curves and item.visibility >= min_visibility:  # type: ignore[attr-defined]
                items.append(item)
    return items


def loso_scores(items: Sequence[RepCurves]) -> list[dict[str, Any]]:
    """Score each person with templates built from the other four."""
    scored: list[dict[str, Any]] = []
    lookup = {(i.rep.video_id, i.rep.cam17_orientation, i.rep.repetition_number, i.camera): i for i in items}
    for person in sorted({i.rep.person_id for i in items}):
        train = [i for i in items if i.rep.person_id != person]
        test = [i for i in items if i.rep.person_id == person]
        for row in score_reps(train, test):
            item = lookup[(row["video_id"], row["orientation"], row["repetition_number"], row["camera"])]
            row["viewing_angle"] = item.viewing_angle  # type: ignore[attr-defined]
            row["error"] = item.rep.error
            row["visibility"] = round(item.visibility, 4)  # type: ignore[attr-defined]
            scored.append(row)
    return scored


def table(scored: Sequence[Mapping[str, Any]], key: str) -> list[dict[str, Any]]:
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in scored:
        groups[str(row[key])].append(row)
        groups["all"].append(row)
    out = []
    for name, rows in sorted(groups.items()):
        labels = [r["incorrect"] for r in rows]
        entry: dict[str, Any] = {key: name, "reps": len(rows), "incorrect": sum(labels)}
        for method in METHODS:
            auc = roc_auc([r[method] for r in rows], labels)
            entry[method] = None if auc is None else round(auc, 3)
        out.append(entry)
    return out


def error_table(scored: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """AUC of personal DTW for each error type (that error vs correct reps), per view bucket."""
    out = []
    errors = sorted({r["error"] for r in scored if r["error"] != "CORRECT"})
    views = sorted({r["view"] for r in scored})
    for error in errors:
        entry: dict[str, Any] = {"error": error}
        for view in views:
            rows = [r for r in scored if r["view"] == view and r["error"] in (error, "CORRECT")]
            auc = roc_auc([r["personal_dtw"] for r in rows], [r["incorrect"] for r in rows])
            entry[view] = None if auc is None else round(auc, 2)
        out.append(entry)
    return out


def markdown(rows: Sequence[Mapping[str, Any]]) -> str:
    if not rows:
        return "_none_\n"
    keys = list(rows[0])
    lines = ["| " + " | ".join(keys) + " |", "|" + " --- |" * len(keys)]
    lines += ["| " + " | ".join("" if row[k] is None else str(row[k]) for k in keys) + " |" for row in rows]
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, required=True, help="folder with Segmentation.csv and mp/mediapipe/ex*/")
    parser.add_argument("--exercises", type=int, nargs="+", default=[6, 1])
    parser.add_argument("--width", type=float, default=1920.0)
    parser.add_argument("--height", type=float, default=1080.0)
    parser.add_argument("--min-visibility", type=float, default=0.0, help="drop rep views whose mean landmark visibility is below this")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    packs = load_packs()
    by_id = {p["datasetMapping"]["rehab26_exercise_id"]: p for p in packs.values() if "rehab26_exercise_id" in p.get("datasetMapping", {})}
    args.out.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {"width": args.width, "height": args.height, "exercises": {}}
    md = ["# REHAB26-ViewAngles: personal vs universal reference on MediaPipe skeletons\n",
          f"Leave-one-person-out over 5 people; ROC AUC for flagging incorrect reps (0.5 = chance). 2D landmarks scaled to {int(args.width)}x{int(args.height)} (assumed).\n"]
    for exercise_id in args.exercises:
        pack = by_id[exercise_id]
        items = build_curves(args.root, pack, exercise_id, args.width, args.height, args.min_visibility)
        scored = loso_scores(items)
        by_view = table(scored, "view")
        by_person = table(scored, "person_id")
        errors = error_table(scored)
        boot = [subject_bootstrap(scored, "personal_dtw", b) for b in ("population_dtw", "population_peak")]
        summary["exercises"][pack["packId"]] = {"by_view": by_view, "by_person": by_person, "by_error": errors, "bootstrap": boot, "units": len(scored)}
        with (args.out / f"scores_ex{exercise_id}.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(scored[0]))
            writer.writeheader()
            writer.writerows(scored)
        md += [f"## {pack['names']['en']} ({pack['packId']}), {len(scored)} rep views\n", "By viewing angle:\n", markdown(by_view),
               "By person:\n", markdown(by_person),
               "Personal DTW, AUC per error type (that error vs correct reps) by viewing angle:\n", markdown(errors),
               "Personal DTW minus baseline (95% CI, resampling people):\n",
               markdown([{"baseline": b["baseline"], "auc_difference": b["auc_difference"], "ci95": f"{b['ci95'][0]} to {b['ci95'][1]}"} for b in boot])]
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (args.out / "summary.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

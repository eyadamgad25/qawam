"""Does a personal reference catch incorrect reps better than a universal one?

Uses REHAB24-6 motion-capture ground truth only (no video, no pose model),
so it measures the comparison method itself, an upper bound before pose
noise. For each pack angle it builds the rep's angle curve and scores how
far the rep is from a reference; a higher score should mean "incorrect".

Methods compared (same camera view, same angles):
  personal_dtw   DTW distance to the subject's own first correct rep in the
                 same recording and orientation (what a physio would record
                 in clinic). That reference rep is excluded from scoring.
  population_dtw DTW distance to the average correct rep of the *training*
                 subjects (a universal template).
  population_peak  |peak - training mean peak| / training SD of the primary
                 angle (a universal threshold on depth).
  personal_peak  |peak - own reference peak| for the primary angle.

Labels are REHAB24-6 physio correctness (0 = incorrect). Reported metric:
ROC AUC for flagging incorrect reps, per view and per split. Validation
subjects are the headline; the sealed test split needs --final.

Mocap ground truth does not depend on room lights or bystanders, so reps
are filtered on mocap_erroneous == 0 only.

  py -3.14 ml\\eval\\reference_eval.py --exercises 6 --dataset-root C:\\Users\\eyada\\Grad_1\\data\\raw\\rehab24-6
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

ML_ROOT = Path(__file__).resolve().parents[1]
if str(ML_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_ROOT))

from qawam_ml.filters import view_for_camera  # noqa: E402
from qawam_ml.packs import compute_angle, load_packs, resolve_pack  # noqa: E402
from qawam_ml.reference import dtw_path  # noqa: E402
from qawam_ml.rehab24 import REPO_ROOT, Repetition, load_repetitions  # noqa: E402

DEFAULT_OUT = REPO_ROOT / "data" / "derived" / "reference-eval"
TEMPLATE_POINTS = 100
METHODS = ("personal_dtw", "population_dtw", "population_peak", "personal_peak")


@dataclass
class RepCurves:
    split: str
    rep: Repetition
    camera: int
    view: str
    pack_id: str
    primary: str
    curves: dict[str, np.ndarray] = field(default_factory=dict)  # "<side|moving>:<angle>" -> degrees

    @property
    def incorrect(self) -> int:
        return int(self.rep.correctness == 0)

    @property
    def group(self) -> tuple:
        return (self.rep.video_id, self.rep.cam17_orientation, self.camera)


# ---------------------------------------------------------------- pure helpers


def resample(curve: np.ndarray, points: int = TEMPLATE_POINTS) -> np.ndarray:
    x_old = np.linspace(0.0, 1.0, curve.size)
    return np.interp(np.linspace(0.0, 1.0, points), x_old, curve)


def roc_auc(scores: Sequence[float], labels: Sequence[int]) -> float | None:
    """Mann-Whitney AUC: P(score of a positive > score of a negative); ties count 0.5."""
    pos = [s for s, y in zip(scores, labels) if y == 1]
    neg = [s for s, y in zip(scores, labels) if y == 0]
    if not pos or not neg:
        return None
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def curve_distance(a: Mapping[str, np.ndarray], b: Mapping[str, np.ndarray]) -> float:
    """Mean DTW absolute deviation over the curves both reps share."""
    keys = sorted(set(a) & set(b))
    if not keys:
        raise ValueError("no shared curves")
    values = []
    for key in keys:
        total, path = dtw_path(a[key], b[key], window=max(a[key].size, b[key].size) // 3)
        values.append(total / len(path))
    return float(statistics.fmean(values))


def personal_references(reps: Sequence[RepCurves]) -> dict[tuple, RepCurves]:
    """First correct rep per recording x orientation x camera."""
    refs: dict[tuple, RepCurves] = {}
    for item in sorted(reps, key=lambda r: (r.group, r.rep.repetition_number)):
        if item.rep.correctness == 1 and item.group not in refs:
            refs[item.group] = item
    return refs


def population_template(reps: Sequence[RepCurves]) -> dict[str, np.ndarray]:
    stacks: dict[str, list[np.ndarray]] = defaultdict(list)
    for item in reps:
        if item.rep.correctness == 1:
            for key, curve in item.curves.items():
                stacks[key].append(resample(curve))
    return {key: np.mean(np.stack(curves), axis=0) for key, curves in stacks.items()}


def peak(item: RepCurves) -> float:
    values = [float(curve.max()) for key, curve in item.curves.items() if key.endswith(":" + item.primary)]
    return statistics.fmean(values)


def score_reps(
    train: Sequence[RepCurves],
    evaluate: Sequence[RepCurves],
) -> list[dict[str, Any]]:
    """Score every rep in ``evaluate`` with every method; reference reps are skipped."""
    refs = personal_references(evaluate)
    by_key: dict[tuple[str, str], list[RepCurves]] = defaultdict(list)
    for item in train:
        by_key[(item.pack_id, item.view)].append(item)
    templates = {key: population_template(items) for key, items in by_key.items()}
    peak_stats = {}
    for key, items in by_key.items():
        peaks = [peak(i) for i in items if i.rep.correctness == 1]
        if len(peaks) >= 2:
            peak_stats[key] = (statistics.fmean(peaks), statistics.stdev(peaks) or 1.0)
    scored = []
    for item in evaluate:
        ref = refs.get(item.group)
        key = (item.pack_id, item.view)
        if ref is None or ref is item or key not in templates or key not in peak_stats:
            continue
        mean_peak, sd_peak = peak_stats[key]
        scored.append(
            {
                "split": item.split,
                "pack_id": item.pack_id,
                "person_id": item.rep.person_id,
                "video_id": item.rep.video_id,
                "repetition_number": item.rep.repetition_number,
                "orientation": item.rep.cam17_orientation,
                "camera": item.camera,
                "view": item.view,
                "incorrect": item.incorrect,
                "personal_dtw": curve_distance(item.curves, ref.curves),
                "population_dtw": curve_distance(item.curves, templates[key]),
                "population_peak": abs(peak(item) - mean_peak) / sd_peak,
                "personal_peak": abs(peak(item) - peak(ref)),
            }
        )
    return scored


def auc_table(scored: Sequence[Mapping[str, Any]], by: str = "view") -> list[dict[str, Any]]:
    """AUC per exercise pack, split and ``by`` column ("view" or "person_id"), plus "all"."""
    groups: dict[tuple, list[Mapping[str, Any]]] = defaultdict(list)
    for row in scored:
        groups[(row["pack_id"], row["split"], str(row[by]))].append(row)
        groups[(row["pack_id"], row["split"], "all")].append(row)
    table = []
    for (pack_id, split, key), rows in sorted(groups.items()):
        labels = [r["incorrect"] for r in rows]
        entry: dict[str, Any] = {"pack": pack_id, "split": split, by: key, "reps": len(rows), "incorrect": sum(labels)}
        for method in METHODS:
            auc = roc_auc([r[method] for r in rows], labels)
            entry[method] = None if auc is None else round(auc, 3)
        table.append(entry)
    return table


def subject_bootstrap(
    scored: Sequence[Mapping[str, Any]],
    method: str,
    baseline: str,
    resamples: int = 2000,
    seed: int = 20261028,
) -> dict[str, Any]:
    """AUC difference (method - baseline) with a 95% CI from resampling subjects."""
    by_subject: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for row in scored:
        by_subject[row["person_id"]].append(row)
    subjects = sorted(by_subject)

    def diff(rows: Sequence[Mapping[str, Any]]) -> float | None:
        labels = [r["incorrect"] for r in rows]
        a = roc_auc([r[method] for r in rows], labels)
        b = roc_auc([r[baseline] for r in rows], labels)
        return None if a is None or b is None else a - b

    point = diff(scored)
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(resamples):
        picked = rng.integers(0, len(subjects), size=len(subjects))
        value = diff([row for i in picked for row in by_subject[subjects[int(i)]]])
        if value is not None:
            draws.append(value)
    low, high = (float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))) if draws else (None, None)
    return {
        "method": method,
        "baseline": baseline,
        "subjects": len(subjects),
        "auc_difference": None if point is None else round(point, 3),
        "ci95": [None if low is None else round(low, 3), None if high is None else round(high, 3)],
    }


# ------------------------------------------------------------------- loading


def build_curves(
    split: str,
    exercises: Sequence[int],
    dataset_root: Path | None,
    csv_path: Path | None,
    final: bool,
) -> tuple[list[RepCurves], list[str]]:
    packs = load_packs()
    by_exercise = {
        p["datasetMapping"]["rehab24_6_exercise_id"]: p for p in packs.values() if "datasetMapping" in p
    }
    reps = load_repetitions(
        split,  # type: ignore[arg-type]
        dataset_root=dataset_root,
        csv_path=csv_path,
        filter_name="none",
        final=final,
        caller="ml/eval/reference_eval.py",
    )
    reps = [r for r in reps if r.exercise_id in exercises and r.mocap_erroneous == 0]
    out: list[RepCurves] = []
    missing: list[str] = []
    cache: dict[Path, np.ndarray] = {}
    for rep in reps:
        pack = by_exercise[rep.exercise_id]
        subtype = rep.exercise_subtype.lower()
        sides = ["left", "right"] if pack["sides"] == "both" or not subtype else (["left"] if "left" in subtype else ["right"])
        for camera, path in ((17, rep.joints_c17_30fps), (18, rep.joints_c18_30fps)):
            if not path.exists():
                missing.append(path.name)
                continue
            if path not in cache:
                cache[path] = np.load(path)
            joints = cache[path]
            last = min(rep.last_frame, joints.shape[0] - 1)
            if last - rep.first_frame < 5:
                continue
            item = RepCurves(split, rep, camera, view_for_camera(rep.cam17_orientation, camera), pack["packId"], pack["primaryAngle"])
            for side in sides:
                resolved = resolve_pack(pack, side)  # type: ignore[arg-type]
                for angle in resolved.angles:
                    from qawam_ml.packs import REHAB24_JOINT_FOR_LANDMARK as J

                    values = []
                    for frame in range(rep.first_frame, last + 1):
                        pts = {n: tuple(joints[frame, J[n]]) for n in angle.landmarks}
                        values.append(compute_angle(pts, angle))
                    if any(v is None for v in values):
                        continue
                    label = side if pack["sides"] == "both" else "moving"
                    item.curves[f"{label}:{angle.name}"] = np.asarray(values, dtype=float)
            if item.curves:
                out.append(item)
    return out, sorted(set(missing))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--exercises", type=int, nargs="+", default=[6])
    parser.add_argument("--dataset-root", type=Path, default=None)
    parser.add_argument("--csv", type=Path, default=None, help="Segmentation.csv if not in the dataset root")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--final", action="store_true", help="also score the sealed test split (logged)")
    args = parser.parse_args(argv)

    train, missing = build_curves("train", args.exercises, args.dataset_root, args.csv, False)
    validation, missing_v = build_curves("validation", args.exercises, args.dataset_root, args.csv, False)
    missing += missing_v
    scored = score_reps(train, validation)
    # Training subjects, scored leave-one-subject-out so no subject is in its own template.
    for person in sorted({r.rep.person_id for r in train}):
        others = [r for r in train if r.rep.person_id != person]
        scored += score_reps(others, [r for r in train if r.rep.person_id == person])
    if args.final:
        test, _ = build_curves("test", args.exercises, args.dataset_root, args.csv, True)
        scored += score_reps(train + validation, test)

    table = auc_table(scored)
    per_subject = auc_table(scored, by="person_id")
    pooled = [r for r in scored if r["split"] in ("train", "validation")]
    bootstrap = [
        {"pack": pack_id, **subject_bootstrap([r for r in pooled if r["pack_id"] == pack_id], "personal_dtw", baseline)}
        for pack_id in sorted({r["pack_id"] for r in pooled})
        for baseline in ("population_dtw", "population_peak")
    ]
    subjects = sorted({(r["split"], r["person_id"]) for r in scored})
    summary = {
        "exercises": args.exercises,
        "methods": list(METHODS),
        "subjects": [f"{s}:{p}" for s, p in subjects],
        "missing_files": missing,
        "auc": table,
        "auc_by_subject": per_subject,
        "bootstrap": bootstrap,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with (args.out / "scores.csv").open("w", encoding="utf-8") as handle:
        if scored:
            keys = list(scored[0])
            handle.write(",".join(keys) + "\n")
            for row in scored:
                handle.write(",".join(str(row[k]) for k in keys) + "\n")
    def markdown(rows: Sequence[Mapping[str, Any]], key: str) -> list[str]:
        out = ["| pack | split | " + key + " | reps | incorrect | " + " | ".join(METHODS) + " |", "|" + " --- |" * (5 + len(METHODS))]
        out += ["| " + " | ".join(str(row[k]) for k in ("pack", "split", key, "reps", "incorrect", *METHODS)) + " |" for row in rows]
        return out

    lines = markdown(table, "view") + ["", "By subject (all views):", ""] + markdown(per_subject, "person_id")
    lines += ["", "Personal DTW minus baseline, AUC difference with 95% CI from resampling subjects (train LOSO + validation pooled):", ""]
    lines += ["| pack | baseline | subjects | AUC difference | 95% CI |", "| --- | --- | --- | --- | --- |"]
    lines += [f"| {b['pack']} | {b['baseline']} | {b['subjects']} | {b['auc_difference']} | {b['ci95'][0]} to {b['ci95'][1]} |" for b in bootstrap]
    md = "\n".join(
        [
            "# Personal vs universal reference (generated by ml/eval/reference_eval.py)\n",
            f"Exercises {args.exercises}; mocap 2D ground truth; ROC AUC for flagging physio-labelled incorrect reps (0.5 = chance). Train rows are leave-one-subject-out.\n",
            "\n".join(lines),
            "",
            f"Subjects: {', '.join(summary['subjects'])}. Missing files skipped: {len(missing)}.",
        ]
    )
    (args.out / "summary.md").write_text(md + "\n", encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

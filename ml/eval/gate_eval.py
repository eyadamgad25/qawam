"""Does a richer confidence score let the gate speak more often, safely?

Reads the output of ``angle_eval.py --save-landmarks`` (reps.csv plus
landmarks/*.npz), computes the quality features in qawam_ml/quality.py for
every gate unit (repetition x camera x side), and compares three scores:

  visibility   mean landmark visibility (the gate we had)
  geometry     the new features without visibility
  combined     all features

Protocol (train + validation subjects only; the sealed test split is never
read). With 5 people, every number is leave-one-person-out:

  * AUROC: for each person, fit the gate model on the other four and score
    the held-out person. Higher score = measurement more likely right.
  * Gate: for each held-out person, calibrate the threshold with
    Learn-then-Test on the other four people's out-of-fold scores (inner
    cross-fitting, so the threshold never sees a model trained on its own
    calibration rows), then apply model + threshold to the held-out person.
    Reported: share of reps the coach speaks on (coverage) and the share of
    those that were wrong measurements (false-cue rate).

The final model is fitted on all five people and written to gate_model.json
with its threshold, ready to port to the phone. It is research output, not a
clinical setting.

Caveat: units from the same person and rep are not independent, so the
binomial guarantee is approximate; that is why results are reported per
held-out person.

  python ml/eval/gate_eval.py --angle-eval data/derived/angle-eval --dataset-root <rehab24-6>
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

EVAL_DIR = Path(__file__).resolve().parent
ML_ROOT = EVAL_DIR.parent
for path in (str(ML_ROOT), str(EVAL_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

from qawam_ml.packs import load_packs, resolve_pack  # noqa: E402
from qawam_ml.quality import FEATURES, LogisticGate, rep_features, segment  # noqa: E402
from qawam_ml.rehab24 import load_repetitions  # noqa: E402
from qawam_ml.selective import apply_threshold, calibrate_threshold, clopper_pearson_upper, risk_coverage_curve  # noqa: E402

GEOMETRY = tuple(f for f in FEATURES if not f.startswith("vis_"))
METHODS: dict[str, tuple[str, ...] | None] = {"visibility": None, "view": None, "geometry": GEOMETRY, "combined": FEATURES}
_PACK_VIEW = {pid: p["view"] for pid, p in load_packs().items()}


def view_score(unit: Mapping[str, Any]) -> float:
    """How well the estimated view matches the view the pack asks for.

    No learning: side packs want frontalness near 0, front packs want it
    high. Only the threshold is calibrated."""
    frontal = float(unit["frontalness"])
    return -frontal if _PACK_VIEW.get(unit["pack_id"]) == "side" else frontal


def auroc(score: Sequence[float], correct: Sequence[int]) -> float | None:
    """P(score of a correct measurement > score of a wrong one)."""
    s = np.asarray(score, dtype=float)
    y = np.asarray(correct, dtype=int)
    pos, neg = s[y == 1], s[y == 0]
    if not pos.size or not neg.size:
        return None
    wins = (pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum()
    return float(wins / (pos.size * neg.size))


def aurc(score: Sequence[float], wrong: Sequence[int]) -> float:
    """Area under the risk-coverage curve (lower is better)."""
    points = risk_coverage_curve(score, wrong)
    cov = [0.0] + [p.coverage for p in points]
    risk = [points[0].risk] + [p.risk for p in points]
    return float(sum((cov[i] - cov[i - 1]) * (risk[i] + risk[i - 1]) / 2 for i in range(1, len(cov))))


# ------------------------------------------------------------------ labels


def calibrated_labels(angle_eval_dir: Path, tolerance_deg: float) -> dict[tuple, dict[str, Any]]:
    """Error after a one-rep offset calibration, per gate unit.

    MediaPipe's knee angle differs from motion capture by a steady offset
    that depends on the person and the camera. Qawam compares home reps with
    a reference recorded by the same phone pipeline, so a steady offset
    cancels; for absolute numbers the physio can read a goniometer once in
    clinic. This simulates that: the first repetition of each recording x
    camera x side sets the offset (mean signed error), and the remaining
    reps are scored after subtracting it. Calibration reps are marked so
    they are left out of the evaluation.
    """
    packs = load_packs()
    primary = {pid: p["primaryAngle"] for pid, p in packs.items()}
    signed: dict[tuple, list[float]] = defaultdict(list)
    with (angle_eval_dir / "frames.csv").open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["split"] not in ("train", "validation") or row["angle"] != primary[row["pack_id"]]:
                continue
            if row["mp_deg"] == "" or row["gt_deg"] == "":
                continue
            key = (row["video_id"], int(row["repetition_number"]), int(row["camera"]), row["side"])
            signed[key].append(float(row["mp_deg"]) - float(row["gt_deg"]))
    groups: dict[tuple, list[int]] = defaultdict(list)
    for video, rep, cam, side in signed:
        groups[(video, cam, side)].append(rep)
    out: dict[tuple, dict[str, Any]] = {}
    for (video, cam, side), reps in groups.items():
        reps.sort()
        offset = statistics.fmean(signed[(video, reps[0], cam, side)])
        for rep in reps:
            errors = np.abs(np.asarray(signed[(video, rep, cam, side)]) - offset)
            out[(video, rep, cam, side)] = {
                "calibration_rep": int(rep == reps[0]),
                "cal_offset_deg": round(offset, 3),
                "cal_mae_deg": round(float(errors.mean()), 3),
                "wrong_calibrated": int(errors.mean() > tolerance_deg),
            }
    return out


# ------------------------------------------------------------------ features


def load_units(angle_eval_dir: Path, dataset_root: Path | None) -> list[dict[str, Any]]:
    """Join reps.csv with landmark features. Only train/validation rows."""
    packs = load_packs()
    units = [u for u in csv.DictReader((angle_eval_dir / "reps.csv").open(encoding="utf-8")) if u["split"] in ("train", "validation")]
    bounds: dict[tuple[str, int], tuple[int, int]] = {}
    for split in ("train", "validation"):
        for cam in (17, 18):
            for rep in load_repetitions(split, dataset_root=dataset_root, filter_name="gt_quality", cam=cam, caller="ml/eval/gate_eval.py"):  # type: ignore[arg-type]
                bounds[(rep.video_id, rep.repetition_number)] = (rep.first_frame, rep.last_frame)
    cache: dict[Path, tuple[np.ndarray, np.ndarray]] = {}
    out = []
    for unit in units:
        path = angle_eval_dir / "landmarks" / f"{unit['video_id']}_cam{unit['camera']}.npz"
        if not path.exists():
            continue
        if path not in cache:
            data = np.load(path)
            cache[path] = (data["frames"], data["marks"].astype(float))
        frames, marks = cache[path]
        first, last = bounds[(unit["video_id"], int(unit["repetition_number"]))]
        resolved = resolve_pack(packs[unit["pack_id"]], unit["side"])  # type: ignore[arg-type]
        features = rep_features(segment(frames, marks, first, last), resolved)
        out.append({**unit, **{k: round(v, 5) for k, v in features.items()}, "person_id": int(unit["person_id"]), "wrong": int(unit["wrong"])})
    return out


# ------------------------------------------------------------------- scoring


def fit_score(train: Sequence[Mapping[str, Any]], test: Sequence[Mapping[str, Any]], method: str, l2: float) -> np.ndarray:
    features = METHODS[method]
    if method == "view":
        return np.asarray([view_score(u) for u in test])
    if features is None:
        return np.asarray([float(u["vis_mean"]) for u in test])
    model = LogisticGate(features, l2=l2).fit(train, [1 - u["wrong"] for u in train])  # type: ignore[arg-type]
    return model.predict(test)  # type: ignore[arg-type]


def out_of_fold(units: Sequence[Mapping[str, Any]], method: str, l2: float) -> np.ndarray:
    """Leave-one-person-out scores for every unit."""
    scores = np.zeros(len(units))
    for person in sorted({u["person_id"] for u in units}):
        idx = [i for i, u in enumerate(units) if u["person_id"] == person]
        train = [u for u in units if u["person_id"] != person]
        scores[idx] = fit_score(train, [units[i] for i in idx], method, l2)
    return scores


PROCEDURE = "fixed_sequence"


def nested_gate(units: Sequence[Mapping[str, Any]], method: str, alpha: float, delta: float, l2: float, per_pack: bool = False) -> dict[str, Any]:
    """Per held-out person: threshold from the others' out-of-fold scores.

    With per_pack, each exercise pack gets its own threshold (and Bonferroni
    over packs is not applied: each pack's guarantee is separate)."""
    if per_pack:
        results = [nested_gate([u for u in units if u["pack_id"] == pack], method, alpha, delta, l2) for pack in sorted({u["pack_id"] for u in units})]
        n = sum(sum(p["units"] for p in r["per_person"]) for r in results)
        accepted = sum(round(r["coverage"] * sum(p["units"] for p in r["per_person"])) for r in results)
        wrong = sum(r["_wrong"] for r in results)
        return {
            "method": method + " (per pack)",
            "alpha": alpha,
            "coverage": round(accepted / n, 3),
            "false_cue_rate": None if accepted == 0 else round(wrong / accepted, 3),
            "people_over_alpha": max(r["people_over_alpha"] for r in results),
            "per_pack": {pack: {k: r[k] for k in ("coverage", "false_cue_rate")} for pack, r in zip(sorted({u["pack_id"] for u in units}), results)},
            "per_person": [p for r in results for p in r["per_person"]],
            "_wrong": wrong,
        }
    per_person = []
    accepted = wrong_accepted = total = 0
    for person in sorted({u["person_id"] for u in units}):
        held = [u for u in units if u["person_id"] == person]
        others = [u for u in units if u["person_id"] != person]
        calib_scores = out_of_fold(others, method, l2)
        calibration = calibrate_threshold(calib_scores, [u["wrong"] for u in others], alpha, delta, procedure=PROCEDURE)
        scores = fit_score(others, held, method, l2)
        point = apply_threshold(scores, [u["wrong"] for u in held], calibration.threshold)
        per_person.append(
            {
                "person_id": person,
                "units": len(held),
                "always_speak_risk": round(statistics.fmean(u["wrong"] for u in held), 3),
                "coverage": round(point.coverage, 3),
                "false_cue_rate": None if point.accepted == 0 else round(point.risk, 3),
            }
        )
        accepted += point.accepted
        wrong_accepted += point.wrong
        total += len(held)
    return {
        "method": method,
        "alpha": alpha,
        "coverage": round(accepted / total, 3),
        "false_cue_rate": None if accepted == 0 else round(wrong_accepted / accepted, 3),
        "people_over_alpha": sum(1 for p in per_person if p["false_cue_rate"] is not None and p["false_cue_rate"] > alpha),
        "per_person": per_person,
        "_wrong": wrong_accepted,
    }


def view_cuts(units: Sequence[Mapping[str, Any]]) -> tuple[float, float]:
    """Frontalness cut-offs from the dataset's camera-view labels only.

    side cut = midpoint between the most frontal 'profile' unit and the least
    frontal 'half-profile' unit; front cut likewise between 'half-profile'
    and 'front'. No error labels are used."""
    f = {v: [float(u["frontalness"]) for u in units if u["view"] == v] for v in ("profile", "half-profile", "front")}
    side = (max(f["profile"]) + min(f["half-profile"])) / 2
    front = (max(f["half-profile"]) + min(f["front"])) / 2
    return side, front


def view_rule_accepts(unit: Mapping[str, Any], side_cut: float, front_cut: float) -> bool:
    view = _PACK_VIEW.get(unit["pack_id"])
    frontal = float(unit["frontalness"])
    return frontal <= side_cut if view == "side" else frontal >= front_cut


def view_rule_gate(units: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Speak only when the estimated view matches the pack's view.

    Cut-offs are set leave-one-person-out from view labels; the false-cue
    rate gets an exact one-sided 95% upper bound (Clopper-Pearson)."""
    decided: list[tuple[Mapping[str, Any], bool]] = []
    cuts = {}
    for person in sorted({u["person_id"] for u in units}):
        side, front = view_cuts([u for u in units if u["person_id"] != person])
        cuts[person] = (round(side, 3), round(front, 3))
        decided += [(u, view_rule_accepts(u, side, front)) for u in units if u["person_id"] == person]

    def summarise(rows: Sequence[tuple[Mapping[str, Any], bool]]) -> dict[str, Any]:
        accepted = [u for u, ok in rows if ok]
        k = sum(u["wrong"] for u in accepted)
        return {
            "units": len(rows),
            "always_speak_risk": round(statistics.fmean(u["wrong"] for u, _ in rows), 3) if rows else None,
            "coverage": round(len(accepted) / len(rows), 3) if rows else 0.0,
            "accepted": len(accepted),
            "wrong_accepted": k,
            "false_cue_rate": round(k / len(accepted), 3) if accepted else None,
            "upper95": round(clopper_pearson_upper(k, len(accepted)), 3) if accepted else None,
        }

    by_pack = {pack: summarise([d for d in decided if d[0]["pack_id"] == pack]) for pack in sorted({u["pack_id"] for u in units})}
    by_person = {person: summarise([d for d in decided if d[0]["person_id"] == person]) for person in cuts}
    return {"overall": summarise(decided), "by_pack": by_pack, "by_person": by_person, "cuts": cuts}


def person_bootstrap(units: Sequence[Mapping[str, Any]], a: np.ndarray, b: np.ndarray, rounds: int = 2000, seed: int = 20261029) -> dict[str, Any]:
    """AUROC(a) - AUROC(b) with a 95% CI from resampling people."""
    rng = np.random.default_rng(seed)
    people = sorted({u["person_id"] for u in units})
    index = {p: [i for i, u in enumerate(units) if u["person_id"] == p] for p in people}
    correct = np.asarray([1 - u["wrong"] for u in units])
    diffs = []
    for _ in range(rounds):
        rows = [i for k in rng.integers(0, len(people), len(people)) for i in index[people[k]]]
        da, db = auroc(a[rows], correct[rows]), auroc(b[rows], correct[rows])
        if da is not None and db is not None:
            diffs.append(da - db)
    point = (auroc(a, correct) or math.nan) - (auroc(b, correct) or math.nan)
    lo, hi = np.percentile(diffs, [2.5, 97.5]) if diffs else (math.nan, math.nan)
    return {"difference": round(point, 3), "ci95": [round(float(lo), 3), round(float(hi), 3)]}


# ------------------------------------------------------------------------ CLI


def _markdown(rows: Sequence[Mapping[str, Any]]) -> str:
    if not rows:
        return "_none_\n"
    keys = list(rows[0])
    lines = ["| " + " | ".join(keys) + " |", "|" + " --- |" * len(keys)]
    lines += ["| " + " | ".join("" if r[k] is None else str(r[k]) for k in keys) + " |" for r in rows]
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--angle-eval", type=Path, required=True, help="output folder of angle_eval.py --save-landmarks")
    parser.add_argument("--dataset-root", type=Path, default=None)
    parser.add_argument("--alphas", type=float, nargs="+", default=[0.1, 0.15, 0.2])
    parser.add_argument("--delta", type=float, default=0.1)
    parser.add_argument("--l2", type=float, default=1.0)
    parser.add_argument("--procedure", choices=["fixed_sequence", "bonferroni"], default="fixed_sequence", help="Learn-then-Test multiple-testing procedure")
    parser.add_argument("--label", choices=["absolute", "calibrated"], default="absolute",
                        help="absolute: raw angle error; calibrated: error after a one-rep offset calibration (calibration reps dropped)")
    parser.add_argument("--tolerance-deg", type=float, default=None, help="default: the tolerance angle_eval used")
    parser.add_argument("--out", type=Path, default=None, help="default: <angle-eval>/gate")
    args = parser.parse_args(argv)
    out = args.out or args.angle_eval / ("gate" if args.label == "absolute" else "gate-calibrated")
    out.mkdir(parents=True, exist_ok=True)

    global PROCEDURE
    PROCEDURE = args.procedure
    units = load_units(args.angle_eval, args.dataset_root)
    if not units:
        parser.error("no units with landmarks; run angle_eval.py with --save-landmarks")
    if args.label == "calibrated":
        tolerance = args.tolerance_deg
        if tolerance is None:
            tolerance = json.loads((args.angle_eval / "summary.json").read_text(encoding="utf-8"))["tolerance_deg"]
        labels = calibrated_labels(args.angle_eval, tolerance)
        kept = []
        for u in units:
            info = labels.get((u["video_id"], int(u["repetition_number"]), int(u["camera"]), u["side"]))
            if info is None:  # no pose on any frame: stays a wrong measurement
                kept.append({**u, "calibration_rep": 0})
                continue
            if info["calibration_rep"]:
                continue
            failed_detection = float(u["detection_rate"]) < 0.5
            kept.append({**u, **info, "wrong_absolute": u["wrong"], "wrong": int(info["wrong_calibrated"] or failed_detection)})
        units = kept
    with (out / "units.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(units[0]))
        writer.writeheader()
        writer.writerows(units)

    correct = [1 - u["wrong"] for u in units]
    single = [{"feature": f, "auroc": None if (a := auroc([u[f] for u in units], correct)) is None else round(a, 3)} for f in FEATURES]
    scores = {m: out_of_fold(units, m, args.l2) for m in METHODS}
    wrong = [u["wrong"] for u in units]
    ranking = []
    for m, s in scores.items():
        row: dict[str, Any] = {"method": m, "auroc_all": round(auroc(s, correct) or math.nan, 3), "aurc": round(aurc(s, wrong), 3)}
        for pack in sorted({u["pack_id"] for u in units}):
            idx = [i for i, u in enumerate(units) if u["pack_id"] == pack]
            value = auroc(s[idx], [correct[i] for i in idx])
            row[pack.split(".")[-1]] = None if value is None else round(value, 3)
        ranking.append(row)
    boot = {m: person_bootstrap(units, scores[m], scores["visibility"]) for m in ("geometry", "combined")}
    gates = [nested_gate(units, m, a, args.delta, args.l2, per_pack=pp) for a in args.alphas for pp in (False, True) for m in METHODS]
    for g in gates:
        g.pop("_wrong", None)

    rule = view_rule_gate(units)
    side_cut, front_cut = view_cuts(units)
    (out / "view_rule.json").write_text(json.dumps({
        "type": "view-match",
        "feature": "frontalness = |left shoulder x - right shoulder x| / torso length (2D, px)",
        "side_pack_max_frontalness": round(side_cut, 3),
        "front_pack_min_frontalness": round(front_cut, 3),
        "requires": "one-rep offset calibration against the clinic-recorded reference",
        "label": args.label,
        "trained_on": "REHAB24-6 train+validation subjects, view labels only",
        "status": "research-only; not a clinical setting",
    }, indent=2), encoding="utf-8")
    final = LogisticGate(FEATURES, l2=args.l2).fit(units, correct)  # type: ignore[arg-type]
    final_threshold = {str(a): calibrate_threshold(scores["combined"], wrong, a, args.delta, procedure=PROCEDURE).threshold for a in args.alphas}
    model_json = {
        **final.to_json(),
        "thresholds": final_threshold,
        "delta": args.delta,
        "trained_on": "REHAB24-6 train+validation subjects (gt_quality reps), MediaPipe " + args.angle_eval.name,
        "status": "research-only; not a clinical setting",
    }
    (out / "gate_model.json").write_text(json.dumps(model_json, indent=2), encoding="utf-8")

    summary = {
        "units": len(units),
        "people": sorted({u["person_id"] for u in units}),
        "always_speak_risk": round(statistics.fmean(wrong), 3),
        "single_feature_auroc": single,
        "ranking": ranking,
        "auroc_gain_vs_visibility": boot,
        "gates": gates,
        "view_rule": rule,
        "model": model_json,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    gate_rows = [{k: g[k] for k in ("alpha", "method", "coverage", "false_cue_rate", "people_over_alpha")} for g in gates]
    md = [
        f"# Confidence gate: visibility vs richer quality features, {args.label} label (generated by ml/eval/gate_eval.py)\n",
        f"{len(units)} units (rep x camera x side) from people {summary['people']}, leave-one-person-out. "
        f"Wrong measurement = rep error above the angle_eval tolerance. Speaking on every rep gives a false-cue rate of {summary['always_speak_risk']}.\n",
        "## Each feature alone (AUROC for telling right from wrong measurements, pooled)\n",
        _markdown(single),
        "## Gate scores, out-of-fold AUROC (higher better) and AURC (lower better)\n",
        _markdown(ranking),
        "AUROC gain over visibility, 95% CI from resampling people:\n",
        _markdown([{"method": m, **b} for m, b in boot.items()]),
        f"## Calibrated gate on held-out people (Learn-then-Test, {args.procedure}, delta {args.delta})\n",
        "coverage = share of reps the coach speaks on; false_cue_rate = wrong measurements among those.\n",
        _markdown(gate_rows),
        "## View-match rule (no learning; cut-offs from view labels, leave-one-person-out)\n",
        "Speak only when the estimated camera view (frontalness) matches the view the exercise pack asks for. upper95 = exact one-sided 95% upper bound on the false-cue rate.\n",
        _markdown([{"scope": "all", **rule["overall"]}] + [{"scope": k.split(".")[-1], **v} for k, v in rule["by_pack"].items()]),
        "Per held-out person:\n",
        _markdown([{"person_id": k, **v} for k, v in rule["by_person"].items()]),
        "Per exercise pack (per-pack thresholds, first alpha):\n",
        _markdown([{"method": g["method"], **{f"{k.split('.')[-1]} coverage / false cues": f"{v['coverage']} / {v['false_cue_rate']}" for k, v in g["per_pack"].items()}} for g in gates if g["alpha"] == args.alphas[0] and "per_pack" in g]),
    ]
    (out / "summary.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

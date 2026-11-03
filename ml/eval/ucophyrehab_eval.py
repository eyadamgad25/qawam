"""Personal reference and rep counting on UCOPhyRehab++ (physiotherapist-scored reps).

UCOPhyRehab++ (Zenodo 17935737, CC BY 4.0; Scientific Data 2026) has 27 adults
doing 8 rehabilitation exercises with each side (16 exercise ids), OptiTrack 3D
joints for the moving limb (hip-knee-ankle or shoulder-elbow-wrist) with the 3D
joint angle, and one physiotherapist quality score per rep (1-5).

Two questions, both on motion capture (the upper bound before pose-model noise):

A. Does the distance to the person's own reference rep track the physio's
   score better than universal methods? Reference = the person's best-scored
   rep (the rep a physio would record in clinic), or their first rep as a
   robustness check; it is never scored. Universal template = mean curve of
   score-5 reps of the other people (leave-one-person-out); universal range =
   distance of the rep's range of motion from those people's mean, in SDs.
B. How well does the app's rep rule (hysteresis at 30% / 15% of range, as in
   web/src/exercise/liveCoach.ts) count the physio-annotated reps?

Nothing is fitted on the people being scored, so there is no sealed split.

  py -3.14 ml\\eval\\ucophyrehab_eval.py --root data\\raw\\ucophyrehab-pp
"""

from __future__ import annotations

import argparse
import json
import statistics
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

from qawam_ml.kimore import segment_reps  # noqa: E402
from qawam_ml.reference import dtw_path  # noqa: E402
from qawam_ml.rehab24 import REPO_ROOT  # noqa: E402
from reference_eval import resample, roc_auc  # noqa: E402

DEFAULT_ROOT = REPO_ROOT / "data" / "raw" / "ucophyrehab-pp"
DEFAULT_OUT = REPO_ROOT / "data" / "derived" / "ucophyrehab-eval"
METHODS = ("personal_best", "personal_first", "universal_template", "universal_range")
LOW_SCORE = 3  # reps scored <= 3 count as "needs correction" for the AUC
MAX_MISSING = 0.2
ENTER, LEAVE = 0.3, 0.15  # web/src/exercise/liveCoach.ts ENTER_FRACTION / EXIT_FRACTION


@dataclass
class Rep:
    subject: str
    exercise: str
    body: str
    start: int
    score: float
    curve: np.ndarray
    moving: bool = True  # the recording's angle carries the movement (see angle_moves)

    @property
    def rom(self) -> float:
        return float(self.curve.max() - self.curve.min())


# ------------------------------------------------------------------- loading


def angle_series(record: Mapping[str, Any]) -> dict[int, float]:
    """Frame id -> 3D joint angle; frames without joints are left out."""
    return {
        int(f["id"]): float(f["joints"]["angle"])
        for f in record.get("frames") or []
        if f.get("joints") and f["joints"].get("angle") is not None
    }


def angle_moves(series: Mapping[int, float]) -> bool:
    """Same guard as segment_reps: a p10-p95 range under 10 deg means this angle is not the movement."""
    values = np.array(list(series.values()))
    return bool(np.percentile(values, 95) - np.percentile(values, 10) >= 10)


def rep_curve(series: Mapping[int, float], start: int, end: int) -> np.ndarray | None:
    """Angle curve between two frame ids, gaps interpolated; None if too much is missing."""
    ids = np.arange(start, end + 1)
    known = np.array([i for i in ids if i in series])
    if known.size < 2 or 1 - known.size / ids.size > MAX_MISSING:
        return None
    return np.interp(ids, known, [series[i] for i in known])


def load(root: Path) -> tuple[list[Rep], list[dict[str, Any]]]:
    """Scored reps, and per recording the annotated and full angle series (for counting)."""
    meta = {}
    for line in (root / "ucophyrehab2_data.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            meta[(str(row["subject_id"]), str(row["exercise_id"]))] = row["scores"]
    data = json.loads((root / "dataset_3d_with_angles.json").read_text(encoding="utf-8"))["data"]
    reps: list[Rep] = []
    recordings: list[dict[str, Any]] = []
    for record in data:
        key = (str(record["folder"]), str(record["exercise"]))
        series = angle_series(record)
        scores = meta.get(key)
        if not series or not scores:
            continue
        moving = angle_moves(series)
        recordings.append({"subject": key[0], "exercise": key[1], "series": series, "annotated": len(scores),
                           "moving": moving})
        for s in scores:
            curve = rep_curve(series, int(s["init_frame"]), int(s["final_frame"]))
            if curve is not None:
                reps.append(Rep(key[0], key[1], str(record["body"]), int(s["init_frame"]), float(s["score"]),
                                curve, moving))
    return reps, recordings


# --------------------------------------------------------------- experiment A


def dtw_distance(a: np.ndarray, b: np.ndarray) -> float:
    total, path = dtw_path(a, b, window=max(a.size, b.size) // 3)
    return total / len(path)


def score_reps(reps: Sequence[Rep]) -> list[dict[str, Any]]:
    """Distance of every non-reference rep under each method (larger = further from good)."""
    groups: dict[tuple[str, str], list[Rep]] = defaultdict(list)
    for rep in reps:
        groups[(rep.subject, rep.exercise)].append(rep)
    by_exercise: dict[str, list[Rep]] = defaultdict(list)
    for rep in reps:
        if rep.score == 5:
            by_exercise[rep.exercise].append(rep)
    rows = []
    for (subject, exercise), items in sorted(groups.items()):
        items = sorted(items, key=lambda r: r.start)
        best = max(items, key=lambda r: (r.score, -r.start))
        first = items[0]
        others = [r for r in by_exercise[exercise] if r.subject != subject]
        if len(others) < 2:
            continue
        template = np.mean(np.stack([resample(r.curve) for r in others]), axis=0)
        roms = [r.rom for r in others]
        mean_rom, sd_rom = statistics.fmean(roms), statistics.stdev(roms) or 1.0
        for rep in items:
            if rep is best or rep is first:
                continue  # both references are left out so every method scores the same reps
            rows.append({
                "subject": subject,
                "exercise": exercise,
                "body": rep.body,
                "moving": rep.moving,
                "score": rep.score,
                "low": int(rep.score <= LOW_SCORE),
                "personal_best": dtw_distance(rep.curve, best.curve),
                "personal_first": dtw_distance(rep.curve, first.curve),
                "universal_template": dtw_distance(resample(rep.curve), template),
                "universal_range": abs(rep.rom - mean_rom) / sd_rom,
            })
    return rows


def spearman(x: Sequence[float], y: Sequence[float]) -> float | None:
    """Spearman rho with average ranks for ties."""
    def ranks(v: Sequence[float]) -> np.ndarray:
        order = np.argsort(v, kind="mergesort")
        r = np.empty(len(v))
        sorted_v = np.asarray(v)[order]
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and sorted_v[j + 1] == sorted_v[i]:
                j += 1
            r[order[i : j + 1]] = (i + j) / 2
            i = j + 1
        return r

    if len(x) < 3 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return None
    return float(np.corrcoef(ranks(x), ranks(y))[0, 1])


def agreement(rows: Sequence[Mapping[str, Any]], method: str) -> dict[str, Any]:
    """rho(-distance, score) and AUC for low-scored reps, each with a subject-bootstrap 95% CI."""
    def stats(sample: Sequence[Mapping[str, Any]]) -> tuple[float | None, float | None]:
        rho = spearman([-r[method] for r in sample], [r["score"] for r in sample])
        auc = roc_auc([r[method] for r in sample], [r["low"] for r in sample])
        return rho, auc

    rho, auc = stats(rows)
    by_subject: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for r in rows:
        by_subject[r["subject"]].append(r)
    subjects = sorted(by_subject)
    rng = np.random.default_rng(20261103)
    rhos, aucs = [], []
    for _ in range(1000):
        sample = [r for i in rng.integers(0, len(subjects), len(subjects)) for r in by_subject[subjects[int(i)]]]
        b_rho, b_auc = stats(sample)
        if b_rho is not None:
            rhos.append(b_rho)
        if b_auc is not None:
            aucs.append(b_auc)

    def ci(values: list[float]) -> list[float] | None:
        return [round(float(np.percentile(values, 2.5)), 3), round(float(np.percentile(values, 97.5)), 3)] if values else None

    return {
        "method": method,
        "reps": len(rows),
        "low_reps": sum(r["low"] for r in rows),
        "subjects": len(subjects),
        "rho": None if rho is None else round(rho, 3),
        "rho_ci95": ci(rhos),
        "auc_low": None if auc is None else round(auc, 3),
        "auc_ci95": ci(aucs),
    }


# --------------------------------------------------------------- experiment B


def count_reps(series: Mapping[int, float]) -> int:
    """App rep rule on the recording's angle, flipped when the rest pose is the high end."""
    ids = np.array(sorted(series))
    full = np.arange(ids[0], ids[-1] + 1)
    signal = np.interp(full, ids, [series[i] for i in ids])
    rest = float(np.median(signal[:10]))
    if rest > (signal.max() + signal.min()) / 2:
        signal = signal.max() - signal
    return len(segment_reps(signal, enter=ENTER, leave=LEAVE))


def counting(recordings: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Count error where the angle moves; where it does not, the rule abstains (counts 0) by design."""
    moving = [r for r in recordings if r["moving"]]
    errors = [count_reps(r["series"]) - r["annotated"] for r in moving]
    return {
        "recordings": len(recordings),
        "abstained": len(recordings) - len(moving),
        "abstained_exercises": sorted({r["exercise"] for r in recordings if not r["moving"]}),
        "counted": len(errors),
        "mae": round(float(np.mean(np.abs(errors))), 3),
        "exact": round(float(np.mean([e == 0 for e in errors])), 3),
        "within_one": round(float(np.mean([abs(e) <= 1 for e in errors])), 3),
        "mean_signed": round(float(np.mean(errors)), 3),
    }


# -------------------------------------------------------------------- report


def build_report(reps: Sequence[Rep], recordings: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = score_reps(reps)
    out: dict[str, Any] = {
        "dataset": "UCOPhyRehab++ (Zenodo 17935737, CC BY 4.0)",
        "scored_reps": len(reps),
        "score_counts": {str(k): sum(1 for r in reps if r.score == k) for k in sorted({r.score for r in reps})},
        "agreement": {"all": [agreement(rows, m) for m in METHODS]},
        "counting": counting(recordings),
    }
    parts = {
        "angle moves": [r for r in rows if r["moving"]],
        "angle moves, lower": [r for r in rows if r["moving"] and r["body"] == "lower"],
        "angle moves, upper": [r for r in rows if r["moving"] and r["body"] == "upper"],
    }
    for name, part in parts.items():
        if part:
            out["agreement"][name] = [agreement(part, m) for m in METHODS]
    return out


def markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# UCOPhyRehab++: personal reference vs physio score, and rep counting",
        "",
        f"{report['dataset']}; {report['scored_reps']} scored reps; score counts {report['score_counts']}.",
        "Motion-capture 3D joint angle (upper bound before pose noise). rho = Spearman between minus the distance "
        f"and the physio score; AUC = flags reps scored <= {LOW_SCORE}. 95% CIs resample people.",
        "",
        "| Reps | Method | Reps (low) | rho [95% CI] | AUC low [95% CI] |",
        "| --- | --- | --- | --- | --- |",
    ]
    for part, results in report["agreement"].items():
        for r in results:
            lines.append(
                f"| {part} | {r['method']} | {r['reps']} ({r['low_reps']}) | {r['rho']} {r['rho_ci95']} | "
                f"{r['auc_low']} {r['auc_ci95']} |"
            )
    c = report["counting"]
    lines += [
        "",
        f"Rep counting (app rule, {ENTER:.0%} / {LEAVE:.0%} hysteresis): of {c['recordings']} recordings it "
        f"abstained on {c['abstained']} where the angle moves < 10 deg (exercises {', '.join(c['abstained_exercises'])}). "
        f"On the {c['counted']} it counted: MAE {c['mae']} reps, exact {c['exact']:.0%}, within one "
        f"{c['within_one']:.0%}, mean signed error {c['mean_signed']}.",
    ]
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    reps, recordings = load(args.root)
    if not reps:
        print(f"no scored reps found under {args.root}", file=sys.stderr)
        return 1
    report = build_report(reps, recordings)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    text = markdown(report)
    (args.out / "summary.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

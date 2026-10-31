"""KIMORE study: is one phone camera enough, from where, and does the view gate know?

Uses KIMORE's Kinect v2 skeletons (real stroke, Parkinson's and low-back-pain
patients, each scored by clinicians) as 3D ground truth and projects them into
virtual phone cameras around the patient. For every placement it measures
what Qawam would actually tell the patient:

1. Range-of-motion error of the 2D angle against the 3D angle, per rep.
2. Cue agreement: the app compares each rep with the patient's own first rep
   ("less / more / matches" at the tolerance). Does the 2D cue match the cue the
   3D skeleton would give?
3. View gate transfer: the frontalness thresholds were fitted on healthy
   REHAB24-6 volunteers. Do they still separate good from bad placements on
   KIMORE patients?
4. Clinical signal: does per-patient 2D range of motion track the clinicians'
   total score as well as the 3D one does?

This isolates geometry (camera placement). Detector error of MediaPipe on real
video was measured separately on REHAB24-6.

Run (data stays local, outputs are aggregates only):

    python ml/eval/kimore_eval.py --root data/raw/kimore --out docs/kimore-study.md
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qawam_ml.kimore import (
    frontalness,
    iter_recordings,
    joint_angle,
    plane_view,
    read_scores,
    segment_reps,
    smooth,
    virtual_view,
)
from qawam_ml.selective import clopper_pearson_upper

REPO = Path(__file__).resolve().parents[2]
GATE = json.loads((REPO / "rules/gate/view-rule.json").read_text())
SIDE_MAX = GATE["side_pack_max_frontalness"]

# KIMORE Es5 is a squat; Es1 lifts both arms forward and overhead (we measured:
# the elbow moves mostly forward, i.e. shoulder flexion), so both are side-view
# exercises for a 2D camera.
EXERCISES = {
    5: {"name": "Squat (KIMORE Es5)", "angle": "knee_flexion", "plane": "sagittal"},
    1: {"name": "Arm lift (KIMORE Es1)", "angle": "shoulder_elevation", "plane": "sagittal"},
}
YAWS = (0, 15, 30, 45, 60, 75, 90)
TOL = 10.0  # Qawam's default test tolerance in degrees


def cue(diff: float, tol: float = TOL) -> str:
    return "less" if diff < -tol else "more" if diff > tol else "match"


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    rx = np.argsort(np.argsort(x)).astype(float)
    ry = np.argsort(np.argsort(y)).astype(float)
    return float(np.corrcoef(rx, ry)[0, 1])


def bootstrap_ci(x: np.ndarray, y: np.ndarray, n: int = 2000, seed: int = 0) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n):
        idx = rng.integers(0, len(x), len(x))
        if np.ptp(x[idx]) == 0 or np.ptp(y[idx]) == 0:
            continue
        vals.append(spearman(x[idx], y[idx]))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def rep_roms(signal: np.ndarray, reps: list[tuple[int, int]]) -> np.ndarray:
    s = smooth(signal)
    base = np.nanpercentile(s, 10)
    return np.array([np.nanmax(s[a : b + 1]) - base for a, b in reps])


def analyse(root: Path, exercise: int, pitches: tuple[float, ...]) -> dict:
    spec = EXERCISES[exercise]
    rom_err: dict[tuple[int, float], list[float]] = defaultdict(list)
    agree: dict[tuple[int, float], list[int]] = defaultdict(list)
    front: dict[tuple[int, float], list[float]] = defaultdict(list)
    gate_rows: list[tuple[float, float, int, int]] = []  # frontalness, |rom err|, yaw, agree
    per_subject: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    n_rec = n_reps = 0
    for rec in iter_recordings(root, exercise):
        recorded = False
        for side in ("left", "right"):
            truth = joint_angle(plane_view(rec.xyz, spec["plane"]), spec["angle"], side)
            reps = segment_reps(truth)
            if len(reps) < 2:
                continue
            recorded = True
            n_reps += len(reps)
            rom3 = rep_roms(truth, reps)
            cue3 = [cue(r - rom3[0]) for r in rom3[1:]]
            per_subject[rec.subject]["plane"].extend(rom3)
            per_subject[rec.subject]["3d"].extend(rep_roms(joint_angle(rec.xyz, spec["angle"], side), reps))
            for pitch in pitches:
                for yaw in YAWS:
                    pts = virtual_view(rec.xyz, yaw, pitch_deg=pitch)
                    rom2 = rep_roms(joint_angle(pts, spec["angle"], side), reps)
                    err = np.abs(rom2 - rom3)
                    f = float(np.median(frontalness(pts)))
                    rom_err[(yaw, pitch)].extend(err)
                    front[(yaw, pitch)].append(f)
                    ok = [int(cue(r - rom2[0]) == c) for r, c in zip(rom2[1:], cue3)]
                    agree[(yaw, pitch)].extend(ok)
                    if pitch == 0:
                        gate_rows.extend((f, e, yaw, a) for e, a in zip(err[1:], ok))
                        if yaw in (0, 90):
                            per_subject[rec.subject][f"2d_{yaw}"].extend(rom2)
        n_rec += recorded
    return {
        "spec": spec, "rom_err": rom_err, "agree": agree, "front": front,
        "gate_rows": gate_rows, "per_subject": per_subject, "n_rec": n_rec, "n_reps": n_reps,
    }


def fmt_ci(k: int, n: int) -> str:
    return f"{100 * k / n:.1f}% (95% upper {100 * clopper_pearson_upper(k, n):.1f}%)" if n else "–"


def report(root: Path, results: dict[int, dict], scores: dict[str, dict[str, float]]) -> str:
    out = [
        "# KIMORE study — one phone camera on real patients",
        "",
        ("Generated by `ml/eval/kimore_eval.py` from KIMORE's Kinect v2 skeletons "
        "(GPP group: stroke, Parkinson's, low-back pain). Ground truth is the goniometer-style angle: "
        "the body-aligned Kinect skeleton projected orthographically onto the exercise's anatomical plane; "
        "each recording is projected into virtual phone cameras placed around the patient "
        "(0° = facing the camera, 90° = side-on), 2.5 m away at chest height. "
        "Reps are segmented on the ground-truth angle so the phone and the goniometer compare the same reps. "
        f"Cue tolerance = {TOL:.0f}° (Qawam's default). "
        "This isolates camera placement; MediaPipe's own detector error was measured on REHAB24-6."),
        "",
    ]
    for ex, r in results.items():
        spec = r["spec"]
        out += [f"## {spec['name']} — `{spec['angle']}`", "",
                f"{r['n_rec']} recordings, {r['n_reps']} reps (left and right side counted separately).", ""]
        pitches = sorted({p for _, p in r["rom_err"]})
        out += ["| Camera angle | Pitch | Median frontalness | ROM error median | ROM error p90 | Cue agrees with 3D |",
                "|---|---|---|---|---|---|"]
        for pitch in pitches:
            for yaw in YAWS:
                e = np.array(r["rom_err"][(yaw, pitch)])
                a = np.array(r["agree"][(yaw, pitch)])
                f = np.median(r["front"][(yaw, pitch)])
                out.append(f"| {yaw}° | {pitch:.0f}° | {f:.2f} | {np.median(e):.1f}° | "
                           f"{np.percentile(e, 90):.1f}° | {100 * a.mean():.1f}% |")
        out.append("")

        rows = np.array(r["gate_rows"])
        if len(rows):
            accepted = rows[:, 0] <= SIDE_MAX
            wrong = rows[:, 3] == 0
            ka, na = int((wrong & accepted).sum()), int(accepted.sum())
            kr, nr = int((wrong & ~accepted).sum()), int((~accepted).sum())
            out += [
                f"**View gate transfer** (side-pack rule frontalness ≤ {SIDE_MAX}, fitted on REHAB24-6, unchanged):",
                f"- Accepted placements: {na} cues, wrong cue rate {fmt_ci(ka, na)}.",
                f"- Rejected placements: {nr} cues, wrong cue rate {fmt_ci(kr, nr)}.",
                "- Accepted camera angles: "
                + ", ".join(f"{y}°: {100 * np.mean(rows[rows[:, 2] == y, 0] <= SIDE_MAX):.0f}%" for y in YAWS),
                "",
            ]

        ts_key = f"TS{ex}"
        subj = [s for s, d in r["per_subject"].items() if s in scores and ts_key in scores[s] and d.get("3d")]
        if len(subj) >= 8:
            ts = np.array([scores[s][ts_key] for s in subj])
            out += [(f"**Clinical signal** — Spearman ρ between a patient's mean rep range and the clinicians' "
                    f"total score {ts_key} (n = {len(subj)} patients, 95% bootstrap CI):"), ""]
            for key, label in (("plane", "Kinect, in-plane (goniometer-style)"), ("3d", "Kinect, raw 3D angle"), ("2d_90", "Phone, side-on (90°)"), ("2d_0", "Phone, facing (0°)")):
                x = np.array([np.mean(r["per_subject"][s][key]) for s in subj])
                lo, hi = bootstrap_ci(x, ts)
                out.append(f"- {label}: ρ = {spearman(x, ts):.2f} [{lo:.2f}, {hi:.2f}]")
            cf_key = f"CF{ex}"
            subj_cf = [s for s in subj if cf_key in scores[s] and len(r["per_subject"][s]["2d_90"]) >= 3]
            if len(subj_cf) >= 8:
                cv = np.array([np.std(r["per_subject"][s]["2d_90"]) / max(np.mean(r["per_subject"][s]["2d_90"]), 1)
                               for s in subj_cf])
                cf = np.array([scores[s][cf_key] for s in subj_cf])
                lo, hi = bootstrap_ci(cv, cf)
                out.append(f"- Rep-to-rep variability (coefficient of variation, side-on phone) vs control "
                           f"factor {cf_key}: ρ = {spearman(cv, cf):.2f} [{lo:.2f}, {hi:.2f}]")
            out.append("")
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--root", type=Path, default=REPO / "data/raw/kimore")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--json", type=Path, default=None, help="optional aggregate numbers as JSON")
    args = parser.parse_args()
    scores = read_scores(args.root)
    results = {ex: analyse(args.root, ex, pitches=(0.0, 20.0)) for ex in EXERCISES}
    text = report(args.root, results, scores)
    if args.out:
        args.out.write_text(text + "\n")
    print(text)
    if args.json:
        summary = {
            str(ex): {f"{y}@{p:.0f}": {"rom_err_median": float(np.median(r["rom_err"][(y, p)])),
                                         "cue_agree": float(np.mean(r["agree"][(y, p)]))}
                      for (y, p) in r["rom_err"]}
            for ex, r in results.items()
        }
        args.json.write_text(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()

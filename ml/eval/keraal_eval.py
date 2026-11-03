"""Personal reference on KERAAL: does comparing a patient with their own correct recording
catch the errors two clinicians marked, better than comparing with other people?

KERAAL (Nguyen et al., IJCNN 2024; CC BY-NC-SA) has low-back-pain patients (group 1A,
R1-R6) and healthy people (group 2A) doing 3 exercises (CTK, ELK, RTK), filmed from the
front, with BlazePose skeletons and one verdict per recording from each of two clinicians
(annotatorA, annotatorB: Correct / Incorrect / Incomplete / Motionless).

Features per frame (every 5th): by default the angles the app measures (trunk side tilt,
shoulder abduction and elbow angle on both sides); with --features positions, nose,
shoulders, elbows, wrists and hips (BlazePose 2D) centred on the mid-hip and divided by
the recording's median torso length.
Distance = multivariate DTW, mean cost along the path. Scores per recording:
  personal  - distance to the patient's own reference: their first recording of that
              exercise that both clinicians call Correct (never scored itself);
  patients  - median distance to other patients' both-Correct recordings (leave-person-out);
  healthy   - median distance to the healthy group's both-Correct recordings.
A recording counts as an error if the clinician did not call it Correct; reported for
each clinician and for the recordings where they agree. AUC CIs resample patients.

  py -3.14 ml\\eval\\keraal_eval.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

EVAL_DIR = Path(__file__).resolve().parent
ML_ROOT = EVAL_DIR.parent
for path in (str(ML_ROOT), str(EVAL_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

from gate_eval import auroc  # noqa: E402
from qawam_ml.rehab24 import REPO_ROOT  # noqa: E402

DEFAULT_ROOT = REPO_ROOT / "data" / "raw" / "keraal"
DEFAULT_OUT = REPO_ROOT / "data" / "derived" / "keraal-eval"
JOINTS = ("Nose", "Left_shoulder", "Right_shoulder", "Left_elbow", "Right_elbow",
          "Left_wrist", "Right_wrist", "Left_hip", "Right_hip")
STEP = 5
METHODS = ("personal", "patients", "healthy")
NAME = re.compile(r"G(?P<group>\d[AB])-(?P<exercise>[A-Z]{3})-(?P<person>[A-Z]\d+)-(?P<site>\w+)-(?P<take>\d+)$")


def read_anvil(path: Path) -> str | None:
    """Global verdict from an Anvil file; the files claim UTF-16 but many are UTF-8."""
    raw = path.read_bytes()
    for encoding in ("utf-16", "utf-8-sig", "cp1252"):
        try:
            text = re.sub(r"^\s*<\?xml[^>]*\?>", "", raw.decode(encoding))
            root = ET.fromstring(text)
        except (UnicodeDecodeError, ET.ParseError):
            continue
        for track in root.iter("track"):
            if track.get("name") == "Global evaluation":
                for attribute in track.iter("attribute"):
                    return attribute.text
        return None
    return None


def features(path: Path) -> np.ndarray:
    """(frames, 18) normalised 2D joints; frames missing a joint are dropped."""
    positions = json.loads(path.read_text())["positions"]
    frames = []
    for key in sorted(positions, key=float)[::STEP]:
        frame = positions[key]
        if all(j in frame for j in JOINTS):
            frames.append([frame[j][:2] for j in JOINTS])
    if len(frames) < 5:
        return np.empty((0, 2 * len(JOINTS)))
    xy = np.asarray(frames, dtype=float)
    hip = xy[:, 7:9].mean(axis=1, keepdims=True)
    shoulder = xy[:, 1:3].mean(axis=1, keepdims=True)
    torso = float(np.median(np.linalg.norm((shoulder - hip)[:, 0], axis=1)))
    return ((xy - hip) / max(torso, 1e-6)).reshape(len(xy), -1)


def _interior(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray:
    u, v = a - b, c - b
    cos = np.sum(u * v, axis=1) / (np.linalg.norm(u, axis=1) * np.linalg.norm(v, axis=1) + 1e-9)
    return np.degrees(np.arccos(np.clip(cos, -1.0, 1.0)))


def angle_features(x: np.ndarray) -> np.ndarray:
    """Trunk side tilt, both shoulder abductions and both elbow angles (deg / 30), from positions."""
    j = x.reshape(len(x), len(JOINTS), 2)
    trunk = j[:, 1:3].mean(axis=1) - j[:, 7:9].mean(axis=1)
    tilt = np.degrees(np.arctan2(trunk[:, 0], -trunk[:, 1]))
    return np.stack([
        tilt,
        _interior(j[:, 7], j[:, 1], j[:, 3]), _interior(j[:, 8], j[:, 2], j[:, 4]),
        _interior(j[:, 1], j[:, 3], j[:, 5]), _interior(j[:, 2], j[:, 4], j[:, 6]),
    ], axis=1) / 30.0


def load(root: Path) -> list[dict[str, Any]]:
    recordings = []
    for group in ("group1A", "group2A"):
        for pose in sorted((root / group / "blazepose").glob("*.json")):
            stem = pose.stem.replace("-BP-", "-")
            match = NAME.match(stem)
            if not match:
                continue
            anvil = stem + ".anvil"
            verdicts = {a: read_anvil(root / group / f"annotator{a}" / anvil) for a in "AB"}
            if None in verdicts.values():
                continue
            recordings.append({
                **match.groupdict(),
                "patient": group == "group1A",
                "verdict_A": verdicts["A"],
                "verdict_B": verdicts["B"],
                "x": features(pose),
            })
    return [r for r in recordings if len(r["x"])]


def dtw(a: np.ndarray, b: np.ndarray) -> float:
    """Multivariate DTW (Euclidean frame cost), total cost / (len(a) + len(b))."""
    cost = np.linalg.norm(a[:, None, :] - b[None, :, :], axis=2).tolist()
    inf = float("inf")
    prev = [0.0] + [inf] * len(b)
    for row in cost:
        cur = [inf]
        for j, c in enumerate(row):
            cur.append(c + min(prev[j], prev[j + 1], cur[j]))
        prev = cur
    return prev[-1] / (len(a) + len(b))


def both_correct(r: Mapping[str, Any]) -> bool:
    return r["verdict_A"] == "Correct" and r["verdict_B"] == "Correct"


def score(recordings: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    patients = [r for r in recordings if r["patient"]]
    references = {}
    for r in sorted(patients, key=lambda r: int(r["take"])):
        key = (r["person"], r["exercise"])
        if key not in references and both_correct(r):
            references[key] = r
    rows = []
    for r in patients:
        ref = references.get((r["person"], r["exercise"]))
        if ref is None or ref is r:
            continue
        others = [o for o in patients if o["exercise"] == r["exercise"] and o["person"] != r["person"] and both_correct(o)]
        healthy = [o for o in recordings if not o["patient"] and o["exercise"] == r["exercise"] and both_correct(o)]
        rows.append({
            "person": r["person"],
            "exercise": r["exercise"],
            "take": r["take"],
            "error_A": int(r["verdict_A"] != "Correct"),
            "error_B": int(r["verdict_B"] != "Correct"),
            "personal": dtw(r["x"], ref["x"]),
            "patients": float(np.median([dtw(r["x"], o["x"]) for o in others])) if others else None,
            "healthy": float(np.median([dtw(r["x"], o["x"]) for o in healthy])) if healthy else None,
        })
    return rows


def auc_with_ci(rows: Sequence[Mapping[str, Any]], method: str, label: str, rounds: int = 2000, seed: int = 20261103) -> dict[str, Any]:
    """AUC of distance for flagging errors, 95% CI from resampling patients."""
    rows = [r for r in rows if r[method] is not None and r[label] is not None]

    def auc(rs: Sequence[Mapping[str, Any]]) -> float | None:
        return auroc([-r[method] for r in rs], [1 - r[label] for r in rs])

    people = sorted({r["person"] for r in rows})
    by = {p: [r for r in rows if r["person"] == p] for p in people}
    rng = np.random.default_rng(seed)
    boots = [a for _ in range(rounds) if (a := auc([r for k in rng.integers(0, len(people), len(people)) for r in by[people[k]]])) is not None]
    point = auc(rows)
    lo, hi = np.percentile(boots, [2.5, 97.5]) if boots else (np.nan, np.nan)
    return {"auc": None if point is None else round(point, 3), "ci95": [round(float(lo), 3), round(float(hi), 3)],
            "n": len(rows), "errors": sum(r[label] for r in rows)}


def build_report(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    agreed = [{**r, "error_agreed": r["error_A"]} for r in rows if r["error_A"] == r["error_B"]]
    report: dict[str, Any] = {"recordings_scored": len(rows), "patients": sorted({r["person"] for r in rows})}
    for label, part in (("error_A", rows), ("error_B", rows), ("error_agreed", agreed)):
        report[label] = {m: auc_with_ci(part, m, label) for m in METHODS}
        report[label]["by_exercise"] = {
            ex: {m: auc_with_ci([r for r in part if r["exercise"] == ex], m, label)["auc"] for m in METHODS}
            for ex in sorted({r["exercise"] for r in part})
        }
    return report


def markdown(report: Mapping[str, Any]) -> str:
    lines = [f"KERAAL personal reference: {report['recordings_scored']} patient recordings scored, patients {report['patients']}", ""]
    for label in ("error_A", "error_B", "error_agreed"):
        lines += [f"## {label}", "", "| Method | AUC | 95% CI | n | errors |", "| --- | --- | --- | --- | --- |"]
        for m in METHODS:
            r = report[label][m]
            lines.append(f"| {m} | {r['auc']} | {r['ci95']} | {r['n']} | {r['errors']} |")
        lines += ["", "By exercise: " + json.dumps(report[label]["by_exercise"]), ""]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--features", choices=("angles", "positions"), default="angles",
                        help="angles = what the app measures (default); positions = normalised joints")
    args = parser.parse_args(argv)
    recordings = load(args.root)
    if not any(r["patient"] for r in recordings):
        print(f"no KERAAL patient recordings under {args.root}", file=sys.stderr)
        return 1
    if args.features == "angles":
        for r in recordings:
            r["x"] = angle_features(r["x"])
    report = {"features": args.features, **build_report(score(recordings))}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (args.out / "summary.md").write_text(markdown(report), encoding="utf-8")
    print(markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

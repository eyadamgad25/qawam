"""Confirm the three-rep, per-patient cut-off on data that played no part in finding it.

Rules: docs/superpowers/specs/2026-11-25-three-rep-confirmation.md, written first.

  py -3.14 ml\\eval\\confirm_reference.py --freeze   (once, old datasets only)
  py -3.14 ml\\eval\\confirm_reference.py            (scores the new datasets with the frozen cut-offs)
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import zipfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

EVAL_DIR = Path(__file__).resolve().parent
if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))

import quality_model as q  # noqa: E402

CUTS = EVAL_DIR / "confirm_cuts.json"
DEFAULT_OUT = q.REPO_ROOT / "data" / "derived" / "confirm-reference"
K = 3
KERAAL_ASPECT = 480 / 360
KERAAL_FRAME_STEP = 2
KERAAL_NAMES = {n: n.split("_")[0].capitalize() + "_" + n.split("_")[1].lower() for n in q.LIMBS} | {"HEAD": "Nose"}


def freeze(raw: Path) -> dict[str, float]:
    sets = (q.load_irds(raw / "SkeletonData" / "Simplified"), q.load_rehab24(raw / "rehab24-6", (1, 4, 5, 6)),
            q.load_rehab26(raw / "rehab26", (6, 1)))
    rows = [r for reps in sets for r in q.personalise(reps, K)]
    y = np.array([r["y"] for r in rows])
    return {**{k: q.best_cut(np.array([r[k] for r in rows]), y) for k in ("dtw", "dtw_z")}, "reps": len(rows)}


def moving_leg(points: np.ndarray) -> str:
    """The leg whose ankle travels further sideways."""
    return "right" if np.ptp(points[:, q.P["RIGHT_ANKLE"], 0]) > np.ptp(points[:, q.P["LEFT_ANKLE"], 0]) else "left"


def day(session: Mapping[str, str]) -> str:
    return session["filename"].split("_")[-2]


def load_physiolens(archive: Path, aspect: float) -> list[q.Rep]:
    z = zipfile.ZipFile(archive)
    manifest = list(csv.DictReader(io.StringIO(z.read("manifest.csv").decode("utf-8"))))
    people = {s: f"L{i + 1}" for i, s in enumerate(sorted({m["subject"] for m in manifest}))}
    good_day = {m["subject"]: day(m) for m in manifest if m["intent"] == "good"}
    reps = []
    for session, m in enumerate(manifest):
        records = [json.loads(line) for line in z.read(m["filename"]).decode("utf-8").splitlines()]
        frames = {r["frame"]: r for r in records if r["type"] == "frame" and r.get("landmarks")}
        for r in (r for r in records if r["type"] == "rep"):
            if not r["completed"] or r["aborted"] or r["end_frame"] is None:
                continue
            marks = [frames[i]["landmarks"] for i in range(r["start_frame"], r["end_frame"] + 1) if i in frames]
            points = np.array([[(f[str(q.MEDIAPIPE[n])]["x"] * aspect, f[str(q.MEDIAPIPE[n])]["y"]) for n in q.POINTS] for f in marks])
            if len(points) < 8:
                continue
            person, leg = people[m["subject"]], moving_leg(points)
            rep = q.make_rep(points, len(points) / r["duration"], dataset="physiolens", person=person, exercise="side leg raise",
                             view="same day" if day(m) == good_day[m["subject"]] else "another day", group=(person, leg),
                             order=(session, r["rep_id"]), incorrect=int(m["intent"] == "bad"), error=m["fault_type"])
            if rep:
                reps.append(rep)
    return reps


def load_keraal(root: Path) -> list[q.Rep]:
    import keraal_eval as ke

    reps = []
    for pose in sorted((root / "group1A" / "blazepose").glob("*.json")):
        stem = pose.stem.replace("-BP-", "-")
        match = ke.NAME.match(stem)
        if not match:
            continue
        verdicts = [ke.read_anvil(root / "group1A" / f"annotator{a}" / f"{stem}.anvil") for a in "AB"]
        if None in verdicts or (verdicts[0] == "Correct") != (verdicts[1] == "Correct"):
            continue  # only recordings the clinicians agree on
        positions = json.loads(pose.read_text())["positions"]
        kept = [positions[k] for k in sorted(positions, key=float)[::KERAAL_FRAME_STEP]]
        frames = [[f[KERAAL_NAMES[n]][:2] for n in q.POINTS] for f in kept if all(KERAAL_NAMES[n] in f for n in q.POINTS)]
        if len(frames) < 8:
            continue
        rep = q.make_rep(np.array(frames, dtype=float) * (KERAAL_ASPECT, 1.0), 30 / KERAAL_FRAME_STEP, dataset="keraal",
                         person=match["person"], exercise=match["exercise"], view="front",
                         group=(match["person"], match["exercise"]), order=(int(match["take"]),),
                         incorrect=int(verdicts[0] != "Correct"), patient=True)
        if rep:
            reps.append(rep)
    return reps


def with_channels(rep: q.Rep, channels: np.ndarray) -> q.Rep:
    return q.Rep(**{**rep.__dict__, "channels": channels})


def start_posture(reps: Sequence[q.Rep]) -> list[q.Rep]:
    """Control 1: only how the person stands at the start of the rep."""
    return [with_channels(r, np.repeat(r.channels[:3].mean(axis=0, keepdims=True), q.LENGTH, axis=0)) for r in reps]


def remove_start(reps: Sequence[q.Rep]) -> list[q.Rep]:
    """Control 2: the movement without the starting posture."""
    return [with_channels(r, r.channels - r.channels[:3].mean(axis=0, keepdims=True)) for r in reps]


def plain_gap(reps: Sequence[q.Rep]) -> list[dict[str, Any]]:
    """Unweighted distance to the references: a start posture does not move, so the movement weights would all be zero."""
    rows = q.personalise(reps, K)
    for r in rows:
        r["dtw"] = float(r["x"][: r["rep"].channels.shape[1]].mean())
    return rows


def apply_cuts(rows: Sequence[dict[str, Any]], cuts: Mapping[str, float]) -> None:
    for r in rows:
        for k in ("dtw", "dtw_z"):
            r[f"{k}_says"] = bool(r[k] >= cuts[k])


def exercise_aucs(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, float]:
    out = {}
    for e in sorted({r["exercise"] for r in rows}):
        part = [r for r in rows if r["exercise"] == e]
        auc = q.auroc([r[key] for r in part], [r["y"] for r in part])
        if auc is not None:
            out[e] = round(float(auc), 3)
    return out


def auc_ci(rows: Sequence[Mapping[str, Any]], key: str, seed: int = 20261125) -> dict[str, Any]:
    """Mean AUC within exercise, with a 95% interval from resampling people."""
    by: dict[str, list[Mapping[str, Any]]] = {}
    for r in rows:
        by.setdefault(r["person"], []).append(r)
    people, rng, draws = sorted(by), np.random.default_rng(seed), []
    for _ in range(q.BOOTSTRAP):
        aucs = exercise_aucs([r for i in rng.integers(0, len(people), len(people)) for r in by[people[i]]], key)
        if aucs:
            draws.append(np.mean(list(aucs.values())))
    per = exercise_aucs(rows, key)
    return {"auc": round(float(np.mean(list(per.values()))), 3), "ci95": [round(float(np.percentile(draws, p)), 3) for p in (2.5, 97.5)],
            "per_exercise": per}


def count(rows: Sequence[Mapping[str, Any]], decision: str, y: int) -> str:
    part = [r for r in rows if r["y"] == y]
    return f"{sum(r[decision] for r in part)} / {len(part)}"


def result(rows: Sequence[dict[str, Any]], cuts: Mapping[str, float]) -> dict[str, Any]:
    apply_cuts(rows, cuts)
    out: dict[str, Any] = {}
    for k, name in (("dtw", "plain"), ("dtw_z", "per_patient")):
        out[name] = {**q.evaluate(rows, f"{k}_says", None), "auc": auc_ci(rows, k),
                     "correct_called_wrong": count(rows, f"{k}_says", 0), "wrong_caught": count(rows, f"{k}_says", 1)}
    out["gain_per_patient_over_plain"] = q.paired_gain(rows, "dtw_z_says", "dtw_says")
    return out


def physiolens_block(reps: Sequence[q.Rep], cuts: Mapping[str, float]) -> dict[str, Any]:
    rows = q.personalise(reps, K)
    block: dict[str, Any] = {"main": result(rows, cuts),
                             "control 2, starting posture removed": result(q.personalise(remove_start(reps), K), cuts),
                             "control 1, starting posture only": auc_ci(plain_gap(start_posture(reps)), "dtw")}
    for attribute, value in (("view", "same day"), ("view", "another day"), ("error", "knee_bent"), ("error", "shallow")):
        part = [r for r in rows if not r["y"] or getattr(r["rep"], attribute) == value]
        block[f"faults: {value}"] = {k: v for k, v in result(part, cuts)["per_patient"].items()
                                     if k in ("macro_f1", "auc", "correct_called_wrong", "wrong_caught")}
    block["per person"] = {p: {"correct called wrong": count([r for r in rows if r["person"] == p], "dtw_z_says", 0),
                               "wrong caught": count([r for r in rows if r["person"] == p], "dtw_z_says", 1)}
                           for p in sorted({r["person"] for r in rows})}
    return block


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw", type=Path, default=q.RAW)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--freeze", action="store_true")
    args = parser.parse_args(argv)
    if args.freeze:
        if CUTS.exists():
            print("already frozen", file=sys.stderr)
            return 1
        CUTS.write_text(json.dumps(freeze(args.raw), indent=2) + "\n", encoding="utf-8")
        print(CUTS.read_text(encoding="utf-8"))
        return 0
    cuts = json.loads(CUTS.read_text(encoding="utf-8"))
    archive = args.raw / "physiolens" / "archive.zip"
    report: dict[str, Any] = {"cuts": cuts}
    for label, aspect in (("4:3", 4 / 3), ("16:9", 16 / 9)):
        report[f"PhysioLens {label}"] = physiolens_block(load_physiolens(archive, aspect), cuts)
    report["KERAAL patients"] = result(q.personalise(load_keraal(args.raw / "keraal"), K), cuts)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())

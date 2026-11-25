"""Motion sensors, muscle sensors, or both: correct vs wrong exercise on KneE-PAD knee patients.

Design: docs/superpowers/specs/2026-11-25-quality-model-and-fusion-design.md. KneE-PAD (Zenodo 12112951, CC BY 4.0):
31 knee patients, 8 Delsys sensors (muscle signal + accelerometer + gyroscope). The release has no video, so this
measures fusion of two sensor types, not camera + sensor.

Leave one patient out. Sides are mapped to injured / healthy leg from the patient table, which a physio knows before
the session. Fusion is joined features, or averaged probabilities; the averaged version keeps working when one sensor
type is missing.

  py -3.14 ml\\eval\\fusion_model.py
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import zipfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

EVAL_DIR = Path(__file__).resolve().parent
ML_ROOT = EVAL_DIR.parent
for path in (str(ML_ROOT), str(EVAL_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

from quality_model import abstention, evaluate, fit_logistic, paired_gain, predict_logistic  # noqa: E402
from qawam_ml.rehab24 import REPO_ROOT  # noqa: E402

DEFAULT_ROOT = REPO_ROOT / "data" / "raw" / "knee-pad"
DEFAULT_OUT = REPO_ROOT / "data" / "derived" / "fusion-model"
EXERCISES = {0: "squat", 1: "squat", 2: "squat", 3: "leg extension", 4: "leg extension", 5: "leg extension",
             6: "walking", 7: "walking", 8: "walking"}
CORRECT = (0, 3, 6)
MUSCLES = ("thigh front", "thigh back", "shin", "calf")  # sensors 1-4 right leg, 5-8 left leg
WINDOWS = 6


def injured_sides(metadata: str) -> dict[str, str]:
    out = {}
    for line in metadata.splitlines():
        parts = line.split("\t")
        if len(parts) >= 7 and parts[0].strip().isdigit() and parts[5].strip() in ("left", "right"):
            out[parts[0].strip()] = parts[5].strip()
    return out


def order_sensors(injured: str) -> list[int]:
    """Sensor indices with the injured leg first."""
    right, left = [0, 1, 2, 3], [4, 5, 6, 7]
    return right + left if injured == "right" else left + right


def windows(x: np.ndarray) -> list[np.ndarray]:
    return [w for w in np.array_split(x, WINDOWS, axis=-1) if w.shape[-1]]


def imu_features(imu: np.ndarray) -> np.ndarray:
    """(8 sensors, 6 axes, T) -> per sensor: acceleration and rotation size and spread, whole rep and over time."""
    acc, gyro = np.linalg.norm(imu[:, :3], axis=1), np.linalg.norm(imu[:, 3:], axis=1) / 100
    per = [imu[:, :3].mean(-1), imu[:, :3].std(-1), imu[:, 3:].std(-1) / 100,
           np.stack([acc.std(-1), gyro.mean(-1), gyro.max(-1), np.abs(np.diff(acc, axis=-1)).mean(-1) * 10], 1),
           np.stack([w.mean(-1) for w in windows(gyro)], 1)]
    return np.concatenate(per, axis=1)


def emg_features(emg: np.ndarray) -> np.ndarray:
    """(8 sensors, T) millivolts -> per sensor: log muscle activity, shape over time, frequency proxy."""
    x = emg - emg.mean(-1, keepdims=True)
    rms = np.sqrt((x**2).mean(-1)) + 1e-6
    over_time = np.stack([np.sqrt((w**2).mean(-1)) for w in windows(x)], 1)
    crossings = (np.diff(np.signbit(x), axis=-1)).mean(-1)
    share = rms / rms.sum()
    return np.concatenate([np.log(rms)[:, None], over_time / rms[:, None], crossings[:, None], share[:, None]], axis=1)


def load(root: Path) -> list[dict[str, Any]]:
    sides = injured_sides((root / "metadata.txt").read_text(encoding="utf-8", errors="replace"))
    archive = zipfile.ZipFile(root / "dataset.zip")
    names = set(archive.namelist())
    read = lambda n: np.load(io.BytesIO(archive.read(n)), allow_pickle=False)  # noqa: E731
    rows = []
    for name in sorted(n for n in names if n.endswith("imu.npy")):
        _, subject, label, _, _ = name.split("/")
        person, other = subject.split("_")[1], name.replace("imu.npy", "emg.npy")
        if person not in sides or other not in names:
            continue
        imu, emg = read(name), read(other)
        if imu.shape[0] != 48 or emg.shape[0] != 8 or imu.shape[1] < 30 or not (np.isfinite(imu).all() and np.isfinite(emg).all()):
            continue
        order = order_sensors(sides[person])
        rows.append({"person": person, "exercise": EXERCISES[int(label)], "label": int(label), "y": int(int(label) not in CORRECT),
                     "imu": imu_features(imu.reshape(8, 6, -1)[order]), "emg": emg_features(emg[order]),
                     "seconds": imu.shape[1] / 148.148})
    return rows


def vector(row: Mapping[str, Any], kind: str, sensors: Sequence[int] | None = None) -> np.ndarray:
    part = row[kind] if sensors is None else row[kind][list(sensors)]
    return np.append(part.ravel(), np.log(row["seconds"]))


def out_of_fold(rows: Sequence[dict[str, Any]], key: str, x: np.ndarray) -> None:
    y, ex = np.array([r["y"] for r in rows]), np.array([r["exercise"] for r in rows])
    who = np.array([r["person"] for r in rows])
    for person in sorted(set(who)):
        for e in set(ex[who == person]):  # one model per exercise
            test, train = (who == person) & (ex == e), (who != person) & (ex == e)
            for i, p in zip(np.flatnonzero(test), predict_logistic(fit_logistic(x[train], y[train], ex[train]), x[test]), strict=True):
                rows[i][key] = float(p)


def decide(rows: Sequence[dict[str, Any]], key: str) -> None:
    for r in rows:
        r[f"{key}_says"] = r[key] >= 0.5


def build_report(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    variants = {
        "motion": lambda r: vector(r, "imu"),
        "muscle": lambda r: vector(r, "emg"),
        "joined": lambda r: np.concatenate([vector(r, "imu"), vector(r, "emg")]),
        "motion, injured thigh only": lambda r: vector(r, "imu", [0]),
        "motion, both thighs": lambda r: vector(r, "imu", [0, 4]),
    }
    for name, make in variants.items():
        out_of_fold(rows, name, np.stack([make(r) for r in rows]))
        decide(rows, name)
    for r in rows:
        r["averaged"] = (r["motion"] + r["muscle"]) / 2
    decide(rows, "averaged")
    keys = [*variants, "averaged"]
    report: dict[str, Any] = {}
    for scope in ("squat", "leg extension", "walking"):
        part = [r for r in rows if r["exercise"] == scope]
        block = {k: evaluate(part, f"{k}_says", k) for k in keys}
        block["gain of averaged over motion"] = paired_gain(part, "averaged_says", "motion_says")
        block["gain of motion over muscle"] = paired_gain(part, "motion_says", "muscle_says")
        report[scope] = block
        for k in ("motion", "averaged"):
            block[f"not sure, {k}"] = abstention([{**r, "p_model": r[k], "model": r[f"{k}_says"]} for r in part])
        caught = {}
        for label in sorted({r["label"] for r in part if r["y"]}):
            wrong = [r for r in part if r["label"] == label]
            caught[str(label)] = {k: f"{sum(r[f'{k}_says'] for r in wrong)} / {len(wrong)}" for k in ("motion", "muscle", "averaged")}
        block["wrong reps caught, by type"] = caught
    return report


def markdown(report: Mapping[str, Any]) -> str:
    lines = ["# Sensor fusion on KneE-PAD (generated by ml/eval/fusion_model.py)", "",
             "| Exercise | Inputs | Reps | Patients | Majority | Accuracy | F1 (wrong) | Macro-F1 | AUC |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for scope, block in report.items():
        for k, m in block.items():
            if isinstance(m, dict) and "macro_f1" in m:
                lines.append(f"| {scope} | {k} | {m['reps']} | {m['people']} | {m['majority']} | {m['accuracy']} | {m['f1']} | "
                             f"{m['macro_f1']} {m['macro_f1_ci']} | {m['auc_within_exercise']} |")
    for scope, block in report.items():
        lines += ["", f"{scope}: " + json.dumps({k: v for k, v in block.items() if "macro_f1" not in v})]
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    if not (args.root / "dataset.zip").exists():
        print(f"no KneE-PAD dataset.zip under {args.root}", file=sys.stderr)
        return 1
    rows = load(args.root)
    print(f"{len(rows)} reps, {len({r['person'] for r in rows})} patients", flush=True)
    report = build_report(rows)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (args.out / "summary.md").write_text(markdown(report), encoding="utf-8")
    print(markdown(report))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())

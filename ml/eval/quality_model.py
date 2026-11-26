"""Was this rep done correctly, compared with the person's own correct reps? One model, three datasets.

Design and fixed settings: docs/superpowers/specs/2026-11-25-quality-model-and-fusion-design.md.
Every rep becomes phone-style 2D points -> movement channels -> differences from the person's own reference reps
-> logistic regression. Everything is scored on people the model never trained on.

  py -3.14 ml\\eval\\quality_model.py

REHAB24-6 people 7 and 9 (sealed test) are never read.
"""

from __future__ import annotations

import argparse
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

from gate_eval import auroc  # noqa: E402
from qawam_ml.filters import view_for_camera  # noqa: E402
from qawam_ml.packs import MEDIAPIPE_INDEX, REHAB24_JOINT_FOR_LANDMARK  # noqa: E402
from qawam_ml.rehab24 import REPO_ROOT, load_repetitions  # noqa: E402
from qawam_ml.selective import clopper_pearson_upper  # noqa: E402

RAW = REPO_ROOT / "data" / "raw"
DEFAULT_OUT = REPO_ROOT / "data" / "derived" / "quality-model"
LIMBS = ("LEFT_SHOULDER", "RIGHT_SHOULDER", "LEFT_ELBOW", "RIGHT_ELBOW", "LEFT_WRIST", "RIGHT_WRIST", "LEFT_HIP",
         "RIGHT_HIP", "LEFT_KNEE", "RIGHT_KNEE", "LEFT_ANKLE", "RIGHT_ANKLE")
POINTS = (*LIMBS, "HEAD")
P = {name: i for i, name in enumerate(POINTS)}
KINECT = dict(zip(POINTS, (4, 8, 5, 9, 6, 10, 12, 16, 13, 17, 14, 18, 3), strict=True))
REHAB24 = {**{n: REHAB24_JOINT_FOR_LANDMARK[n] for n in LIMBS}, "HEAD": 4}
MEDIAPIPE = {**{n: MEDIAPIPE_INDEX[n] for n in LIMBS}, "HEAD": MEDIAPIPE_INDEX["NOSE"]}
IRDS_EXCLUDED = "217"  # stopped mid-recording; the dataset's authors exclude them too
LENGTH = 48
L2, STEPS, RATE = 0.1, 800, 0.5
TARGET = 0.10
BOOTSTRAP = 1000
ANGLES = (("SHOULDER", "ELBOW", "WRIST"), ("HIP", "SHOULDER", "ELBOW"), ("SHOULDER", "HIP", "KNEE"), ("HIP", "KNEE", "ANKLE"))


@dataclass
class Rep:
    dataset: str
    person: str
    exercise: str
    group: tuple  # reps that may share a reference: same person, exercise, camera set-up
    order: tuple
    incorrect: int
    view: str
    channels: np.ndarray  # (LENGTH, C)
    seconds: float
    jerk: float
    patient: bool = False
    error: str = ""


# ---------------------------------------------------------------- features


def channels(points: np.ndarray) -> np.ndarray:
    """(T, 13, 2) image points -> (T, C): angles in units of 30 degrees, offsets in torso lengths."""
    mid = lambda a: (points[:, P[f"LEFT_{a}"]] + points[:, P[f"RIGHT_{a}"]]) / 2  # noqa: E731
    hips, shoulders = mid("HIP"), mid("SHOULDER")
    torso = np.median(np.linalg.norm(shoulders - hips, axis=1)) + 1e-12
    out = []
    for side in ("LEFT", "RIGHT"):
        for a, b, c in ANGLES:
            u = points[:, P[f"{side}_{a}"]] - points[:, P[f"{side}_{b}"]]
            v = points[:, P[f"{side}_{c}"]] - points[:, P[f"{side}_{b}"]]
            cos = (u * v).sum(1) / (np.linalg.norm(u, axis=1) * np.linalg.norm(v, axis=1) + 1e-12)
            out.append(np.degrees(np.arccos(np.clip(cos, -1, 1))) / 30)
        knee, ankle = points[:, P[f"{side}_KNEE"]], points[:, P[f"{side}_ANKLE"]]
        out.append((knee[:, 0] - ankle[:, 0]) / torso)
        out.append((points[:, P[f"{side}_ANKLE"], 1] - hips[:, 1]) / torso)
    trunk = shoulders - hips
    out.append(np.degrees(np.arctan2(trunk[:, 0], np.abs(trunk[:, 1]) + 1e-6)) / 30)
    out.append((points[:, P["LEFT_SHOULDER"], 1] - points[:, P["RIGHT_SHOULDER"], 1]) / torso)
    out.append((points[:, P["HEAD"], 0] - shoulders[:, 0]) / torso)
    out.append((points[:, P["HEAD"], 1] - shoulders[:, 1]) / torso)
    out.append(np.linalg.norm(points[:, P["LEFT_KNEE"]] - points[:, P["RIGHT_KNEE"]], axis=1) / torso)
    return np.stack(out, axis=1)


def resample(x: np.ndarray, n: int = LENGTH) -> np.ndarray:
    grid, t = np.linspace(0, len(x) - 1, n), np.arange(len(x))
    return np.stack([np.interp(grid, t, x[:, c]) for c in range(x.shape[1])], axis=1)


def smooth(x: np.ndarray, width: int = 5) -> np.ndarray:
    if len(x) < width:
        return x
    pad = np.pad(x, ((width // 2, width // 2), (0, 0)), mode="edge")
    return np.stack([np.convolve(pad[:, c], np.ones(width) / width, mode="valid") for c in range(x.shape[1])], axis=1)


def make_rep(points: np.ndarray, fps: float, **kw: Any) -> Rep | None:
    if len(points) < 8 or not np.isfinite(points).all():
        return None
    c = resample(smooth(channels(points)))
    jerk = float(np.abs(np.diff(c, n=2, axis=0)).mean())
    return Rep(channels=c, seconds=len(points) / fps, jerk=jerk, **kw)


def align(a: np.ndarray, b: np.ndarray, band: int = 12) -> np.ndarray:
    """For each frame of b, the mean of the frames of a that DTW aligns with it."""
    n, m = len(a), len(b)
    cost = np.abs(a[:, None, :] - b[None, :, :]).mean(axis=2)
    acc = np.full((n + 1, m + 1), np.inf)
    acc[0, 0] = 0
    rows = cost.tolist()
    table = acc.tolist()
    for i in range(1, n + 1):
        lo, hi = max(1, i - band), min(m, i + band)
        row, prev, c = table[i], table[i - 1], rows[i - 1]
        for j in range(lo, hi + 1):
            row[j] = c[j - 1] + min(prev[j - 1], prev[j], row[j - 1])
    i, j = n, m
    sums, counts = np.zeros_like(b), np.zeros((m, 1))
    while i > 0 and j > 0:
        sums[j - 1] += a[i - 1]
        counts[j - 1] += 1
        step = int(np.argmin((table[i - 1][j - 1], table[i - 1][j], table[i][j - 1])))
        i, j = (i - 1, j - 1) if step == 0 else ((i - 1, j) if step == 1 else (i, j - 1))
    return sums / np.maximum(counts, 1)


def compare(rep: Rep, ref: Rep) -> tuple[np.ndarray, np.ndarray, float]:
    """(per-channel mean |difference|, feature vector, one DTW distance) of a rep against one reference rep."""
    a, b = rep.channels, ref.channels
    diff = align(a, b) - b
    gap = np.abs(diff).mean(axis=0)
    peaks = np.concatenate([a.max(axis=0) - b.max(axis=0), a.min(axis=0) - b.min(axis=0)])
    reach = np.ptp(a, axis=0) - np.ptp(b, axis=0)
    tempo = np.log(rep.seconds / ref.seconds)
    rough = np.log((rep.jerk + 1e-4) / (ref.jerk + 1e-4))
    moving = np.ptp(b, axis=0)
    w = moving / (moving.sum() + 1e-6)  # channels that move in this exercise
    summary = [gap.mean(), gap.max(), float(w @ gap), float(w @ reach), abs(float(w @ reach)), tempo, abs(tempo), rough]
    return gap, np.concatenate([gap, np.abs(peaks), peaks, reach, summary]), float(w @ gap)


def personalise(reps: Sequence[Rep], k: int) -> list[dict[str, Any]]:
    """Score rows for every rep except each group's first k correct reps, which become its references."""
    groups: dict[tuple, list[Rep]] = defaultdict(list)
    for r in reps:
        groups[r.group].append(r)
    rows = []
    for members in groups.values():
        members = sorted(members, key=lambda r: r.order)
        refs = [r for r in members if not r.incorrect][:k]
        if len(refs) < k:
            continue
        own = [compare(x, y) for x in refs for y in refs if x is not y]
        spread = np.mean([o[0] for o in own], axis=0) + 0.05 if own else None
        noise = float(np.mean([o[2] for o in own])) + 0.05 if own else None
        for r in members:
            if any(r is x for x in refs):
                continue
            parts = [compare(r, ref) for ref in refs]
            gap, feats, dist = (np.mean([p[i] for p in parts], axis=0) for i in range(3))
            row = {"rep": r, "person": r.person, "exercise": r.exercise, "view": r.view, "y": r.incorrect,
                   "dtw": float(dist), "x": feats}
            if spread is not None:
                z = gap / spread
                row["dtw_z"] = float(dist) / noise
                row["x"] = np.concatenate([feats, z, [z.mean(), z.max(), float(dist) / noise]])
            rows.append(row)
    return rows


# ------------------------------------------------------------------- model


def fit_logistic(x: np.ndarray, y: np.ndarray, strata: np.ndarray) -> tuple[np.ndarray, ...]:
    """Weighted logistic regression; each class counts equally inside each exercise."""
    mean, std = x.mean(axis=0), x.std(axis=0) + 1e-6
    a = np.concatenate([np.clip((x - mean) / std, -5, 5), np.ones((len(x), 1))], axis=1)
    w = np.zeros(len(y))
    for s in set(strata):
        for c in (0, 1):
            mask = (strata == s) & (y == c)
            if mask.any():
                w[mask] = (strata == s).sum() / 2 / mask.sum()
    penalty = np.full(a.shape[1], L2)
    penalty[-1] = 0
    beta = np.zeros(a.shape[1])
    lip = 0.25 * np.linalg.eigvalsh((a * w[:, None]).T @ a / len(y))[-1] + L2
    step = 1 / lip
    momentum, t = beta.copy(), 1.0
    for _ in range(STEPS):
        p = 1 / (1 + np.exp(-(a @ momentum)))
        new = momentum - step * (a.T @ (w * (p - y)) / len(y) + penalty * momentum)
        t2 = (1 + np.sqrt(1 + 4 * t * t)) / 2
        momentum, beta, t = new + (t - 1) / t2 * (new - beta), new, t2
    return mean, std, beta


def predict_logistic(model: tuple[np.ndarray, ...], x: np.ndarray) -> np.ndarray:
    mean, std, beta = model
    a = np.concatenate([np.clip((x - mean) / std, -5, 5), np.ones((len(x), 1))], axis=1)
    return 1 / (1 + np.exp(-(a @ beta)))


def arrays(rows: Sequence[Mapping[str, Any]]) -> tuple[np.ndarray, ...]:
    return (np.stack([r["x"] for r in rows]), np.array([r["y"] for r in rows]), np.array([r["exercise"] for r in rows]),
            np.array([r["person"] for r in rows]))


def best_cut(score: np.ndarray, y: np.ndarray) -> float:
    """The cut-off with the best macro-F1 on these (training) people."""
    return float(max(np.unique(score), key=lambda t: macro_f1(y, score >= t)))


def leave_one_person_out(rows: Sequence[dict[str, Any]]) -> None:
    """Adds p_model (and decisions for the DTW baselines), each from other people only."""
    x, y, ex, who = arrays(rows)
    for person in sorted(set(who)):
        test, train = who == person, who != person
        p = predict_logistic(fit_logistic(x[train], y[train], ex[train]), x[test])
        for i, v in zip(np.flatnonzero(test), p, strict=True):
            rows[i]["p_model"], rows[i]["model"] = float(v), bool(v >= 0.5)
        for key in ("dtw", "dtw_z"):
            if key not in rows[0]:
                continue
            s = np.array([r[key] for r in rows])
            for e in set(ex[test]):
                part = train & (ex == e)
                cut = best_cut(s[part], y[part]) if part.any() else np.inf
                for i in np.flatnonzero(test & (ex == e)):
                    rows[i][f"{key}_says"] = bool(s[i] >= cut)


# ----------------------------------------------------------------- scoring


def prf(y: np.ndarray, p: np.ndarray) -> tuple[float, float, float]:
    y, p = np.asarray(y, bool), np.asarray(p, bool)
    tp = (y & p).sum()
    prec = tp / p.sum() if p.any() else 0.0
    rec = tp / y.sum() if y.any() else 0.0
    return float(prec), float(rec), float(2 * prec * rec / (prec + rec)) if prec + rec else 0.0


def macro_f1(y: np.ndarray, p: np.ndarray) -> float:
    y, p = np.asarray(y, bool), np.asarray(p, bool)
    return (prf(y, p)[2] + prf(~y, ~p)[2]) / 2


def evaluate(rows: Sequence[Mapping[str, Any]], decision: str, score: str | None, seed: int = 20261125) -> dict[str, Any]:
    y = np.array([bool(r["y"]) for r in rows])
    p = np.array([bool(r[decision]) for r in rows])
    who = np.array([r["person"] for r in rows])
    prec, rec, f1 = prf(y, p)
    people = sorted(set(who))
    index = {w: np.flatnonzero(who == w) for w in people}
    rng = np.random.default_rng(seed)
    draws = [macro_f1(y[i], p[i]) for i in (np.concatenate([index[people[k]] for k in rng.integers(0, len(people), len(people))])
                                            for _ in range(BOOTSTRAP))]
    out = {"reps": len(rows), "people": len(people), "majority": round(float(max(y.mean(), 1 - y.mean())), 3),
           "accuracy": round(float((y == p).mean()), 3), "precision": round(prec, 3), "recall": round(rec, 3), "f1": round(f1, 3),
           "macro_f1": round(macro_f1(y, p), 3), "macro_f1_ci": [round(float(np.percentile(draws, q)), 3) for q in (2.5, 97.5)]}
    if score:
        s = np.array([r[score] for r in rows])
        ex = np.array([r["exercise"] for r in rows])
        aucs = [auroc(list(s[ex == e]), list(y[ex == e].astype(int))) for e in sorted(set(ex))]
        aucs = [a for a in aucs if a is not None]
        out["auc_within_exercise"] = round(float(np.mean(aucs)), 3) if aucs else None
    return out


def paired_gain(rows: Sequence[Mapping[str, Any]], a: str, b: str, seed: int = 20261125) -> dict[str, Any]:
    """Macro-F1 of a minus b, with a 95% interval from resampling people."""
    y = np.array([bool(r["y"]) for r in rows])
    pa, pb = (np.array([bool(r[k]) for r in rows]) for k in (a, b))
    who = np.array([r["person"] for r in rows])
    people = sorted(set(who))
    index = {w: np.flatnonzero(who == w) for w in people}
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(BOOTSTRAP):
        i = np.concatenate([index[people[k]] for k in rng.integers(0, len(people), len(people))])
        draws.append(macro_f1(y[i], pa[i]) - macro_f1(y[i], pb[i]))
    return {"gain": round(macro_f1(y, pa) - macro_f1(y, pb), 3),
            "ci95": [round(float(np.percentile(draws, q)), 3) for q in (2.5, 97.5)]}


def abstention(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Answer only above a confidence chosen on the other people so the exact 95% bound on wrong answers is <= 10%."""
    conf = np.array([abs(r["p_model"] - 0.5) for r in rows])
    bad = np.array([bool(r["model"]) != bool(r["y"]) for r in rows])
    who = np.array([r["person"] for r in rows])
    answered, wrong, worst = 0, 0, 0.0
    for person in sorted(set(who)):
        o = who != person
        order = np.argsort(-conf[o])
        k = np.cumsum(bad[o][order])
        ok = [n for n in range(len(k)) if clopper_pearson_upper(int(k[n]), n + 1) <= TARGET]
        if not ok:
            continue
        chosen = (who == person) & (conf >= conf[o][order][ok[-1]])
        n, w = int(chosen.sum()), int(bad[chosen].sum())
        answered, wrong, worst = answered + n, wrong + w, max(worst, w / n if n else 0.0)
    return {"answered": answered, "of": len(rows), "wrong": wrong, "rate": round(wrong / answered, 3) if answered else None,
            "upper95": round(clopper_pearson_upper(wrong, answered), 3) if answered else None, "worst_person": round(worst, 3)}


def transfer(train: Sequence[dict[str, Any]], test: Sequence[dict[str, Any]]) -> None:
    """Fit once on one dataset, decide once on the other. Baseline cut-offs come from the training dataset too."""
    x, y, ex, _ = arrays(train)
    model = fit_logistic(x, y, ex)
    keys = [k for k in ("dtw", "dtw_z") if k in train[0]]
    cuts = {k: best_cut(np.array([r[k] for r in train]), y) for k in keys}
    for r, p in zip(test, predict_logistic(model, arrays(test)[0]), strict=True):
        r["p_model"], r["model"] = float(p), bool(p >= 0.5)
        for k in keys:
            r[f"{k}_says"] = bool(r[k] >= cuts[k])


# ----------------------------------------------------------------- loading


def load_irds(root: Path) -> list[Rep]:
    reps = []
    for f in sorted(root.glob("*.txt")):
        person, date, gesture, number, label, position = f.stem.split("_")
        if person == IRDS_EXCLUDED or label not in ("1", "2"):
            continue
        m = np.loadtxt(f, delimiter=",", ndmin=2)
        if m.shape[1] < 75:
            continue
        joints = m[:, :75].reshape(len(m), 25, 3)
        points = joints[:, [KINECT[n] for n in POINTS], :2] * (1, -1)  # the front view a phone sees; image y points down
        rep = make_rep(points, 30.0, dataset="irds", person=person, exercise=gesture, view="front",
                       group=(person, gesture, position), order=(int(date), int(number)), incorrect=int(label == "2"),
                       patient=person.startswith("2"))
        if rep:
            reps.append(rep)
    return reps


def load_rehab24(root: Path, exercises: Sequence[int]) -> list[Rep]:
    names = {1: "arm abduction", 4: "leg abduction", 5: "lunge", 6: "squat"}
    reps, cache = [], {}
    for split in ("train", "validation"):
        for r in load_repetitions(split, dataset_root=root, csv_path=None, filter_name="none", final=False,  # type: ignore[arg-type]
                                  caller="ml/eval/quality_model.py"):
            if r.exercise_id not in exercises or r.mocap_erroneous:
                continue
            for camera, path in ((17, r.joints_c17_30fps), (18, r.joints_c18_30fps)):
                if not path.exists():
                    continue
                if path not in cache:
                    cache[path] = np.load(path)
                points = cache[path][r.first_frame : r.last_frame + 1][:, [REHAB24[n] for n in POINTS], :2].astype(float)
                rep = make_rep(points, 30.0, dataset="rehab24", person=str(r.person_id), exercise=names[r.exercise_id],
                               view=view_for_camera(r.cam17_orientation, camera), group=(r.video_id, r.cam17_orientation, camera),
                               order=(r.repetition_number,), incorrect=int(r.correctness == 0))
                if rep:
                    reps.append(rep)
    return reps


def load_rehab26(root: Path, exercises: Sequence[int]) -> list[Rep]:
    from rehab26_eval import read_reps, view_bucket, viewing_angle

    names = {1: "arm abduction", 6: "squat"}
    reps, cache = [], {}
    for exercise in exercises:
        for r in read_reps(root, exercise):
            for camera in (1, 2, 3):
                path = root / "mp" / "mediapipe" / f"ex{exercise}" / f"{r.video_id}_cam{camera}_2d.npy"
                if path not in cache:
                    cache[path] = np.load(path)
                points = cache[path][r.first_frame : r.last_frame + 1][:, [MEDIAPIPE[n] for n in POINTS], :2] * (1920.0, 1080.0)
                rep = make_rep(points, 30.0, dataset="rehab26", person=r.person_id, exercise=names[exercise],
                               view=view_bucket(viewing_angle(r.orientation, camera)),
                               group=(r.video_id, r.orientation, camera), order=(r.repetition_number,),
                               incorrect=int(r.correctness == 0), error=r.error)
                if rep:
                    reps.append(rep)
    return reps


# ------------------------------------------------------------------ report


def block(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {"model": evaluate(rows, "model", "p_model"), "personal_dtw": evaluate(rows, "dtw_says", "dtw")}
    if "dtw_z_says" in rows[0]:
        out["personal_dtw_per_patient"] = evaluate(rows, "dtw_z_says", "dtw_z")
        out["gain_per_patient_over_dtw"] = paired_gain(rows, "dtw_z_says", "dtw_says")
    out["gain_over_dtw"] = paired_gain(rows, "model", "dtw_says")
    out["not_sure"] = abstention(rows)
    return out


def within(reps: Sequence[Rep], exercises: Sequence[str] | None = None) -> dict[str, Any]:
    """Leave-one-person-out blocks for K = 1 and K = 3, per exercise (own model each) or pooled if exercises is None."""
    out: dict[str, Any] = {}
    for k in (1, 3):
        for name in exercises or ["all"]:
            rows = personalise([r for r in reps if name == "all" or r.exercise == name], k)
            if len({r["person"] for r in rows}) < 3 or len({r["y"] for r in rows}) < 2:
                out[f"k{k} {name}"] = {"skipped": f"{len(rows)} reps"}
                continue
            leave_one_person_out(rows)
            out[f"k{k} {name}"] = block(rows)
            if any(r["rep"].patient for r in rows):
                out[f"k{k} {name} patients"] = block([r for r in rows if r["rep"].patient])
    return out


def across(train_reps: Sequence[Rep], test_reps: Sequence[Rep], exercise: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k in (1, 3):
        train = personalise([r for r in train_reps if r.exercise == exercise], k)
        test = personalise([r for r in test_reps if r.exercise == exercise], k)
        if train and test and len({r["y"] for r in test}) == 2:
            transfer(train, test)
            out[f"k{k}"] = block(test)
    return out


def leave_one_dataset_out(sets: Mapping[str, Sequence[Rep]]) -> dict[str, Any]:
    """Fit on all the other datasets (every exercise pooled), test once on the one left out."""
    out: dict[str, Any] = {}
    for k in (1, 3):
        rows = {name: personalise(reps, k) for name, reps in sets.items()}
        for name in rows:
            train = [{**r, "exercise": f"{other} {r['exercise']}"} for other in rows if other != name for r in rows[other]]
            transfer(train, rows[name])
            for e in ["all", *sorted({r["exercise"] for r in rows[name]})] if name != "IntelliRehabDS" else ["all"]:
                part = [r for r in rows[name] if e == "all" or r["exercise"] == e]
                if len({r["y"] for r in part}) == 2:
                    out[f"k{k} test {name} {e}"] = block(part)
    return out


def markdown(report: Mapping[str, Any]) -> str:
    lines = ["# Quality model (generated by ml/eval/quality_model.py)", "",
             "Macro-F1 on people the model never saw, 95% interval by resampling people. K = reference reps per person.", "",
             "| Test | Reps | People | Majority | Method | Accuracy | F1 (incorrect) | Macro-F1 | AUC | Gain over DTW | Not sure: answered, wrong, 95% upper |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for section, blocks in report.items():
        for name, b in blocks.items():
            if "model" not in b:
                lines.append(f"| {section}, {name} | {b.get('skipped')} | | | | | | | | | |")
                continue
            for method in ("model", "personal_dtw", "personal_dtw_per_patient"):
                if method not in b:
                    continue
                m, first = b[method], method == "model"
                g = {"model": b["gain_over_dtw"], "personal_dtw_per_patient": b.get("gain_per_patient_over_dtw")}.get(method)
                gain = f"{g['gain']:+} {g['ci95']}" if g else ""
                ns = b["not_sure"]
                sure = f"{ns['answered']} / {ns['of']}, {ns['rate']}, {ns['upper95']}" if first else ""
                lines.append(f"| {section}, {name} | {m['reps']} | {m['people']} | {m['majority']} | {method} | {m['accuracy']} | {m['f1']} | "
                             f"{m['macro_f1']} {m['macro_f1_ci']} | {m.get('auc_within_exercise')} | {gain} | {sure} |")
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw", type=Path, default=RAW)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    irds_dir, r24_dir, r26_dir = args.raw / "SkeletonData" / "Simplified", args.raw / "rehab24-6", args.raw / "rehab26"
    report: dict[str, Any] = {}
    irds = load_irds(irds_dir) if irds_dir.exists() else []
    r24 = load_rehab24(r24_dir, (1, 4, 5, 6)) if r24_dir.exists() else []
    r26 = load_rehab26(r26_dir, (6, 1)) if (r26_dir / "Segmentation.csv").exists() else []
    print(f"reps: irds {len(irds)}, rehab24 {len(r24)}, rehab26 {len(r26)}", flush=True)
    if irds:
        report["IntelliRehabDS"] = within(irds)
        print("irds done", flush=True)
    if r24:
        report["REHAB24-6 mocap 2D"] = within(r24, sorted({r.exercise for r in r24}))
        print("rehab24 done", flush=True)
    if r26:
        report["REHAB26 phone points"] = within(r26, sorted({r.exercise for r in r26}))
        print("rehab26 done", flush=True)
    if r24 and r26:
        for e in ("squat", "arm abduction"):
            report[f"train REHAB24-6, test REHAB26, {e}"] = across(r24, r26, e)
    sets = {n: r for n, r in (("IntelliRehabDS", irds), ("REHAB24-6", r24), ("REHAB26", r26)) if r}
    if len(sets) > 1:  # added after the two-dataset transfer above failed: exploratory
        report["leave one dataset out"] = leave_one_dataset_out(sets)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (args.out / "summary.md").write_text(markdown(report), encoding="utf-8")
    print(markdown(report))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())

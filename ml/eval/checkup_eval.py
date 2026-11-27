"""Accuracy test of the check-up timing (web/src/checkup/checkupTiming.ts) on public data.

Spec: docs/superpowers/specs/2026-11-26-checkup-test-mode-design.md. Pass rules are fixed there, before any app result.
The app's own TypeScript scores every recording (bundled with rolldown, as ml/pain/pain_batch.ts), so what is tested is
what ships.

  py -3.14 ml\\eval\\checkup_eval.py frames   body points -> data/derived/checkup/frames/<set>/<id>.json (MediaPipe layout)
  py -3.14 ml\\eval\\checkup_eval.py sample   draws and freezes the evaluation recordings -> data/derived/checkup/eval_set.json
  (two raters mark start and end in tools/label-checkup.html -> data/derived/checkup/labels_<rater>.json)
  py -3.14 ml\\eval\\checkup_eval.py score    runs the app's timing once and writes data/derived/checkup/result.json

Data (git-ignored, never committed): data/raw/sit2stand (Stanford sit2stand, npj Digital Medicine 2023; no licence
stated: evaluation only) and data/raw/kinecal (PhysioNet, CC0).
"""

from __future__ import annotations

import csv
import json
import random
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "data" / "raw"
OUT = REPO / "data" / "derived" / "checkup"
SEED = 20261127
N_STANFORD = 60

# OpenPose BODY_25 index -> MediaPipe Pose index (only the joints the timing and the face blur use)
BODY25_TO_MP = {0: 0, 2: 12, 3: 14, 4: 16, 5: 11, 6: 13, 7: 15, 9: 24, 10: 26, 11: 28, 12: 23, 13: 25, 14: 27, 15: 5, 16: 2,
                17: 8, 18: 7, 21: 29, 22: 32, 19: 31, 24: 30}
# Kinect v2 joint name -> MediaPipe Pose index
KINECT_TO_MP = {"Head": 0, "ShoulderLeft": 11, "ShoulderRight": 12, "ElbowLeft": 13, "ElbowRight": 14, "WristLeft": 15,
                "WristRight": 16, "HipLeft": 23, "HipRight": 24, "KneeLeft": 25, "KneeRight": 26, "AnkleLeft": 27,
                "AnkleRight": 28, "FootLeft": 31, "FootRight": 32}
KINECAL_TESTS = {"sts5": "STS-5", "tug": "Get-Up-And-Go"}
# KINECAL groups used to set thresholds (healthy adults) vs. the test groups (spec)
KINECAL_TUNING_GROUPS = {"HA"}


def empty_landmarks() -> list[dict[str, float]]:
    return [{"x": 0.0, "y": 0.0, "visibility": 0.0} for _ in range(33)]


def stanford_frames(points: np.ndarray, fps: float, width: float, height: float) -> list[dict[str, Any]]:
    """OpenPose BODY_25 (frames x 75: x, y, confidence in pixels) -> app frames; confidence 0 means not detected."""
    frames = []
    for i, row in enumerate(points.reshape(len(points), 25, 3)):
        marks = empty_landmarks()
        for src, dst in BODY25_TO_MP.items():
            x, y, c = (float(v) for v in row[src])
            if c > 0 and np.isfinite(x) and np.isfinite(y):
                marks[dst] = {"x": x / width, "y": y / height, "visibility": c}
        seen = any(m["visibility"] > 0 for m in marks)
        frames.append({"timeSeconds": i / fps, "width": width, "height": height, "landmarks": marks if seen else None})
    return frames


def kinecal_side_frames(skeletons: list[tuple[int, dict[str, tuple[float, float, float, bool]]]]) -> list[dict[str, Any]]:
    """Kinect 3D joints (camera in front of the person) -> an orthographic side view (depth across, height up), like a
    phone placed to the person's side. Inferred joints get visibility 0.5, tracked 0.95."""
    width, height, scale = 640.0, 480.0, 100.0  # 1 m = 100 px
    t0 = skeletons[0][0]
    zs = [j[2] for _, joints in skeletons for j in joints.values()]
    ys = [j[1] for _, joints in skeletons for j in joints.values()]
    z0, y0 = (min(zs) + max(zs)) / 2, max(ys)
    frames = []
    for tick, joints in skeletons:
        marks = empty_landmarks()
        for name, idx in KINECT_TO_MP.items():
            if name in joints:
                x, y, z, tracked = joints[name]
                marks[idx] = {"x": (width / 2 + (z - z0) * scale) / width, "y": (40 + (y0 - y) * scale) / height,
                              "visibility": 0.95 if tracked else 0.5}
        # file names are clock times in milliseconds (about 33 apart at 30 fps), checked on the data 2026-11-27
        frames.append({"timeSeconds": (tick - t0) / 1e3, "width": width, "height": height, "landmarks": marks})
    return frames


def read_kinecal(folder: Path) -> list[tuple[int, dict[str, tuple[float, float, float, bool]]]]:
    out = []
    for path in sorted(folder.glob("*.txt"), key=lambda p: int(p.stem)):
        joints = {}
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[1] in ("Tracked", "Inferred"):
                joints[parts[0]] = (float(parts[2]), float(parts[3]), float(parts[4]), parts[1] == "Tracked")
        if joints:
            out.append((int(path.stem), joints))
    return out


def kinecal_groups() -> dict[str, str]:
    """Folder number -> group code from register.csv (part_id like 'SPPB2' -> folder '2')."""
    groups = {}
    with (RAW / "kinecal" / "register.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            digits = "".join(ch for ch in r["part_id"] if ch.isdigit())
            if digits:
                groups[str(int(digits))] = r["group"]
    return groups


def make_frames() -> dict[str, int]:
    counts = {"stanford": 0, "kinecal": 0}
    rate = {}
    with (RAW / "sit2stand" / "dataMovement.csv").open(encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f):
            if r["framerate"]:
                rate[r["subjectid"]] = float(r["framerate"])
    (OUT / "frames" / "stanford").mkdir(parents=True, exist_ok=True)
    for path in sorted((RAW / "sit2stand" / "np" / "np").glob("*.npy")):
        if path.stem not in rate:
            continue
        points = np.load(path, allow_pickle=False)
        xy = points.reshape(len(points), 25, 3)
        seen = xy[:, :, 2] > 0
        width = float(np.nanmax(np.where(seen, xy[:, :, 0], np.nan))) * 1.05 if seen.any() else 1.0
        height = float(np.nanmax(np.where(seen, xy[:, :, 1], np.nan))) * 1.05 if seen.any() else 1.0
        frames = stanford_frames(points, rate[path.stem], width, height)
        (OUT / "frames" / "stanford" / f"{path.stem}.json").write_text(json.dumps(frames), encoding="utf-8")
        counts["stanford"] += 1
    for person in sorted((RAW / "kinecal" / "skel").glob("*")):
        for kind, name in KINECAL_TESTS.items():
            for folder in person.glob(f"*{name}*"):
                skeletons = read_kinecal(folder)
                if len(skeletons) < 10:
                    continue
                target = OUT / "frames" / f"kinecal_{kind}"
                target.mkdir(parents=True, exist_ok=True)
                (target / f"{person.name}.json").write_text(json.dumps(kinecal_side_frames(skeletons)), encoding="utf-8")
                counts["kinecal"] += 1
    return counts


def sample() -> dict[str, Any]:
    """Fixed before any app result: 60 random Stanford recordings; every KINECAL test-group recording."""
    stanford = sorted(p.stem for p in (OUT / "frames" / "stanford").glob("*.json"))
    picked = sorted(random.Random(SEED).sample(stanford, N_STANFORD))
    groups = kinecal_groups()
    kinecal = {kind: sorted(p.stem for p in (OUT / "frames" / f"kinecal_{kind}").glob("*.json")
                            if groups.get(p.stem) and groups[p.stem] not in KINECAL_TUNING_GROUPS)
               for kind in KINECAL_TESTS}
    frozen = {"seed": SEED, "stanford_sts5": picked, "kinecal_sts5": kinecal["sts5"], "kinecal_tug": kinecal["tug"]}
    path = OUT / "eval_set.json"
    if path.exists():
        raise SystemExit(f"{path} exists: the evaluation set is frozen")
    path.write_text(json.dumps(frozen, indent=1), encoding="utf-8")
    folders = {"stanford_sts5": "stanford", "kinecal_sts5": "kinecal_sts5", "kinecal_tug": "kinecal_tug"}
    (OUT / "to_label").mkdir(exist_ok=True)
    for key, folder in folders.items():
        for rec in frozen[key]:  # the labelling page reads the set from the file name: <set>__<id>.json
            src = OUT / "frames" / folder / f"{rec}.json"
            (OUT / "to_label" / f"{key}__{rec}.json").write_bytes(src.read_bytes())
    return frozen


def icc21(a: np.ndarray, b: np.ndarray) -> float:
    """ICC(2,1): two-way random effects, absolute agreement, single measurement (Shrout and Fleiss)."""
    x = np.column_stack([a, b]).astype(float)
    n, k = x.shape
    grand = x.mean()
    msr = k * ((x.mean(axis=1) - grand) ** 2).sum() / (n - 1)
    msc = n * ((x.mean(axis=0) - grand) ** 2).sum() / (k - 1)
    sse = ((x - x.mean(axis=1, keepdims=True) - x.mean(axis=0, keepdims=True) + grand) ** 2).sum()
    mse = sse / ((n - 1) * (k - 1))
    return float((msr - mse) / (msr + (k - 1) * mse + k * (msc - mse) / n))


def agreement(app: list[float], ref: list[float], n_boot: int = 2000) -> dict[str, Any]:
    a, r = np.asarray(app, float), np.asarray(ref, float)
    diff = a - r
    rng = np.random.default_rng(SEED)
    boots = []
    for _ in range(n_boot):
        i = rng.integers(0, len(a), len(a))
        if np.ptp(r[i]) > 0:
            boots.append(icc21(a[i], r[i]))
    return {"n": len(a), "icc21": round(icc21(a, r), 3), "icc21_95": [round(float(q), 3) for q in np.percentile(boots, [2.5, 97.5])],
            "mae_s": round(float(np.abs(diff).mean()), 3), "bias_s": round(float(diff.mean()), 3),
            "limits_of_agreement_s": [round(float(diff.mean() - 1.96 * diff.std(ddof=1)), 3),
                                      round(float(diff.mean() + 1.96 * diff.std(ddof=1)), 3)]}


def run_app(kind: str, paths: list[Path]) -> list[dict[str, Any]]:
    """The app's analyseCheckup on each recording, start = first movement (recorded videos have no 'go')."""
    bundle, listing, result = OUT / "checkupBatch.cjs", OUT / "batch_in.json", OUT / "batch_out.json"
    listing.write_text(json.dumps({"kind": kind, "files": [str(p) for p in paths]}), encoding="utf-8")
    rolldown = REPO / "node_modules" / "rolldown" / "bin" / "cli.mjs"
    subprocess.run(["node", str(rolldown), str(REPO / "ml" / "eval" / "checkup_batch.ts"), "--platform", "node", "--format", "cjs",
                    "--file", str(bundle), "--logLevel", "silent"], check=True)
    subprocess.run(["node", str(bundle), str(listing), str(result)], check=True)
    return json.loads(result.read_text(encoding="utf-8"))


def starts_standing(frames: list[dict[str, Any]]) -> bool:
    """Spec rule: mean hip height above the ankle in the first 0.5 s is above half of the clip's 5-95 percentile range."""
    h, t = [], []
    for f in frames:
        m = f["landmarks"]
        if not m:
            continue
        side = [(m[a]["y"] - m[hip]["y"]) * f["height"] for hip, a in ((23, 27), (24, 28))
                if m[hip]["visibility"] > 0.35 and m[a]["visibility"] > 0.35]
        if side:
            h.append(side[-1])
            t.append(f["timeSeconds"])
    if len(h) < 3:
        return False
    hs, ts = np.array(h), np.array(t)
    lo, hi = np.percentile(hs, 5), np.percentile(hs, 95)
    return bool(hi > lo and (hs[ts < ts[0] + 0.5].mean() - lo) / (hi - lo) > 0.5)


def reference(ids: list[str], dataset: str) -> dict[str, tuple[float, float]]:
    """Mean of the raters' (start, end) seconds per recording; recordings a rater skipped are left out."""
    files = sorted(OUT.glob("labels_*.json"))
    if len(files) < 2:
        raise SystemExit("needs labels from two raters: data/derived/checkup/labels_<rater>.json")
    per = [json.loads(f.read_text(encoding="utf-8")).get(dataset, {}) for f in files]
    out = {}
    for rec in ids:
        marks = [p[rec] for p in per if rec in p and p[rec].get("end") is not None]
        if len(marks) == len(per):
            out[rec] = (float(np.mean([m["start"] for m in marks])), float(np.mean([m["end"] for m in marks])))
    return out


def count_exact(stand_ups: dict[str, list[float]], ref: dict[str, tuple[float, float]]) -> float:
    """Share of recordings where the app finds exactly 5 stand-ups between the raters' mean start and end."""
    return float(np.mean([sum(s <= t <= e for t in stand_ups[i]) == 5 for i, (s, e) in ref.items()]))


def score() -> dict[str, Any]:
    frozen = json.loads((OUT / "eval_set.json").read_text(encoding="utf-8"))
    load = lambda folder, i: json.loads((OUT / "frames" / folder / f"{i}.json").read_text(encoding="utf-8"))  # noqa: E731
    standing = [i for i in frozen["stanford_sts5"] if starts_standing(load("stanford", i))]
    sts5_rule, tug_rule = {"icc": 0.90, "mae": 0.5}, {"icc": 0.85, "mae": 1.0}
    report: dict[str, Any] = {}
    for name, key, kind, folder, rule, ids in (
            ("stanford_sts5", "stanford_sts5", "sts5", "stanford", sts5_rule,
             [i for i in frozen["stanford_sts5"] if i not in standing]),
            ("stanford_sts5_standing_start", "stanford_sts5", "sts5", "stanford", None, standing),  # reported, not judged
            ("kinecal_sts5", "kinecal_sts5", "sts5", "kinecal_sts5", sts5_rule, frozen["kinecal_sts5"]),
            ("kinecal_tug", "kinecal_tug", "tug", "kinecal_tug", tug_rule, frozen["kinecal_tug"])):
        if not ids:
            continue
        results = run_app(kind, [OUT / "frames" / folder / f"{i}.json" for i in ids])
        ref = reference(ids, key)
        got = {i: r for i, r in zip(ids, results) if r["ok"]}
        both = [i for i in ids if i in got and i in ref]
        block: dict[str, Any] = {"recordings": ids if rule is None else len(ids), "with_reference": len(ref),
                                 "app_result_rate": round(len(got) / len(ids), 3), "no_result_reasons": {}}
        for r in results:
            if not r["ok"]:
                block["no_result_reasons"][r["reason"]] = block["no_result_reasons"].get(r["reason"], 0) + 1
        if len(both) >= 3:
            block |= agreement([got[i]["seconds"] for i in both], [ref[i][1] - ref[i][0] for i in both])
            raters = [json.loads(f.read_text(encoding="utf-8")).get(key, {}) for f in sorted(OUT.glob("labels_*.json"))[:2]]
            r1 = [raters[0][i]["end"] - raters[0][i]["start"] for i in both]
            r2 = [raters[1][i]["end"] - raters[1][i]["start"] for i in both]
            block["raters"] = agreement(r1, r2)
            if kind == "sts5":
                block["count_exact"] = round(count_exact({i: got[i]["standUps"] for i in both}, {i: ref[i] for i in both}), 3)
            if rule is not None:
                block["passes"] = (block["icc21"] >= rule["icc"] and block["mae_s"] <= rule["mae"]
                                   and (kind != "sts5" or (block["app_result_rate"] >= 0.80 and block["count_exact"] >= 0.95)))
        report[name] = block
    (OUT / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main(argv: list[str]) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    if argv[:1] == ["frames"]:
        print(make_frames())
    elif argv[:1] == ["sample"]:
        frozen = sample()
        print({k: len(v) for k, v in frozen.items() if isinstance(v, list)})
    elif argv[:1] == ["score"]:
        print(json.dumps(score(), indent=1))
    else:
        print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

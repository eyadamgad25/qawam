"""Gate 2.0 on Fit3D: does the camera-view gate hold on new people, and can a learned score do better?

Fit3D (fit3d.imar.ro; Fieraru et al., CVPR 2021; non-commercial research
licence, single user) films people from 4 calibrated RGB cameras with Vicon
motion capture. ``notebooks/fit3d_extract_colab.ipynb`` runs MediaPipe Pose
Lite on the chosen exercises in Colab and saves, per subject x action x
camera, an ``.npz`` with:

  frames  sampled video frame indices          (N,)
  marks   MediaPipe landmarks, N x 33 x 5       (x px, y px, z px, visibility, presence; NaN = no pose)
  gt2d    Vicon joints projected into the camera, N x 25 x 2 (Human3.6M order + hands/feet)
  gt3d    the same joints in 3D world coordinates, N x 25 x 3 (the truth for every camera)
  meta    json: subject, action, camera, fps, width, height

This script never refits the shipped rule: the view cut-offs come from
``rules/gate/view-rule.json`` (fitted on REHAB24-6), so section A is an
external check on 8 people it never saw. Section B fits the learned gate
(``quality.LogisticGate`` on every feature, Learn-then-Test at alpha 0.10)
leave-one-person-out, like ``gate_eval.py``.

Reps are found on the 3D angle, so a camera that cannot see the movement
still contributes its reps (as wrong measurements the gate must refuse).
A rep is "wrong" when, after the one-rep calibration (first rep of each
subject x action x camera x side sets the offset), its MediaPipe angle is on
average more than 10 deg from motion capture; the calibration rep is left out.

  py -3.14 ml\\eval\\fit3d_gate_eval.py --features data\\derived\\fit3d-landmarks
"""

from __future__ import annotations

import argparse
import json
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

from gate_eval import nested_gate, person_rate_interval  # noqa: E402
from qawam_ml.kimore import segment_reps  # noqa: E402
from qawam_ml.packs import MEDIAPIPE_INDEX, compute_angle, load_packs, resolve_pack, transform_angle  # noqa: E402
from qawam_ml.quality import rep_features  # noqa: E402
from qawam_ml.rehab24 import REPO_ROOT  # noqa: E402
from qawam_ml.selective import clopper_pearson_upper  # noqa: E402

DEFAULT_FEATURES = REPO_ROOT / "data" / "derived" / "fit3d-landmarks"
DEFAULT_OUT = REPO_ROOT / "data" / "derived" / "fit3d-gate"
TOLERANCE_DEG = 10.0
MIN_DETECTION = 0.5  # same as the app's MIN_DETECTION_RATE
ENTER, LEAVE = 0.3, 0.15  # web/src/exercise/liveCoach.ts ENTER_FRACTION / EXIT_FRACTION

# Fit3D joints3d_25 follow Human3.6M: 1-3 right leg, 4-6 left leg, 11-13 left arm, 14-16 right arm.
H36M_FOR_LANDMARK = {
    "RIGHT_HIP": 1, "RIGHT_KNEE": 2, "RIGHT_ANKLE": 3,
    "LEFT_HIP": 4, "LEFT_KNEE": 5, "LEFT_ANKLE": 6,
    "LEFT_SHOULDER": 11, "LEFT_ELBOW": 12, "LEFT_WRIST": 13,
    "RIGHT_SHOULDER": 14, "RIGHT_ELBOW": 15, "RIGHT_WRIST": 16,
}

# action-name keyword -> pack; the first match wins, so put specific words first
ACTION_PACKS = (
    ("lunge", "lower-limb.lunge"),
    ("squat", "lower-limb.squat"),
    ("lateral_raise", "upper-limb.shoulder-abduction"),
    ("side_raise", "upper-limb.shoulder-abduction"),
    ("front_raise", "upper-limb.shoulder-flexion"),
)


def pack_for_action(action: str) -> str | None:
    name = action.lower().replace(" ", "_").replace("-", "_")
    return next((pack for word, pack in ACTION_PACKS if word in name), None)


# ------------------------------------------------------------------ angles


def angle_curves(points: Sequence[Mapping[str, Sequence[float]]], resolved) -> np.ndarray:
    angle = next(a for a in resolved.angles if a.name == resolved.primary_angle)
    values = [compute_angle(p, angle) for p in points]
    return np.array([np.nan if v is None else v for v in values], dtype=float)


def truth_curve(gt3d: np.ndarray, resolved, swap: bool) -> np.ndarray:
    """The pack's primary angle from the 3D motion-capture joints: the same for every camera."""
    angle = next(a for a in resolved.angles if a.name == resolved.primary_angle)

    def index(name: str) -> int:
        if swap:
            name = name.replace("LEFT", "TMP").replace("RIGHT", "LEFT").replace("TMP", "RIGHT")
        return H36M_FOR_LANDMARK[name]

    a, b, c = (gt3d[:, index(n)] for n in angle.landmarks)
    u, v = a - b, c - b
    with np.errstate(invalid="ignore", divide="ignore"):
        cos = np.einsum("ij,ij->i", u, v) / (np.linalg.norm(u, axis=1) * np.linalg.norm(v, axis=1))
    interior = np.degrees(np.arccos(np.clip(cos, -1.0, 1.0)))
    return np.array([transform_angle(float(x), angle.transform) for x in interior])


def mp_points(marks: np.ndarray) -> list[dict[str, tuple[float, float]]]:
    out = []
    for frame in marks:
        if not np.isfinite(frame[0, 0]):
            out.append({})
            continue
        out.append({name: (float(frame[i, 0]), float(frame[i, 1])) for name, i in MEDIAPIPE_INDEX.items()})
    return out


def gt_side_swapped(videos: Sequence[Mapping[str, Any]]) -> bool:
    """True if Fit3D's left/right labels are the mirror of MediaPipe's (checked on shoulders)."""
    same, mirrored = [], []
    for video in videos:
        marks, gt2d = video["marks"], video["gt2d"]
        ok = np.isfinite(marks[:, 0, 0])
        if not ok.any():
            continue
        ls, rs = marks[ok, MEDIAPIPE_INDEX["LEFT_SHOULDER"], :2], marks[ok, MEDIAPIPE_INDEX["RIGHT_SHOULDER"], :2]
        gl, gr = gt2d[ok, 11], gt2d[ok, 14]
        same.append(np.median(np.linalg.norm(ls - gl, axis=1) + np.linalg.norm(rs - gr, axis=1)))
        mirrored.append(np.median(np.linalg.norm(ls - gr, axis=1) + np.linalg.norm(rs - gl, axis=1)))
    return bool(same) and float(np.median(mirrored)) < float(np.median(same))


# ------------------------------------------------------------------- units


def segment_on_truth(curve: np.ndarray) -> list[tuple[int, int]]:
    """App-style rep segmentation on the motion-capture angle (flipped if the rest pose is the high end)."""
    finite = np.where(np.isfinite(curve), curve, np.nanmedian(curve))
    rest = float(np.median(finite[:10]))
    if rest > (finite.max() + finite.min()) / 2:
        finite = finite.max() - finite
    return segment_reps(finite, enter=ENTER, leave=LEAVE, min_frames=5)


def build_units(videos: Sequence[Mapping[str, Any]], swap: bool) -> list[dict[str, Any]]:
    packs = load_packs()
    units = []
    for video in videos:
        pack_id = pack_for_action(video["meta"]["action"])
        if pack_id is None:
            continue
        mp_pts = mp_points(video["marks"])
        for side in ("left", "right"):
            resolved = resolve_pack(packs[pack_id], side)
            gt_curve, mp_curve = truth_curve(video["gt3d"], resolved, swap), angle_curves(mp_pts, resolved)
            reps = segment_on_truth(gt_curve)
            offset = None
            for index, (a, b) in enumerate(reps):
                diff = mp_curve[a : b + 1] - gt_curve[a : b + 1]
                seen = np.isfinite(diff)
                features = rep_features(video["marks"][a : b + 1], resolved)
                detected = features["detect_rate"] >= MIN_DETECTION and seen.mean() >= MIN_DETECTION
                if index == 0:
                    offset = float(np.mean(diff[seen])) if detected else None
                    continue  # the calibration rep is never scored
                error = float(np.mean(np.abs(diff[seen] - offset))) if detected and offset is not None else None
                units.append({
                    "pack_id": pack_id,
                    "person_id": int(str(video["meta"]["subject"]).lstrip("s") or 0),
                    "action": video["meta"]["action"],
                    "camera": str(video["meta"]["camera"]),
                    "side": side,
                    "rep": index,
                    "detected": int(detected and offset is not None),
                    "error_deg": None if error is None else round(error, 3),
                    "wrong": int(error is None or error > TOLERANCE_DEG),
                    **{k: round(v, 5) for k, v in features.items()},
                })
    return units


# ----------------------------------------------------------------- reports


def shipped_rule(units: Sequence[Mapping[str, Any]], side_cut: float, front_cut: float) -> dict[str, Any]:
    views = {pid: p["view"] for pid, p in load_packs().items()}

    def accepts(u: Mapping[str, Any]) -> bool:
        if not u["detected"]:
            return False
        f = float(u["frontalness"])
        return f <= side_cut if views[u["pack_id"]] == "side" else f >= front_cut

    def summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        accepted = [u for u in rows if accepts(u)]
        k = sum(u["wrong"] for u in accepted)
        return {
            "units": len(rows),
            "always_speak_risk": round(statistics.fmean(u["wrong"] for u in rows), 3) if rows else None,
            "coverage": round(len(accepted) / len(rows), 3) if rows else 0.0,
            "accepted": len(accepted),
            "wrong_accepted": k,
            "false_cue_rate": round(k / len(accepted), 3) if accepted else None,
            "upper95": round(clopper_pearson_upper(k, len(accepted)), 3) if accepted else None,
        }

    def by(key: str) -> dict[str, Any]:
        return {str(v): summary([u for u in units if u[key] == v]) for v in sorted({u[key] for u in units})}

    overall = summary(units)
    people = by("person_id")
    overall.update(person_rate_interval([(p["wrong_accepted"], p["accepted"]) for p in people.values()]))
    return {"cuts": [side_cut, front_cut], "overall": overall, "by_pack": by("pack_id"), "by_camera": by("camera"), "by_person": people}


def build_report(units: Sequence[Mapping[str, Any]], swap: bool, alpha: float) -> dict[str, Any]:
    rule = json.loads((REPO_ROOT / "rules" / "gate" / "view-rule.json").read_text(encoding="utf-8"))
    report: dict[str, Any] = {
        "units": len(units),
        "people": sorted({u["person_id"] for u in units}),
        "gt_left_right_mirrored": swap,
        "shipped_rule": shipped_rule(units, rule["side_pack_max_frontalness"], rule["front_pack_min_frontalness"]),
    }
    if len(report["people"]) >= 3:
        detected = [u for u in units if u["detected"]]
        report["learned_gate"] = {m: nested_gate(detected, m, alpha, 0.10, 1.0) for m in ("view", "combined")}
        for result in report["learned_gate"].values():
            result.pop("_wrong", None)
    return report


def markdown(report: Mapping[str, Any]) -> str:
    rule = report["shipped_rule"]
    o = rule["overall"]
    lines = [
        "# Gate 2.0 on Fit3D",
        "",
        f"{report['units']} units (rep x camera x side) from people {report['people']}; Fit3D left/right mirrored vs MediaPipe: {report['gt_left_right_mirrored']}.",
        "",
        f"## A. Shipped view rule, cut-offs {rule['cuts']} from REHAB24-6 (not refitted)",
        "",
        f"Speaks on {o['coverage']:.0%} of units; wrong cues {o['wrong_accepted']} / {o['accepted']} = {o['false_cue_rate']} "
        f"(exact 95% upper {o['upper95']}); always speaking would be wrong {o['always_speak_risk']}.",
        "",
        "| Group | Units | Coverage | False cues | 95% upper |",
        "| --- | --- | --- | --- | --- |",
    ]
    for group in ("by_pack", "by_camera", "by_person"):
        for key, s in rule[group].items():
            lines.append(f"| {group[3:]} {key} | {s['units']} | {s['coverage']:.0%} | {s['wrong_accepted']} / {s['accepted']} | {s['upper95']} |")
    if "learned_gate" in report:
        lines += ["", "## B. Learned gate, leave-one-person-out, Learn-then-Test", "",
                  "| Score | Coverage | False-cue rate | People over alpha |", "| --- | --- | --- | --- |"]
        for name, g in report["learned_gate"].items():
            lines.append(f"| {name} | {g['coverage']:.0%} | {g['false_cue_rate']} | {g['people_over_alpha']} |")
    return "\n".join(lines) + "\n"


def load_videos(folder: Path) -> list[dict[str, Any]]:
    videos = []
    for path in sorted(folder.glob("*.npz")):
        data = np.load(path, allow_pickle=False)
        videos.append({
            "frames": data["frames"],
            "marks": data["marks"].astype(float),
            "gt2d": data["gt2d"].astype(float),
            "gt3d": data["gt3d"].astype(float),
            "meta": json.loads(str(data["meta"])),
        })
    return videos


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--features", type=Path, default=DEFAULT_FEATURES, help="folder of .npz files from the Colab notebook")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--alpha", type=float, default=0.10)
    args = parser.parse_args(argv)
    videos = load_videos(args.features)
    if not videos:
        print(f"no .npz files in {args.features}; run notebooks/fit3d_extract_colab.ipynb first", file=sys.stderr)
        return 1
    unmatched = sorted({v["meta"]["action"] for v in videos if pack_for_action(v["meta"]["action"]) is None})
    if unmatched:
        print("actions with no pack (skipped):", ", ".join(unmatched))
    swap = gt_side_swapped(videos)
    units = build_units(videos, swap)
    report = build_report(units, swap, args.alpha)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    text = markdown(report)
    (args.out / "summary.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

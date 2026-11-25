"""Two-day volunteer test: does a day 1 reference judge day 2 reps correctly?

Protocol and pass rule: docs/recording-kit/ (fixed before any recording). Videos: data/raw/two-day/P01_D1_squat_ok.mp4.
The cut-offs are the frozen ones in confirm_cuts.json; nothing is fitted here. Landmarks are cached next to the videos,
so a second run is quick.

  py -3.14 ml\\eval\\two_day_eval.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

EVAL_DIR = Path(__file__).resolve().parent
if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))

import quality_model as q  # noqa: E402
from confirm_reference import CUTS, K, remove_start, result  # noqa: E402
from qawam_ml.kimore import segment_reps  # noqa: E402

DEFAULT_ROOT = q.RAW / "two-day"
DEFAULT_OUT = q.REPO_ROOT / "data" / "derived" / "two-day"
NAME = re.compile(r"(?P<person>P\d{2})_D(?P<day>[12])_(?P<exercise>squat|legabd|armabd)_(?P<condition>ok|fault)$")
REPS, SLACK, MAX_LEFT_OUT, MIN_PEOPLE = 8, 1, 0.25, 8
MAX_FALSE, MAX_FALSE_UPPER, MIN_CAUGHT = 0.20, 0.35, 0.70
# channel index (per side, 6 channels each side) of the angle that moves, see quality_model.channels
MAIN = {"squat": 3, "legabd": 2, "armabd": 1}


def check_files(names: Sequence[str]) -> list[str]:
    """Problems with the set of file names (without extension); empty means complete."""
    problems = [f"name not understood: {n}" for n in names if not NAME.match(n)]
    matched = [m for n in names if (m := NAME.match(n))]
    have = {m.group(0) for m in matched}
    for person in sorted({m["person"] for m in matched}):
        for exercise in sorted({m["exercise"] for m in matched if m["person"] == person}):
            for day in "12":
                for condition in ("ok", "fault"):
                    if (name := f"{person}_D{day}_{exercise}_{condition}") not in have:
                        problems.append(f"missing: {name}")
    return problems


def rep_signal(points: np.ndarray, exercise: str) -> np.ndarray:
    """Degrees away from rest of the angle this exercise moves, on the side (or sides) that move."""
    c = q.channels(points) * 30
    left, right = c[:, MAIN[exercise]], c[:, 6 + MAIN[exercise]]
    if exercise == "squat":
        return 180 - (left + right) / 2
    side = left if np.ptp(left) >= np.ptp(right) else right
    return side if exercise == "armabd" else 180 - side


def split_reps(points: np.ndarray, exercise: str) -> list[tuple[int, int]]:
    return segment_reps(rep_signal(points, exercise), enter=0.5, leave=0.2, min_frames=8)


def video_points(path: Path) -> tuple[np.ndarray, float]:
    """(T, 13, 2) pixel points and frames per second; frames without a person repeat the last seen one."""
    cache = path.with_suffix(".points.npz")
    if cache.exists():
        saved = np.load(cache)
        return saved["points"], float(saved["fps"])
    import cv2
    from angle_eval import DEFAULT_MODEL, _landmarker, landmark_array

    capture = cv2.VideoCapture(str(path))
    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    width, height = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    mp, landmarker = _landmarker(DEFAULT_MODEL)
    index, rows = [q.MEDIAPIPE[n] for n in q.POINTS], []
    try:
        i = 0
        while True:
            ok, bgr = capture.read()
            if not ok:
                break
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
            found = landmarker.detect_for_video(image, int(i * 1000 / fps)).pose_landmarks
            if found:
                rows.append(landmark_array(found[0], width, height)[index, :2])
            elif rows:
                rows.append(rows[-1])
            i += 1
    finally:
        capture.release()
        landmarker.close()
    points = np.asarray(rows, dtype=float).reshape(-1, len(index), 2)
    np.savez_compressed(cache, points=points, fps=fps)
    return points, fps


def reps_of(name: str, points: np.ndarray, fps: float) -> list[q.Rep]:
    m = NAME.match(name)
    reps = []
    for number, (start, end) in enumerate(split_reps(points, m["exercise"])):
        rep = q.make_rep(points[start : end + 1], fps, dataset="two-day", person=m["person"], exercise=m["exercise"],
                         view=f"day {m['day']}", group=(m["person"], m["exercise"]),
                         order=(int(m["day"]), m["condition"] == "fault", number), incorrect=int(m["condition"] == "fault"))
        if rep:
            reps.append(rep)
    return reps


def false_alarm_interval(rows: Sequence[Mapping[str, Any]], seed: int = 20261125) -> tuple[float, float, float]:
    """Share of correct reps called wrong, with a 95% interval from resampling people."""
    correct = [r for r in rows if not r["y"]]
    by: dict[str, list[bool]] = {}
    for r in correct:
        by.setdefault(r["person"], []).append(r["dtw_z_says"])
    people, rng = sorted(by), np.random.default_rng(seed)
    draws = [np.mean([v for i in rng.integers(0, len(people), len(people)) for v in by[people[i]]]) for _ in range(q.BOOTSTRAP)]
    return (float(np.mean([r["dtw_z_says"] for r in correct])), *(float(np.percentile(draws, p)) for p in (2.5, 97.5)))


def verdict(rows: Sequence[dict[str, Any]], block: Mapping[str, Any], left_out: float) -> dict[str, Any]:
    rate, low, high = false_alarm_interval(rows)
    caught = float(np.mean([r["dtw_z_says"] for r in rows if r["y"]]))
    gain = block["gain_per_patient_over_plain"]
    checks = {
        f"at least {MIN_PEOPLE} people": len({r["person"] for r in rows}) >= MIN_PEOPLE,
        "at most a quarter of the videos left out": left_out <= MAX_LEFT_OUT,
        f"correct called wrong {rate:.1%} <= {MAX_FALSE:.0%}, interval {low:.1%}-{high:.1%} up to {MAX_FALSE_UPPER:.0%}":
            rate <= MAX_FALSE and high <= MAX_FALSE_UPPER,
        f"faults caught {caught:.1%} >= {MIN_CAUGHT:.0%}": caught >= MIN_CAUGHT,
        f"gain over the plain cut-off {gain['gain']} {gain['ci95']} above 0": gain["ci95"][0] > 0,
    }
    return {"passed": all(checks.values()), "checks": checks}


def build_report(reps: Sequence[q.Rep], left_out: Sequence[str], videos: int, cuts: Mapping[str, float]) -> dict[str, Any]:
    ready = {r.group for r in reps if (r.order[0], r.order[1]) == (1, False)}
    rows = [r for r in q.personalise([r for r in reps if r.group in ready], K)]
    report: dict[str, Any] = {"cuts": dict(cuts), "videos": videos, "left out": list(left_out)}
    day2 = [r for r in rows if r["rep"].view == "day 2"]
    report["day 2"] = result(day2, cuts)
    report["verdict"] = verdict(day2, report["day 2"], len(left_out) / max(videos, 1))
    report["day 1, same day"] = result([r for r in rows if r["rep"].view == "day 1"], cuts)
    report["day 2, starting posture removed"] = result(
        [r for r in q.personalise(remove_start([r for r in reps if r.group in ready]), K) if r["rep"].view == "day 2"], cuts)
    for key in ("exercise", "person"):
        report[f"day 2 by {key}"] = {v: {"correct called wrong": _count(day2, key, v, 0), "faults caught": _count(day2, key, v, 1)}
                                     for v in sorted({r[key] for r in day2})}
    return report


def _count(rows: Sequence[Mapping[str, Any]], key: str, value: str, y: int) -> str:
    part = [r for r in rows if r[key] == value and r["y"] == y]
    return f"{sum(r['dtw_z_says'] for r in part)} / {len(part)}"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--check-only", action="store_true", help="only check the file names")
    args = parser.parse_args(argv)
    videos = sorted(p for p in args.root.glob("*") if p.suffix.lower() in (".mp4", ".mov", ".mkv")) if args.root.exists() else []
    problems = check_files([p.stem for p in videos]) if videos else [f"no videos in {args.root}"]
    if problems or args.check_only:
        print("\n".join(problems) or "files complete")
        return int(bool(problems))
    reps, left_out = [], []
    for path in videos:
        points, fps = video_points(path)
        found = reps_of(path.stem, points, fps) if len(points) > 8 else []
        if abs(len(found) - REPS) > SLACK:
            left_out.append(f"{path.stem}: {len(found)} reps found")
        else:
            reps += found
        print(f"{path.stem}: {len(found)} reps", flush=True)
    report = build_report(reps, left_out, len(videos), json.loads(CUTS.read_text(encoding="utf-8")))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())

"""Tests for ml/eval/keraal_eval.py on a tiny fake KERAAL folder."""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

EVAL_DIR = Path(__file__).resolve().parents[2] / "ml" / "eval"
sys.path.insert(0, str(EVAL_DIR))
spec = importlib.util.spec_from_file_location("keraal_eval", EVAL_DIR / "keraal_eval.py")
keraal = importlib.util.module_from_spec(spec)
sys.modules["keraal_eval"] = keraal
spec.loader.exec_module(keraal)

ANVIL = """<?xml version="1.0" encoding="UTF-16"?>
<annotation><body><track name="Global evaluation" type="primary">
<el index="0" start="0" end="1"><attribute name="evaluation">{v}</attribute></el>
</track></body></annotation>"""


def _write(root: Path, group: str, person: str, take: int, verdicts: tuple[str, str], raise_deg: float, encoding: str):
    """Arms raise to raise_deg and back; an error rep raises them less."""
    stem = f"G{group[-2:]}-CTK-{person}-Brest-{take:03d}"
    positions = {}
    for f in range(60):
        lift = np.radians(raise_deg) * np.sin(np.pi * f / 59)
        frame = {"Nose": [0.5, 0.2, 0], "Left_hip": [0.45, 0.7, 0], "Right_hip": [0.55, 0.7, 0],
                 "Left_shoulder": [0.42, 0.35, 0], "Right_shoulder": [0.58, 0.35, 0]}
        for side, sx, sign in (("Left", 0.42, -1), ("Right", 0.58, 1)):
            elbow = [sx + sign * 0.15 * np.sin(lift), 0.35 + 0.15 * np.cos(lift)]
            frame[f"{side}_elbow"] = elbow + [0]
            frame[f"{side}_wrist"] = [elbow[0] + sign * 0.12 * np.sin(lift), elbow[1] + 0.12 * np.cos(lift), 0]
        positions[f"{f + 1}.0"] = frame
    (root / group / "blazepose").mkdir(parents=True, exist_ok=True)
    pose = root / group / "blazepose" / f"{stem.replace('-CTK', '-BP-CTK')}.json"
    pose.write_text(json.dumps({"positions": positions}))
    for annotator, verdict in zip("AB", verdicts):
        folder = root / group / f"annotator{annotator}"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{stem}.anvil").write_bytes(ANVIL.format(v=verdict).encode(encoding))


def test_personal_reference_ranks_errors_above_correct_recordings(tmp_path):
    for p, person in enumerate(("R1", "R2", "R3")):
        _write(tmp_path, "group1A", person, 1, ("Correct", "Correct"), 120 + 10 * p, "utf-16")
        for take in range(2, 6):
            _write(tmp_path, "group1A", person, take, ("Correct", "Correct"), 120 + 10 * p + take, "utf-8")
        for take in range(6, 9):
            _write(tmp_path, "group1A", person, take, ("Incorrect", "Incorrect"), 50 + 10 * p, "utf-8")
    for take in range(1, 4):
        _write(tmp_path, "group2A", "S1", take, ("Correct", "Correct"), 150, "utf-16")
    out = tmp_path / "out"
    assert keraal.main(["--root", str(tmp_path), "--out", str(out)]) == 0
    report = json.loads((out / "summary.json").read_text())
    assert report["recordings_scored"] == 21  # 3 patients x 7, references left out
    assert report["error_agreed"]["personal"]["auc"] == 1.0
    assert report["error_A"]["personal"]["errors"] == 9


def test_verdict_reader_handles_mislabelled_encoding(tmp_path):
    path = tmp_path / "x.anvil"
    path.write_bytes(ANVIL.format(v="Incomplete").encode("utf-8"))
    assert keraal.read_anvil(path) == "Incomplete"

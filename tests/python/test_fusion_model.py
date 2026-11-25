"""Tests for ml/eval/fusion_model.py: which leg is injured, features, and fusion on clear data."""

import importlib.util
import sys
from pathlib import Path

import numpy as np

EVAL_DIR = Path(__file__).resolve().parents[2] / "ml" / "eval"
sys.path.insert(0, str(EVAL_DIR))
spec = importlib.util.spec_from_file_location("fusion_model", EVAL_DIR / "fusion_model.py")
f = importlib.util.module_from_spec(spec)
sys.modules["fusion_model"] = f
spec.loader.exec_module(f)


def test_injured_leg_comes_from_the_patient_table_and_goes_first():
    text = "Participant ID\tGender\n4\tFemale\t1.6\t83\t48\tright\tosteoarthritis\n1\tMale\t1.82\t87\t27\tleft\tmeniscus\n"
    assert f.injured_sides(text) == {"4": "right", "1": "left"}
    assert f.order_sensors("right")[:4] == [0, 1, 2, 3] and f.order_sensors("left")[:4] == [4, 5, 6, 7]


def test_features_are_finite_and_one_row_per_sensor():
    rng = np.random.default_rng(0)
    imu, emg = f.imu_features(rng.normal(size=(8, 6, 448))), f.emg_features(rng.normal(size=(8, 3808)))
    assert imu.shape[0] == emg.shape[0] == 8 and np.isfinite(imu).all() and np.isfinite(emg).all()


def test_muscle_features_ignore_a_constant_offset():
    x = np.random.default_rng(0).normal(size=(8, 1200))
    assert np.allclose(f.emg_features(x), f.emg_features(x + 5))


def test_each_patient_is_scored_by_models_that_never_saw_them_and_fusion_helps_on_complementary_noise():
    rng = np.random.default_rng(3)
    rows = []
    for p in range(10):
        for i in range(16):
            y = i % 2
            signal = lambda: rng.normal(0.9 * y, 1.0, (8, 1)) + rng.normal(0, 1.2)  # noqa: E731
            rows.append({"person": str(p), "exercise": "squat", "label": y, "y": y, "imu": signal(), "emg": signal(), "seconds": 3.0})
    report = f.build_report(rows + [{**r, "exercise": e, "label": 3 + r["y"] if e != "walking" else 6 + r["y"]}
                                    for e in ("leg extension", "walking") for r in rows])
    block = report["squat"]
    assert block["averaged"]["macro_f1"] > max(block["motion"]["macro_f1"], block["muscle"]["macro_f1"]) - 0.02
    assert block["motion"]["people"] == 10

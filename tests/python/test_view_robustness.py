from __future__ import annotations

import csv
from pathlib import Path

import pytest

from ml.eval.summarize_view_robustness import build_report


FIELDS = [
    "split",
    "exercise_id",
    "camera",
    "view",
    "pose_detected",
    "mean_visibility",
    "direct_error_diagonal_fraction",
    "swapped_error_diagonal_fraction",
]


def _write_csv(path: Path, split: str, rows: list[list[str]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(FIELDS)
        writer.writerows([[split, *row] for row in rows])
    return path


def test_report_stratifies_and_computes_coverage(tmp_path: Path) -> None:
    train = _write_csv(
        tmp_path / "train.csv",
        "train",
        [
            ["1", "17", "front", "1", "0.75", "0.01", "0.10"],
            ["1", "17", "front", "1", "0.65", "0.03", "0.12"],
        ],
    )
    validation = _write_csv(
        tmp_path / "validation.csv",
        "validation",
        [["1", "18", "profile", "1", "0.85", "0.02", "0.08"]],
    )

    report = build_report(train, validation)

    assert (
        "| train | 2 | 100.0 | 70.00 | 2.00 | 3.00 | 50.0 | "
        "1.00 / 1.00 | 0.0 | \u2014 / \u2014 |"
    ) in report
    assert any(
        line.startswith("| train | 1 | 17 | front | 2 |")
        for line in report.splitlines()
    )
    assert "| validation | 1 | 18 | profile | 1 |" in report
    assert "| train | 17 | front | 2 |" in report
    assert "| validation | 18 | profile | 1 |" in report
    assert "not a visual overlay" in report
    assert "No confidence intervals" in report


def test_report_refuses_test_rows(tmp_path: Path) -> None:
    train = _write_csv(
        tmp_path / "train.csv",
        "test",
        [["1", "17", "front", "1", "0.75", "0.01", "0.10"]],
    )
    validation = _write_csv(
        tmp_path / "validation.csv",
        "validation",
        [["1", "18", "profile", "1", "0.85", "0.02", "0.08"]],
    )

    with pytest.raises(ValueError, match="test data is not accepted"):
        build_report(train, validation)

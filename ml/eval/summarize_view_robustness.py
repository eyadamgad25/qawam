"""Summarize supplied train/validation pose exports by exercise and camera view."""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = REPO_ROOT / "data" / "processed" / "model-evaluation"
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "eval-confidence-coverage.md"
EXPECTED_SPLITS = ("train", "validation")
THRESHOLDS = (0.70, 0.80)
REQUIRED_COLUMNS = {
    "split",
    "exercise_id",
    "camera",
    "view",
    "pose_detected",
    "mean_visibility",
    "direct_error_diagonal_fraction",
    "swapped_error_diagonal_fraction",
}


def _read_rows(path: Path, expected_split: str) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"empty CSV: {path}")
        missing = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ValueError(f"{path} missing columns: {sorted(missing)}")
        rows = list(reader)

    if not rows:
        raise ValueError(f"no rows in {path}")
    for line_number, row in enumerate(rows, start=2):
        actual_split = row["split"].strip()
        if actual_split != expected_split:
            raise ValueError(
                f"{path}:{line_number} expected split {expected_split!r}, "
                f"found {actual_split!r}; test data is not accepted"
            )
        for column in ("exercise_id", "camera"):
            try:
                int(row[column])
            except ValueError as exc:
                raise ValueError(
                    f"{path}:{line_number} invalid {column}: {row[column]!r}"
                ) from exc
        detected = row["pose_detected"].strip()
        if detected not in {"0", "1"}:
            raise ValueError(
                f"{path}:{line_number} pose_detected must be 0 or 1"
            )
        for column in (
            "mean_visibility",
            "direct_error_diagonal_fraction",
            "swapped_error_diagonal_fraction",
        ):
            try:
                value = float(row[column])
            except ValueError as exc:
                raise ValueError(
                    f"{path}:{line_number} invalid {column}: {row[column]!r}"
                ) from exc
            if not math.isfinite(value) or value < 0:
                raise ValueError(
                    f"{path}:{line_number} {column} must be finite and nonnegative"
                )
        visibility = float(row["mean_visibility"])
        if visibility > 1:
            raise ValueError(
                f"{path}:{line_number} mean_visibility must be in [0, 1]"
            )
    return rows


def _percentile90(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[math.ceil(0.90 * len(ordered)) - 1]


def _fmt(value: float | None) -> str:
    return "—" if value is None else f"{value:.2f}"


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _summarize(rows: list[dict[str, str]]) -> list[str]:
    errors = [float(row["direct_error_diagonal_fraction"]) * 100 for row in rows]
    detected = [row for row in rows if row["pose_detected"] == "1"]
    visibilities = [float(row["mean_visibility"]) for row in rows]
    cells = [
        str(len(rows)),
        f"{100 * len(detected) / len(rows):.1f}",
        f"{100 * sum(visibilities) / len(rows):.2f}",
        _fmt(sum(errors) / len(errors)),
        _fmt(_percentile90(errors)),
    ]
    for threshold in THRESHOLDS:
        assessed = [
            row
            for row in detected
            if float(row["mean_visibility"]) >= threshold
        ]
        assessed_errors = [
            float(row["direct_error_diagonal_fraction"]) * 100
            for row in assessed
        ]
        cells.extend(
            [
                f"{100 * len(assessed) / len(rows):.1f}",
                _fmt(
                    sum(assessed_errors) / len(assessed_errors)
                    if assessed_errors
                    else None
                ),
                _fmt(_percentile90(assessed_errors)),
            ]
        )
    return cells


def _group_rows(
    rows: list[dict[str, str]],
) -> Iterable[tuple[str, str, str, list[dict[str, str]]]]:
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[
            (
                row["exercise_id"].strip(),
                row["camera"].strip(),
                row["view"].strip(),
            )
        ].append(row)
    for (exercise, camera, view), group in sorted(
        groups.items(),
        key=lambda item: (
            int(item[0][0]),
            int(item[0][1]),
            item[0][2],
        ),
    ):
        yield exercise, camera, view, group


def _orientation_comparison(rows: list[dict[str, str]]) -> list[str]:
    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[(row["camera"].strip(), row["view"].strip())].append(row)
    output = []
    for (camera, view), group in sorted(
        groups.items(), key=lambda item: (int(item[0][0]), item[0][1])
    ):
        direct = [
            float(row["direct_error_diagonal_fraction"]) * 100 for row in group
        ]
        swapped = [
            float(row["swapped_error_diagonal_fraction"]) * 100 for row in group
        ]
        direct_mean = sum(direct) / len(direct)
        swapped_mean = sum(swapped) / len(swapped)
        output.append(
            f"| {camera} | {view} | {len(group)} | {direct_mean:.2f} | "
            f"{_fmt(_percentile90(direct))} | {swapped_mean:.2f} | "
            f"{_fmt(_percentile90(swapped))} | "
            f"{swapped_mean / direct_mean:.2f}× |"
        )
    return output


def build_report(train_csv: Path, validation_csv: Path) -> str:
    split_rows = {
        "train": _read_rows(train_csv, "train"),
        "validation": _read_rows(validation_csv, "validation"),
    }
    lines = [
        "# REHAB24-6 confidence and view robustness (exploratory)",
        "",
        "Generated by `ml/eval/summarize_view_robustness.py` from the two "
        "supplied derived CSV exports only. This analysis reads no raw video, "
        "skeleton arrays, split manifest, or test data.",
        "",
        f"- Train input: `{_display_path(train_csv)}` "
        f"({len(split_rows['train'])} frames)",
        f"- Validation input: `{_display_path(validation_csv)}` "
        f"({len(split_rows['validation'])} frames)",
        "- Grouping: exercise × camera × recorded view orientation.",
        "- Confidence proxy: row-level `mean_visibility`; assessed coverage at "
        "each descriptive threshold requires both pose detection and visibility "
        "at or above that threshold.",
        "- Error: direct keypoint error divided by frame diagonal, shown as "
        "percent. p90 uses the nearest-rank empirical percentile.",
        "- These exploratory thresholds are not clinical cutoffs and are not "
        "implemented as app gates.",
        "",
        "## Split totals",
        "",
        "| Split | Frames | Pose detected (%) | Mean visibility | Error mean (%) | "
        "Error p90 (%) | >=0.70 coverage (%) | >=0.70 error mean / p90 (%) | "
        ">=0.80 coverage (%) | >=0.80 error mean / p90 (%) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for split, rows in split_rows.items():
        summary = _summarize(rows)
        lines.append(
            f"| {split} | {summary[0]} | {summary[1]} | {summary[2]} | "
            f"{summary[3]} | {summary[4]} | {summary[5]} | "
            f"{summary[6]} / {summary[7]} | {summary[8]} | "
            f"{summary[9]} / {summary[10]} |"
        )

    lines.extend(
        [
            "",
            "## Exercise × camera × view",
            "",
            "| Split | Exercise | Camera | View | Frames | Pose detected (%) | "
            "Mean visibility | Error mean (%) | Error p90 (%) | "
            ">=0.70 coverage (%) | Error mean / p90 (%) | "
            ">=0.80 coverage (%) | Error mean / p90 (%) |",
            "| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | "
            "---: | ---: | --- | ---: | --- |",
        ]
    )
    for split, rows in split_rows.items():
        for exercise, camera, view, group in _group_rows(rows):
            summary = _summarize(group)
            lines.append(
                f"| {split} | {exercise} | {camera} | {view} | "
                f"{summary[0]} | {summary[1]} | {summary[2]} | "
                f"{summary[3]} | {summary[4]} | {summary[5]} | "
                f"{summary[6]} / {summary[7]} | {summary[8]} | "
                f"{summary[9]} / {summary[10]} |"
            )
    lines.extend(
        [
            "",
            "## Coordinate-order diagnostic",
            "",
            "The export's `swapped_error_diagonal_fraction` is compared with "
            "`direct_error_diagonal_fraction` for the same sampled rows. "
            "This checks whether swapping the two stored coordinate components "
            "would improve agreement; it is not a visual overlay or proof of "
            "coordinate origin, rotation, frame synchronization, or joint "
            "semantics.",
            "",
            "| Split | Camera | View | Frames | Direct mean (%) | Direct p90 (%) | "
            "Swapped mean (%) | Swapped p90 (%) | Swapped/direct mean |",
            "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for split, rows in split_rows.items():
        for line in _orientation_comparison(rows):
            cells = line[2:-2].split(" | ")
            lines.append("| " + split + " | " + " | ".join(cells) + " |")
    lines.extend(
        [
            "",
            "## Interpretation limits",
            "",
            "- Train is used for discovery; validation is a single descriptive "
            "check on the supplied sample and must not be treated as an "
            "independent external replication.",
            "- Rows are sampled frames, not independent participants or "
            "repetitions. No confidence intervals or clinical significance "
            "are claimed.",
            "- All reported error values describe 2D landmark localization, "
            "not exercise correctness, repetition-count accuracy, or treatment "
            "outcomes.",
            "- The supplied CSVs contain no test rows. The program rejects any "
            "row whose split label differs from its expected input split.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Summarize supplied train/validation view-robustness CSVs."
    )
    parser.add_argument(
        "--train",
        type=Path,
        default=DEFAULT_INPUT_DIR / "train_view_robustness.csv",
    )
    parser.add_argument(
        "--validation",
        type=Path,
        default=DEFAULT_INPUT_DIR / "validation_view_robustness.csv",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    report = build_report(args.train, args.validation)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

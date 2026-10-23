"""REHAB24-6 repetition index (CSV + path layout). No pose / MediaPipe."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Mapping

from qawam_ml.filters import apply_filter

SplitName = Literal["train", "validation", "test"]

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET_ROOT = REPO_ROOT / "data" / "raw" / "rehab24-6"
DEFAULT_SPLITS_PATH = Path(__file__).resolve().parents[1] / "splits.json"
DEFAULT_TEST_ACCESS_LOG = REPO_ROOT / "logs" / "test_access.jsonl"

# From data/raw/rehab24-6/joints_names.txt (index: name). Do not remap here.
JOINT_NAMES: tuple[str, ...] = (
    "Hips",
    "Spine",
    "Spine1",
    "Neck",
    "Head",
    "Head_end",
    "LeftShoulder",
    "LeftArm",
    "LeftForeArm",
    "LeftHand",
    "LeftHand_end",
    "RightShoulder",
    "RightArm",
    "RightForeArm",
    "RightHand",
    "RightHand_end",
    "LeftUpLeg",
    "LeftLeg",
    "LeftFoot",
    "LeftToeBase",
    "LeftToeBase_end",
    "RightUpLeg",
    "RightLeg",
    "RightFoot",
    "RightToeBase",
    "RightToeBase_end",
)

CSV_COLUMNS: tuple[str, ...] = (
    "video_id",
    "repetition_number",
    "exercise_id",
    "person_id",
    "first_frame",
    "last_frame",
    "cam17_orientation",
    "mocap_erroneous",
    "exercise_subtype",
    "lights_on",
    "extra_person_in_cam17",
    "extra_person_in_cam18",
    "correctness",
)


class SealedTestSplitError(PermissionError):
    """Raised when code asks for the test split without final=True."""


@dataclass(frozen=True)
class Repetition:
    video_id: str
    repetition_number: int
    exercise_id: int
    person_id: int
    first_frame: int
    last_frame: int
    cam17_orientation: str
    mocap_erroneous: int
    exercise_subtype: str
    lights_on: int
    extra_person_in_cam17: int
    extra_person_in_cam18: int
    correctness: int
    video_c17_30fps: Path
    video_c18_30fps_transposed: Path
    joints_c17_30fps: Path
    joints_c17_120fps: Path
    joints_c18_30fps: Path
    joints_c18_120fps: Path


def exercise_folder(exercise_id: int) -> str:
    return f"Ex{exercise_id}"


def recording_paths(dataset_root: Path, exercise_id: int, video_id: str) -> dict[str, Path]:
    folder = Path(dataset_root) / exercise_folder(exercise_id)
    return {
        "video_c17_30fps": folder / f"{video_id}-Camera17-30fps.mp4",
        "video_c18_30fps_transposed": folder
        / f"{video_id}-Camera18-30fps-transposed.mp4",
        "joints_c17_30fps": folder / f"{video_id}-c17-30fps.npy",
        "joints_c17_120fps": folder / f"{video_id}-c17-120fps.npy",
        "joints_c18_30fps": folder / f"{video_id}-c18-30fps.npy",
        "joints_c18_120fps": folder / f"{video_id}-c18-120fps.npy",
    }


def load_splits(path: Path | None = None) -> dict[str, Any]:
    splits_path = Path(path) if path is not None else DEFAULT_SPLITS_PATH
    with splits_path.open(encoding="utf-8") as handle:
        data: dict[str, Any] = json.load(handle)
    for key in ("train", "validation", "test"):
        if key not in data:
            raise ValueError(f"splits file missing {key!r}: {splits_path}")
    return data


def person_ids_for_split(splits: Mapping[str, Any], split: SplitName) -> frozenset[int]:
    return frozenset(int(pid) for pid in splits[split])


def _log_test_access(
    log_path: Path,
    *,
    n_rows: int,
    caller: str,
) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "split": "test",
        "n_rows": n_rows,
        "caller": caller,
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def _parse_int(value: str, field: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"non-integer {field}: {value!r}") from exc


def _row_to_repetition(row: Mapping[str, str], dataset_root: Path) -> Repetition:
    missing = [name for name in CSV_COLUMNS if name not in row]
    if missing:
        raise ValueError(f"Segmentation.csv missing columns: {missing}")
    video_id = row["video_id"].strip()
    exercise_id = _parse_int(row["exercise_id"], "exercise_id")
    paths = recording_paths(dataset_root, exercise_id, video_id)
    return Repetition(
        video_id=video_id,
        repetition_number=_parse_int(row["repetition_number"], "repetition_number"),
        exercise_id=exercise_id,
        person_id=_parse_int(row["person_id"], "person_id"),
        first_frame=_parse_int(row["first_frame"], "first_frame"),
        last_frame=_parse_int(row["last_frame"], "last_frame"),
        cam17_orientation=row["cam17_orientation"].strip(),
        mocap_erroneous=_parse_int(row["mocap_erroneous"], "mocap_erroneous"),
        exercise_subtype=row["exercise_subtype"].strip(),
        lights_on=_parse_int(row["lights_on"], "lights_on"),
        extra_person_in_cam17=_parse_int(
            row["extra_person_in_cam17"],
            "extra_person_in_cam17",
        ),
        extra_person_in_cam18=_parse_int(
            row["extra_person_in_cam18"],
            "extra_person_in_cam18",
        ),
        correctness=_parse_int(row["correctness"], "correctness"),
        **paths,
    )


def read_segmentation(
    dataset_root: Path,
    csv_path: Path | None = None,
) -> list[Repetition]:
    """Read Segmentation.csv with sep=';'. Does not open video/npy files."""
    path = Path(csv_path) if csv_path is not None else Path(dataset_root) / "Segmentation.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        if reader.fieldnames is None:
            raise ValueError(f"empty segmentation file: {path}")
        return [_row_to_repetition(row, Path(dataset_root)) for row in reader]


def load_repetitions(
    split: SplitName,
    *,
    dataset_root: Path | None = None,
    csv_path: Path | None = None,
    splits_path: Path | None = None,
    filter_name: str = "none",
    cam: int = 17,
    final: bool = False,
    test_access_log: Path | None = None,
    caller: str = "load_repetitions",
) -> list[Repetition]:
    """Return repetitions for one subject-wise split.

    The test split is sealed: raise unless final=True, and append a JSONL
    line for every successful test load. Log path defaults to
    ``logs/test_access.jsonl`` (timestamp, split, n_rows, caller only).
    """
    if split not in ("train", "validation", "test"):
        raise ValueError(f"unknown split {split!r}")

    root = Path(dataset_root) if dataset_root is not None else DEFAULT_DATASET_ROOT
    splits = load_splits(splits_path)
    allowed = person_ids_for_split(splits, split)

    if split == "test" and not final:
        raise SealedTestSplitError(
            "test split is sealed; pass final=True (eval CLI --final). "
            "Every allowed test access is logged."
        )

    rows = read_segmentation(root, csv_path=csv_path)
    selected = [row for row in rows if row.person_id in allowed]
    selected = apply_filter(selected, filter_name, cam)

    if split == "test":
        log_path = (
            Path(test_access_log)
            if test_access_log is not None
            else DEFAULT_TEST_ACCESS_LOG
        )
        _log_test_access(log_path, n_rows=len(selected), caller=caller)

    return selected

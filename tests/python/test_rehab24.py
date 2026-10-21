from __future__ import annotations

import json
from pathlib import Path

import pytest

from qawam_ml.rehab24 import (
    JOINT_NAMES,
    SealedTestSplitError,
    load_repetitions,
    load_splits,
    read_segmentation,
    recording_paths,
)

FIXTURE_CSV = """video_id;repetition_number;exercise_id;person_id;first_frame;last_frame;cam17_orientation;mocap_erroneous;exercise_subtype;lights_on;extra_person_in_cam17;extra_person_in_cam18;correctness
PM_A;1;1;1;10;20;front;0;right arm;1;0;0;1
PM_A;2;1;1;21;30;front;1;right arm;1;0;0;1
PM_B;1;2;2;5;15;profile;0;;1;0;0;0
PM_C;1;3;3;1;8;half-profile;0;;0;0;0;1
PM_T;1;1;7;40;50;front;0;right arm;1;0;0;1
PM_U;1;6;9;1;9;front;0;;1;2;0;1
"""

SYNTH_SPLITS = {
    "dataset": "synthetic",
    "split_unit": "person_id",
    "seed": 0,
    "train": [2, 3],
    "validation": [1],
    "test": [7, 9],
}


def _write_synth(tmp_path: Path) -> tuple[Path, Path, Path]:
    csv_path = tmp_path / "Segmentation.csv"
    csv_path.write_text(FIXTURE_CSV, encoding="utf-8")
    splits_path = tmp_path / "splits.json"
    splits_path.write_text(json.dumps(SYNTH_SPLITS), encoding="utf-8")
    log_path = tmp_path / "sealed-test-access.jsonl"
    return csv_path, splits_path, log_path


def test_joint_names_are_the_26_from_the_dataset_file() -> None:
    assert len(JOINT_NAMES) == 26
    assert JOINT_NAMES[0] == "Hips"
    assert JOINT_NAMES[7] == "LeftArm"
    assert JOINT_NAMES[17] == "LeftLeg"
    assert JOINT_NAMES[25] == "RightToeBase_end"


def test_read_segmentation_semicolon_and_paths(tmp_path: Path) -> None:
    csv_path, _, _ = _write_synth(tmp_path)
    rows = read_segmentation(tmp_path, csv_path=csv_path)
    assert len(rows) == 6
    first = rows[0]
    assert first.video_id == "PM_A"
    assert first.person_id == 1
    assert first.exercise_id == 1
    assert first.first_frame == 10
    assert first.last_frame == 20
    assert first.cam17_orientation == "front"
    assert first.exercise_subtype == "right arm"
    assert first.correctness == 1
    paths = recording_paths(tmp_path, 1, "PM_A")
    assert first.video_c17_30fps == paths["video_c17_30fps"]
    assert first.video_c17_30fps == tmp_path / "Ex1" / "PM_A-Camera17-30fps.mp4"
    assert (
        first.video_c18_30fps_transposed
        == tmp_path / "Ex1" / "PM_A-Camera18-30fps-transposed.mp4"
    )
    assert first.joints_c17_30fps == tmp_path / "Ex1" / "PM_A-c17-30fps.npy"
    empty_subtype = rows[2]
    assert empty_subtype.exercise_subtype == ""
    assert empty_subtype.video_id == "PM_B"
    assert empty_subtype.person_id == 2


def test_clean_subset_uses_the_three_stated_flags(tmp_path: Path) -> None:
    csv_path, splits_path, log_path = _write_synth(tmp_path)
    val = load_repetitions(
        "validation",
        dataset_root=tmp_path,
        csv_path=csv_path,
        splits_path=splits_path,
        test_access_log=log_path,
    )
    assert [row.repetition_number for row in val] == [1, 2]
    val_clean = load_repetitions(
        "validation",
        dataset_root=tmp_path,
        csv_path=csv_path,
        splits_path=splits_path,
        clean=True,
        test_access_log=log_path,
    )
    assert len(val_clean) == 1
    assert val_clean[0].repetition_number == 1
    train_clean = load_repetitions(
        "train",
        dataset_root=tmp_path,
        csv_path=csv_path,
        splits_path=splits_path,
        clean=True,
        test_access_log=log_path,
    )
    # person 2 lights_on=1 extra17=0 mocap=0; person 3 lights_on=0 excluded
    assert [row.person_id for row in train_clean] == [2]


def test_split_is_by_person_id_not_video_id(tmp_path: Path) -> None:
    csv_path, splits_path, log_path = _write_synth(tmp_path)
    train = load_repetitions(
        "train",
        dataset_root=tmp_path,
        csv_path=csv_path,
        splits_path=splits_path,
        test_access_log=log_path,
    )
    assert {row.person_id for row in train} == {2, 3}
    assert {row.video_id for row in train} == {"PM_B", "PM_C"}


def test_test_split_refused_without_final(tmp_path: Path) -> None:
    csv_path, splits_path, log_path = _write_synth(tmp_path)
    with pytest.raises(SealedTestSplitError, match="sealed"):
        load_repetitions(
            "test",
            dataset_root=tmp_path,
            csv_path=csv_path,
            splits_path=splits_path,
            test_access_log=log_path,
        )
    assert not log_path.exists()


def test_test_split_logs_when_final_true(tmp_path: Path) -> None:
    csv_path, splits_path, log_path = _write_synth(tmp_path)
    rows = load_repetitions(
        "test",
        dataset_root=tmp_path,
        csv_path=csv_path,
        splits_path=splits_path,
        final=True,
        test_access_log=log_path,
        caller="pytest",
    )
    assert {row.person_id for row in rows} == {7, 9}
    logged = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert len(logged) == 1
    assert logged[0]["split"] == "test"
    assert logged[0]["final"] is True
    assert logged[0]["n_rows"] == 2
    assert logged[0]["caller"] == "pytest"


def test_frozen_repo_splits_file_has_ten_subjects() -> None:
    splits = load_splits()
    train = set(splits["train"])
    validation = set(splits["validation"])
    test = set(splits["test"])
    assert len(train) == 6
    assert len(validation) == 2
    assert len(test) == 2
    assert train.isdisjoint(validation)
    assert train.isdisjoint(test)
    assert validation.isdisjoint(test)
    assert train | validation | test == set(range(1, 11))
    assert splits["test"] == [7, 9]

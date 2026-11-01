import copy
import json

import pytest

from qawam_ml.packs import (
    DEFAULT_PACKS_DIR,
    PLACEHOLDER,
    PackError,
    compute_angle,
    concrete_landmark,
    load_packs,
    resolve_pack,
    transform_angle,
    validate_pack,
)


def _squat():
    return json.loads((DEFAULT_PACKS_DIR / "lower-limb.squat.json").read_text(encoding="utf-8"))


def test_shipped_packs_are_valid():
    packs = load_packs()
    assert {
        "lower-limb.squat",
        "lower-limb.lunge",
        "lower-limb.leg-abduction",
        "upper-limb.shoulder-flexion",
    } <= set(packs)


def test_shipped_packs_are_provisional_with_placeholders():
    for pack in load_packs().values():
        assert pack["status"] == "provisional"
        assert pack["approvedBy"] is None
        assert pack["repCounter"] == {"low": PLACEHOLDER, "high": PLACEHOLDER}


def test_concrete_landmark_side_and_other():
    assert concrete_landmark("SIDE_KNEE", "left") == "LEFT_KNEE"
    assert concrete_landmark("OTHER_HIP", "left") == "RIGHT_HIP"
    assert concrete_landmark("RIGHT_ANKLE", "left") == "RIGHT_ANKLE"
    with pytest.raises(PackError):
        concrete_landmark("SIDE_TAIL", "left")


def test_resolve_squat_right_side():
    resolved = resolve_pack(_squat(), "right")
    knee = resolved.angle("knee_flexion")
    assert knee.landmarks == ("RIGHT_HIP", "RIGHT_KNEE", "RIGHT_ANKLE")
    assert resolved.primary_angle == "knee_flexion"


def test_transforms():
    assert transform_angle(180.0, "flexion") == 0.0
    assert transform_angle(90.0, "flexion") == 90.0
    assert transform_angle(120.0, "abduction") == 30.0
    assert transform_angle(None, "flexion") is None


def test_compute_knee_flexion_right_angle():
    knee = resolve_pack(_squat(), "left").angle("knee_flexion")
    points = {"LEFT_HIP": (0.0, 0.0), "LEFT_KNEE": (0.0, 1.0), "LEFT_ANKLE": (1.0, 1.0)}
    assert compute_angle(points, knee) == pytest.approx(90.0)
    assert compute_angle({"LEFT_HIP": (0.0, 0.0)}, knee) is None


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda p: p.pop("view"), "missing keys"),
        (lambda p: p.update(view="top"), "view must be"),
        (lambda p: p.update(primaryAngle="nope"), "primaryAngle"),
        (lambda p: p["repCounter"].update(low="45"), "string must be"),
        (lambda p: p["angles"][0].update(triplet=["SIDE_HIP", "SIDE_KNEE", "SIDE_HEEL"]), "requiredLandmarks"),
        (lambda p: p.update(status="approved", provenance="clinician", approvedBy="Demo Physio (not a real clinician)", approvedAt="2026-10-28"), "demo seed"),
        (lambda p: p.update(approvedBy="Dr X"), "provisional packs keep"),
    ],
)
def test_validation_rejects(mutate, message):
    pack = copy.deepcopy(_squat())
    mutate(pack)
    errors = validate_pack(pack)
    assert any(message in error for error in errors), errors


def test_approved_pack_cannot_keep_placeholders():
    pack = copy.deepcopy(_squat())
    pack.update(status="approved", provenance="clinician", approvedBy="A. Named Physio", approvedAt="2026-11-01")
    assert any("placeholders" in error for error in validate_pack(pack))
    pack["repCounter"] = {"low": 20, "high": 70}
    assert validate_pack(pack) == []


def test_literature_goals_need_citation_and_link():
    pack = copy.deepcopy(_squat())
    assert pack["literatureGoals"][0]["url"].startswith("https://")
    pack["literatureGoals"][0]["url"] = "no link"
    pack["literatureGoals"][0]["citation"] = "x"
    errors = validate_pack(pack)
    assert any("https" in e for e in errors) and any("citation" in e for e in errors)

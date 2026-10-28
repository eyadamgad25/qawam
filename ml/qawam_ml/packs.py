"""Exercise packs: load, validate and resolve a pack into concrete landmarks.

A pack is configuration, not code (see ``rules/packs/pack.schema.json``).
This module is standard library only so CI can validate packs without the
ML stack. Clinical numbers stay strings tagged
``PLACEHOLDER_NEEDS_PHYSIO_APPROVAL`` until a named physiotherapist approves.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from qawam_ml.angles import angle_degrees

PLACEHOLDER = "PLACEHOLDER_NEEDS_PHYSIO_APPROVAL"
DEMO_APPROVER = "Demo Physio (not a real clinician)"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PACKS_DIR = REPO_ROOT / "rules" / "packs"

Side = Literal["left", "right"]

# MediaPipe Pose Landmarker indices (33-landmark BlazePose topology).
MEDIAPIPE_INDEX: dict[str, int] = {
    "NOSE": 0,
    "LEFT_SHOULDER": 11,
    "RIGHT_SHOULDER": 12,
    "LEFT_ELBOW": 13,
    "RIGHT_ELBOW": 14,
    "LEFT_WRIST": 15,
    "RIGHT_WRIST": 16,
    "LEFT_HIP": 23,
    "RIGHT_HIP": 24,
    "LEFT_KNEE": 25,
    "RIGHT_KNEE": 26,
    "LEFT_ANKLE": 27,
    "RIGHT_ANKLE": 28,
    "LEFT_HEEL": 29,
    "RIGHT_HEEL": 30,
    "LEFT_FOOT_INDEX": 31,
    "RIGHT_FOOT_INDEX": 32,
}

# REHAB24-6 26-joint skeleton -> MediaPipe landmark name. In this
# OptiTrack/BVH-style naming a bone's name marks the joint where the bone
# starts (LeftArm = shoulder joint, LeftForeArm = elbow, LeftHand = wrist,
# LeftUpLeg = hip, LeftLeg = knee, LeftFoot = ankle). Accepted 2026-10-28;
# consistent with the PM_039/PM_101 overlay comparison (docs/dataset-report.md).
REHAB24_JOINT_FOR_LANDMARK: dict[str, int] = {
    "LEFT_SHOULDER": 7,
    "LEFT_ELBOW": 8,
    "LEFT_WRIST": 9,
    "RIGHT_SHOULDER": 12,
    "RIGHT_ELBOW": 13,
    "RIGHT_WRIST": 14,
    "LEFT_HIP": 16,
    "LEFT_KNEE": 17,
    "LEFT_ANKLE": 18,
    "RIGHT_HIP": 21,
    "RIGHT_KNEE": 22,
    "RIGHT_ANKLE": 23,
}

_GENERIC = re.compile(r"^(SIDE|OTHER)_([A-Z_]+)$")
_REQUIRED = (
    "packId",
    "version",
    "names",
    "bodyRegion",
    "view",
    "sides",
    "requiredLandmarks",
    "angles",
    "primaryAngle",
    "repCounter",
    "reference",
    "rules",
    "status",
    "provenance",
    "approvedBy",
    "approvedAt",
)
_ENUMS = {
    "bodyRegion": {"lower-limb", "upper-limb", "spine", "full-body"},
    "view": {"side", "front"},
    "sides": {"left", "right", "both", "patient-selected"},
    "status": {"provisional", "approved"},
    "provenance": {"default", "literature", "dataset-derived", "clinician"},
}
_TRANSFORMS = {"interior", "flexion", "abduction"}


class PackError(ValueError):
    """Raised when a pack fails validation."""


@dataclass(frozen=True)
class ResolvedAngle:
    name: str
    landmarks: tuple[str, str, str]
    transform: str


@dataclass(frozen=True)
class ResolvedPack:
    """A pack with SIDE/OTHER replaced by concrete landmark names."""

    pack_id: str
    version: int
    view: str
    side: Side
    required_landmarks: tuple[str, ...]
    angles: tuple[ResolvedAngle, ...]
    primary_angle: str

    def angle(self, name: str) -> ResolvedAngle:
        for item in self.angles:
            if item.name == name:
                return item
        raise KeyError(name)


def concrete_landmark(token: str, side: Side) -> str:
    """Turn SIDE_KNEE / OTHER_KNEE / LEFT_KNEE into a concrete landmark name."""
    match = _GENERIC.match(token)
    if match is None:
        name = token
    else:
        kind, joint = match.groups()
        other: Side = "right" if side == "left" else "left"
        chosen = side if kind == "SIDE" else other
        name = f"{chosen.upper()}_{joint}"
    if name not in MEDIAPIPE_INDEX:
        raise PackError(f"unknown landmark {token!r} (resolved to {name!r})")
    return name


def validate_pack(pack: Mapping[str, Any]) -> list[str]:
    """Return a list of problems; an empty list means the pack is valid."""
    errors: list[str] = []
    missing = [key for key in _REQUIRED if key not in pack]
    if missing:
        return [f"missing keys: {missing}"]

    if not isinstance(pack["packId"], str) or not re.fullmatch(
        r"[a-z0-9]+(?:-[a-z0-9]+)*\.[a-z0-9]+(?:-[a-z0-9]+)*", pack["packId"]
    ):
        errors.append("packId must look like 'lower-limb.squat'")
    if not isinstance(pack["version"], int) or isinstance(pack["version"], bool) or pack["version"] < 1:
        errors.append("version must be an integer >= 1")
    names = pack["names"]
    if not isinstance(names, Mapping) or not names.get("ar") or not names.get("en"):
        errors.append("names needs non-empty 'ar' and 'en'")
    for key, allowed in _ENUMS.items():
        if pack[key] not in allowed:
            errors.append(f"{key} must be one of {sorted(allowed)}")

    required = pack["requiredLandmarks"]
    if not isinstance(required, list) or len(required) < 3 or len(set(required)) != len(required):
        errors.append("requiredLandmarks must be a list of 3+ unique names")
        required = []
    for token in required:
        try:
            concrete_landmark(token, "left")
        except PackError as exc:
            errors.append(str(exc))

    angle_names: list[str] = []
    angles = pack["angles"]
    if not isinstance(angles, list) or not angles:
        errors.append("angles must be a non-empty list")
        angles = []
    for index, angle in enumerate(angles):
        if not isinstance(angle, Mapping):
            errors.append(f"angles[{index}] must be an object")
            continue
        name = angle.get("name")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", name):
            errors.append(f"angles[{index}].name must be snake_case")
        else:
            angle_names.append(name)
        triplet = angle.get("triplet")
        if not isinstance(triplet, list) or len(triplet) != 3:
            errors.append(f"angles[{index}].triplet must have 3 landmarks")
        else:
            for token in triplet:
                if token not in required:
                    errors.append(f"angles[{index}] uses {token!r}, which is not in requiredLandmarks")
        if angle.get("transform") not in _TRANSFORMS:
            errors.append(f"angles[{index}].transform must be one of {sorted(_TRANSFORMS)}")
    if len(set(angle_names)) != len(angle_names):
        errors.append("angle names must be unique")
    if pack["primaryAngle"] not in angle_names:
        errors.append("primaryAngle must name one of the angles")

    counter = pack["repCounter"]
    if not isinstance(counter, Mapping) or set(counter) != {"low", "high"}:
        errors.append("repCounter needs exactly 'low' and 'high'")
    else:
        for key in ("low", "high"):
            value = counter[key]
            if isinstance(value, str) and value != PLACEHOLDER:
                errors.append(f"repCounter.{key} string must be {PLACEHOLDER!r}")
            elif not isinstance(value, (str, int, float)) or isinstance(value, bool):
                errors.append(f"repCounter.{key} must be a number or the placeholder")

    if not isinstance(pack["rules"], list) or not all(isinstance(r, str) for r in pack["rules"]):
        errors.append("rules must be a list of rule IDs")

    errors.extend(_literature_errors(pack.get("literatureGoals", [])))
    errors.extend(_approval_errors(pack))
    return errors


def _literature_errors(goals: Any) -> list[str]:
    """Published values must carry a citation and an https link; they are context, not rules."""
    if not isinstance(goals, list):
        return ["literatureGoals must be a list"]
    errors: list[str] = []
    for index, goal in enumerate(goals):
        if not isinstance(goal, Mapping):
            errors.append(f"literatureGoals[{index}] must be an object")
            continue
        for key in ("metric", "value", "unit", "use", "citation", "url"):
            if key not in goal:
                errors.append(f"literatureGoals[{index}] missing {key!r}")
        if goal.get("use") not in {"display-goal", "context"}:
            errors.append(f"literatureGoals[{index}].use must be 'display-goal' or 'context'")
        if len(str(goal.get("citation", ""))) < 10:
            errors.append(f"literatureGoals[{index}] needs a full citation")
        if not str(goal.get("url", "")).startswith("https://"):
            errors.append(f"literatureGoals[{index}].url must be an https link")
    return errors


def _approval_errors(pack: Mapping[str, Any]) -> list[str]:
    status, provenance = pack["status"], pack["provenance"]
    approved_by, approved_at = pack["approvedBy"], pack["approvedAt"]
    errors: list[str] = []
    if status == "approved":
        if provenance != "clinician":
            errors.append("approved packs must have provenance 'clinician'")
        if not isinstance(approved_by, str) or not approved_by.strip():
            errors.append("approved packs need a named human approvedBy")
        elif approved_by.strip() in {DEMO_APPROVER, "TBD"}:
            errors.append("the demo seed or TBD cannot approve a pack")
        if not approved_at:
            errors.append("approved packs need approvedAt")
        if _contains_placeholder(pack):
            errors.append("approved packs cannot contain placeholders")
    elif approved_by is not None or approved_at is not None:
        errors.append("provisional packs keep approvedBy and approvedAt null")
    return errors


def _contains_placeholder(value: Any) -> bool:
    if isinstance(value, str):
        return value == PLACEHOLDER
    if isinstance(value, Mapping):
        return any(_contains_placeholder(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_placeholder(item) for item in value)
    return False


def load_pack(path: Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        pack: dict[str, Any] = json.load(handle)
    errors = validate_pack(pack)
    if errors:
        raise PackError(f"{path}: " + "; ".join(errors))
    return pack


def load_packs(directory: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load every ``*.json`` pack except the schema, keyed by packId."""
    folder = Path(directory) if directory is not None else DEFAULT_PACKS_DIR
    packs: dict[str, dict[str, Any]] = {}
    for path in sorted(folder.glob("*.json")):
        if path.name.endswith(".schema.json"):
            continue
        pack = load_pack(path)
        if pack["packId"] in packs:
            raise PackError(f"duplicate packId {pack['packId']!r}")
        packs[pack["packId"]] = pack
    return packs


def resolve_pack(pack: Mapping[str, Any], side: Side) -> ResolvedPack:
    if side not in ("left", "right"):
        raise PackError("side must be 'left' or 'right'")
    angles = tuple(
        ResolvedAngle(
            name=item["name"],
            landmarks=tuple(concrete_landmark(t, side) for t in item["triplet"]),  # type: ignore[arg-type]
            transform=item["transform"],
        )
        for item in pack["angles"]
    )
    return ResolvedPack(
        pack_id=pack["packId"],
        version=pack["version"],
        view=pack["view"],
        side=side,
        required_landmarks=tuple(concrete_landmark(t, side) for t in pack["requiredLandmarks"]),
        angles=angles,
        primary_angle=pack["primaryAngle"],
    )


def transform_angle(interior_deg: float | None, transform: str) -> float | None:
    """Map the interior angle at the vertex to the reported clinical-style angle.

    ``flexion`` = 180 - interior (straight limb = 0). ``abduction`` =
    interior - 90 (limb perpendicular to the reference segment = 0).
    """
    if interior_deg is None:
        return None
    if transform == "interior":
        return interior_deg
    if transform == "flexion":
        return 180.0 - interior_deg
    if transform == "abduction":
        return interior_deg - 90.0
    raise PackError(f"unknown transform {transform!r}")


def compute_angle(
    points: Mapping[str, Sequence[float]],
    angle: ResolvedAngle,
) -> float | None:
    """Angle from 2D points keyed by landmark name; None if a point is missing."""
    try:
        a, b, c = (points[name] for name in angle.landmarks)
    except KeyError:
        return None
    return transform_angle(angle_degrees(a, b, c), angle.transform)

"""Configurable landmark-visibility gate; no default cutoff or joint mapping."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal


CaptureStatus = Literal["READY_FOR_ANALYSIS", "CANNOT_ASSESS"]
ReasonCode = Literal[
    "REQUIRED_LANDMARK_MISSING",
    "LOW_REQUIRED_LANDMARK_VISIBILITY",
]


@dataclass(frozen=True)
class CaptureQualityResult:
    """Visibility-gate result, not a judgment about exercise form."""

    status: CaptureStatus
    reason_codes: tuple[ReasonCode, ...]
    failed_landmarks: tuple[str, ...]


def assess_capture_quality(
    required_landmarks: Sequence[str],
    visibility_by_landmark: Mapping[str, float | None],
    min_visibility: float,
) -> CaptureQualityResult:
    """Check caller-selected required landmarks against a caller-supplied cutoff.

    Missing or ``None`` visibility produces ``CANNOT_ASSESS``. Malformed or
    out-of-range visibility is rejected as invalid input rather than silently
    treated as low confidence. An empty or duplicated requirement list is a
    configuration error.
    """
    required = _required_names(required_landmarks)
    cutoff = _visibility_value(min_visibility, "min_visibility")

    missing: list[str] = []
    low_visibility: list[str] = []
    for landmark in required:
        if landmark not in visibility_by_landmark:
            missing.append(landmark)
            continue
        raw_visibility = visibility_by_landmark[landmark]
        if raw_visibility is None:
            missing.append(landmark)
            continue
        visibility = _visibility_value(raw_visibility, landmark)
        if visibility < cutoff:
            low_visibility.append(landmark)

    reasons: list[ReasonCode] = []
    failed_landmarks: list[str] = []
    if missing:
        reasons.append("REQUIRED_LANDMARK_MISSING")
        failed_landmarks.extend(missing)
    if low_visibility:
        reasons.append("LOW_REQUIRED_LANDMARK_VISIBILITY")
        failed_landmarks.extend(low_visibility)

    return CaptureQualityResult(
        status="CANNOT_ASSESS" if reasons else "READY_FOR_ANALYSIS",
        reason_codes=tuple(reasons),
        failed_landmarks=tuple(failed_landmarks),
    )


def _required_names(names: Sequence[str]) -> tuple[str, ...]:
    if isinstance(names, (str, bytes)) or not names:
        raise ValueError("required_landmarks must be a non-empty sequence of names")
    if any(not isinstance(name, str) or not name.strip() for name in names):
        raise ValueError("required_landmarks must contain non-empty strings")
    if len(set(names)) != len(names):
        raise ValueError("required_landmarks must not contain duplicates")
    return tuple(names)


def _visibility_value(value: float, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} visibility must be a finite number from 0 to 1")
    try:
        visibility = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{name} visibility must be a finite number from 0 to 1"
        ) from exc
    if not math.isfinite(visibility) or not 0 <= visibility <= 1:
        raise ValueError(f"{name} visibility must be a finite number from 0 to 1")
    return visibility

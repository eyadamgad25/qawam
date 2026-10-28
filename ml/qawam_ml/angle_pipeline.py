"""Configurable, mapping-agnostic angle-to-repetition analysis pipeline."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from qawam_ml.angles import angle_degrees
from qawam_ml.capture_quality import assess_capture_quality
from qawam_ml.repetitions import RepCounter
from qawam_ml.smoothing import moving_average

PipelineStatus = Literal["READY_FOR_ANALYSIS", "CANNOT_ASSESS"]
PipelineReason = Literal[
    "REQUIRED_LANDMARK_MISSING",
    "LOW_REQUIRED_LANDMARK_VISIBILITY",
    "ANGLE_UNDEFINED",
]


@dataclass(frozen=True)
class AngleRepResult:
    """One frame's technical analysis status and cumulative repetition count."""

    status: PipelineStatus
    reason_codes: tuple[PipelineReason, ...]
    failed_landmarks: tuple[str, ...]
    angle_degrees: float | None
    smoothed_angle_degrees: float | None
    repetition_count: int


class AngleRepPipeline:
    """Process successive frames using only explicit caller configuration.

    This is a generic technical pipeline, not a validated exercise detector.
    All landmarks, visibility cutoff, smoothing window, and repetition bounds
    are supplied by the caller. A failed/undefined frame breaks partial
    smoothing and repetition cycles so a counted cycle cannot bridge a gap.
    """

    def __init__(
        self,
        required_landmarks: Sequence[str],
        angle_landmarks: tuple[str, str, str],
        min_visibility: float,
        smoothing_window: int,
        low_threshold: float,
        high_threshold: float,
    ) -> None:
        if not required_landmarks or len(set(required_landmarks)) != len(
            required_landmarks
        ):
            raise ValueError("required_landmarks must be non-empty and unique")
        if any(not isinstance(name, str) or not name.strip() for name in required_landmarks):
            raise ValueError("required_landmarks must contain non-empty names")
        if len(set(angle_landmarks)) != 3 or not set(angle_landmarks).issubset(
            required_landmarks
        ):
            raise ValueError("angle_landmarks must be three required landmarks")

        self._required_landmarks = tuple(required_landmarks)
        self._angle_landmarks = angle_landmarks
        self._min_visibility = min_visibility
        self._smoothing_window = smoothing_window
        moving_average([], smoothing_window)
        self._counter = RepCounter(low_threshold, high_threshold)
        self._angle_history: deque[float] = deque(maxlen=smoothing_window)

    def update(
        self,
        coordinates: Mapping[str, Sequence[float]],
        visibility_by_landmark: Mapping[str, float | None],
    ) -> AngleRepResult:
        """Analyze one frame, refusing when required observations are unusable."""
        required_visibility = {
            name: visibility_by_landmark.get(name)
            if name in coordinates and name in visibility_by_landmark
            else None
            for name in self._required_landmarks
        }
        quality = assess_capture_quality(
            self._required_landmarks, required_visibility, self._min_visibility
        )
        if quality.status == "CANNOT_ASSESS":
            self._break_partial_cycle()
            return AngleRepResult(
                status="CANNOT_ASSESS",
                reason_codes=quality.reason_codes,
                failed_landmarks=quality.failed_landmarks,
                angle_degrees=None,
                smoothed_angle_degrees=None,
                repetition_count=self._counter.count,
            )

        point_a, vertex, point_c = (
            coordinates[name] for name in self._angle_landmarks
        )
        angle = angle_degrees(point_a, vertex, point_c)
        if angle is None:
            self._break_partial_cycle()
            return AngleRepResult(
                status="CANNOT_ASSESS",
                reason_codes=("ANGLE_UNDEFINED",),
                failed_landmarks=self._angle_landmarks,
                angle_degrees=None,
                smoothed_angle_degrees=None,
                repetition_count=self._counter.count,
            )

        self._angle_history.append(angle)
        smoothed = moving_average(
            tuple(self._angle_history), self._smoothing_window
        )[-1]
        count = self._counter.update(smoothed)
        return AngleRepResult(
            status="READY_FOR_ANALYSIS",
            reason_codes=(),
            failed_landmarks=(),
            angle_degrees=angle,
            smoothed_angle_degrees=smoothed,
            repetition_count=count,
        )

    def reset(self) -> None:
        """Clear all smoothing history and repetition count."""
        self._angle_history.clear()
        self._counter.reset()

    def _break_partial_cycle(self) -> None:
        self._angle_history.clear()
        self._counter.reset_cycle()

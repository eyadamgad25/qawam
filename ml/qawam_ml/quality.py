"""Per-repetition measurement-quality features for the confidence gate.

Everything here is computed from the phone's own pose output (MediaPipe
landmarks), never from ground truth, so the same features can run on the
device. Each feature targets a known way a 2D joint angle goes wrong:

  vis_mean, vis_p10   the model's own landmark visibility (the old gate)
  detect_rate         frames where a pose was found at all
  frontalness         shoulder width / torso length: ~0 in profile, high
                      when facing the camera; the right view depends on the
                      exercise, so the gate model learns it per pack family
  out_of_plane        |depth difference| / 2D length of the two limb
                      segments: a segment pointing at the camera makes the
                      in-plane angle meaningless
  jitter_deg          median |second difference| of the angle curve:
                      landmarks that jump between frames
  bone_cv             variation of the 2D segment lengths across the rep;
                      real bones do not change length
  lr_length_ratio     |log(left / right)| 2D thigh + shank length: one leg
                      foreshortened or mis-tracked
  rom_deg             measured range of motion; a movement out of the
                      image plane shows up as a tiny range

Landmark arrays are N x 33 x 5 (x px, y px, z px, visibility, presence),
with NaN rows where no pose was detected; see ml/eval/angle_eval.py.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from .packs import MEDIAPIPE_INDEX, ResolvedPack

FEATURES: tuple[str, ...] = (
    "vis_mean",
    "vis_p10",
    "detect_rate",
    "frontalness",
    "out_of_plane",
    "jitter_deg",
    "bone_cv",
    "lr_length_ratio",
    "rom_deg",
)

_I = MEDIAPIPE_INDEX


def _angle_deg(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray:
    """Interior angle at b in degrees for N x 2 arrays (NaN where degenerate)."""
    u, v = a - b, c - b
    nu, nv = np.linalg.norm(u, axis=1), np.linalg.norm(v, axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        cos = np.einsum("ij,ij->i", u, v) / (nu * nv)
    return np.degrees(np.arccos(np.clip(cos, -1.0, 1.0)))


def _length(marks: np.ndarray, a: str, b: str) -> np.ndarray:
    return np.linalg.norm(marks[:, _I[a], :2] - marks[:, _I[b], :2], axis=1)


def _nanmedian(values: np.ndarray, default: float = 0.0) -> float:
    values = values[np.isfinite(values)]
    return float(np.median(values)) if values.size else default


def rep_features(marks: np.ndarray, pack: ResolvedPack) -> dict[str, float]:
    """Quality features for one repetition seen by one camera, for one side.

    ``marks`` holds only the frames of the repetition. The pack's primary
    angle picks the three landmarks the measurement depends on.
    """
    if marks.ndim != 3 or marks.shape[1] < 33 or marks.shape[2] < 4:
        raise ValueError("marks must be N x 33 x (>=4)")
    n = marks.shape[0]
    detected = np.isfinite(marks[:, 0, 0])
    out = dict.fromkeys(FEATURES, 0.0)
    out["detect_rate"] = float(detected.mean()) if n else 0.0
    if detected.sum() < 3:
        return out
    m = marks[detected]
    angle = next(a for a in pack.angles if a.name == pack.primary_angle)
    a, b, c = (_I[name] for name in angle.landmarks)

    vis = m[:, [a, b, c], 3].min(axis=1)
    out["vis_mean"] = float(vis.mean())
    out["vis_p10"] = float(np.percentile(vis, 10))

    mid_sh = (m[:, _I["LEFT_SHOULDER"], :2] + m[:, _I["RIGHT_SHOULDER"], :2]) / 2
    mid_hip = (m[:, _I["LEFT_HIP"], :2] + m[:, _I["RIGHT_HIP"], :2]) / 2
    torso = np.linalg.norm(mid_sh - mid_hip, axis=1)
    torso = np.where(torso > 1e-6, torso, np.nan)
    shoulder_w = np.abs(m[:, _I["LEFT_SHOULDER"], 0] - m[:, _I["RIGHT_SHOULDER"], 0])
    out["frontalness"] = _nanmedian(shoulder_w / torso)

    ratios = []
    for p, q in ((a, b), (b, c)):
        length = np.linalg.norm(m[:, p, :2] - m[:, q, :2], axis=1)
        depth = np.abs(m[:, p, 2] - m[:, q, 2])
        with np.errstate(invalid="ignore", divide="ignore"):
            ratios.append(depth / np.where(length > 1e-6, length, np.nan))
    out["out_of_plane"] = _nanmedian(np.nanmax(np.vstack(ratios), axis=0))

    curve = _angle_deg(m[:, a, :2], m[:, b, :2], m[:, c, :2])
    if curve.size >= 3:
        out["jitter_deg"] = _nanmedian(np.abs(np.diff(curve, n=2)))
    finite = curve[np.isfinite(curve)]
    out["rom_deg"] = float(finite.max() - finite.min()) if finite.size else 0.0

    cvs = []
    for p, q in ((a, b), (b, c)):
        length = np.linalg.norm(m[:, p, :2] - m[:, q, :2], axis=1)
        mean = np.nanmean(length)
        cvs.append(float(np.nanstd(length) / mean) if mean > 1e-6 else 0.0)
    out["bone_cv"] = max(cvs)

    left = _length(m, "LEFT_HIP", "LEFT_KNEE") + _length(m, "LEFT_KNEE", "LEFT_ANKLE")
    right = _length(m, "RIGHT_HIP", "RIGHT_KNEE") + _length(m, "RIGHT_KNEE", "RIGHT_ANKLE")
    with np.errstate(invalid="ignore", divide="ignore"):
        out["lr_length_ratio"] = _nanmedian(np.abs(np.log(left / right)))
    return {k: (v if np.isfinite(v) else 0.0) for k, v in out.items()}


def segment(frames: np.ndarray, marks: np.ndarray, first: int, last: int) -> np.ndarray:
    """Rows of ``marks`` whose frame index lies in [first, last]."""
    keep = (frames >= first) & (frames <= last)
    return marks[keep]


# ------------------------------------------------------------- gate model


class LogisticGate:
    """L2-regularised logistic regression on standardised features.

    Predicts P(measurement is trustworthy). Tiny and dependency-free so the
    fitted coefficients can be exported to JSON and run on the phone.
    """

    def __init__(self, features: Sequence[str] = FEATURES, l2: float = 1.0, iterations: int = 500):
        self.features = tuple(features)
        self.l2 = l2
        self.iterations = iterations
        self.mean = np.zeros(len(self.features))
        self.scale = np.ones(len(self.features))
        self.coef = np.zeros(len(self.features))
        self.intercept = 0.0

    def _matrix(self, rows: Sequence[dict[str, float]]) -> np.ndarray:
        return np.asarray([[float(r[f]) for f in self.features] for r in rows], dtype=float)

    def fit(self, rows: Sequence[dict[str, float]], correct: Sequence[int]) -> "LogisticGate":
        x = self._matrix(rows)
        y = np.asarray(correct, dtype=float)
        self.mean = x.mean(axis=0)
        self.scale = np.where(x.std(axis=0) > 1e-9, x.std(axis=0), 1.0)
        z = (x - self.mean) / self.scale
        w = np.zeros(z.shape[1])
        b = 0.0
        n = len(y)
        # Newton's method: the problem is small and convex.
        for _ in range(self.iterations):
            p = 1 / (1 + np.exp(-(z @ w + b)))
            g_w = z.T @ (p - y) / n + self.l2 * w / n
            g_b = float(np.mean(p - y))
            s = p * (1 - p)
            h = np.zeros((len(w) + 1, len(w) + 1))
            h[:-1, :-1] = (z.T * s) @ z / n + self.l2 * np.eye(len(w)) / n
            h[:-1, -1] = h[-1, :-1] = z.T @ s / n
            h[-1, -1] = s.mean() + 1e-9
            step = np.linalg.solve(h, np.append(g_w, g_b))
            w -= step[:-1]
            b -= step[-1]
            if np.abs(step).max() < 1e-8:
                break
        self.coef, self.intercept = w, b
        return self

    def predict(self, rows: Sequence[dict[str, float]]) -> np.ndarray:
        z = (self._matrix(rows) - self.mean) / self.scale
        return 1 / (1 + np.exp(-(z @ self.coef + self.intercept)))

    def to_json(self) -> dict[str, object]:
        return {
            "type": "logistic",
            "features": list(self.features),
            "mean": [round(float(v), 6) for v in self.mean],
            "scale": [round(float(v), 6) for v in self.scale],
            "coef": [round(float(v), 6) for v in self.coef],
            "intercept": round(float(self.intercept), 6),
        }

"""Selective feedback: when may the coach speak?

Each assessed unit (a repetition, not a frame: frames inside one rep are not
exchangeable) has a ``confidence`` (higher = more trustworthy, e.g. mean
landmark visibility) and a ``wrong`` flag (1 if a cue based on it would be
wrong, e.g. measured angle error above a tolerance). Accepting units with
confidence >= t gives a coverage (share assessed) and a selective risk
(share of accepted units that are wrong, the false-cue rate).

``calibrate_threshold`` picks the most permissive t whose selective risk is
certified <= alpha with probability >= 1 - delta, using an exact binomial
test per candidate and a Bonferroni correction over the candidate grid
(a Learn-then-Test procedure). ``procedure="fixed_sequence"`` instead tests
candidates from strictest to most permissive at level delta each and stops at
the first one it cannot certify; this also controls the error at delta and is
far more powerful on small calibration sets, because selective risk usually
grows as the threshold loosens. The guarantee holds for new units that are
exchangeable with the calibration units, i.e. calibrate on held-out subjects
and re-check when the setting changes (lab -> home).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class RiskCoveragePoint:
    threshold: float
    accepted: int
    wrong: int
    coverage: float
    risk: float


@dataclass(frozen=True)
class CalibrationResult:
    threshold: float | None
    alpha: float
    delta: float
    candidates: int
    accepted: int
    wrong: int
    coverage: float
    empirical_risk: float
    p_value: float | None

    @property
    def abstain_always(self) -> bool:
        return self.threshold is None


def _arrays(confidence: Sequence[float], wrong: Sequence[int]) -> tuple[np.ndarray, np.ndarray]:
    conf = np.asarray(confidence, dtype=float)
    err = np.asarray(wrong, dtype=int)
    if conf.shape != err.shape or conf.ndim != 1 or conf.size == 0:
        raise ValueError("confidence and wrong must be equal-length non-empty 1-D sequences")
    if not np.all(np.isfinite(conf)):
        raise ValueError("confidence must be finite")
    if not np.all((err == 0) | (err == 1)):
        raise ValueError("wrong must contain only 0 and 1")
    return conf, err


def risk_coverage_curve(confidence: Sequence[float], wrong: Sequence[int]) -> list[RiskCoveragePoint]:
    """One point per distinct confidence value, strictest threshold first."""
    conf, err = _arrays(confidence, wrong)
    total = conf.size
    points: list[RiskCoveragePoint] = []
    for t in np.unique(conf)[::-1]:
        mask = conf >= t
        n = int(mask.sum())
        k = int(err[mask].sum())
        points.append(RiskCoveragePoint(float(t), n, k, n / total, k / n))
    return points


def binomial_cdf(k: int, n: int, p: float) -> float:
    """P(X <= k) for X ~ Binomial(n, p), computed in log space."""
    if n < 0 or k < 0:
        raise ValueError("n and k must be non-negative")
    if not 0.0 <= p <= 1.0:
        raise ValueError("p must be in [0, 1]")
    if k >= n:
        return 1.0
    if p == 0.0:
        return 1.0
    if p == 1.0:
        return 0.0
    log_p, log_q = math.log(p), math.log1p(-p)
    log_terms = [
        math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * log_p + (n - i) * log_q
        for i in range(k + 1)
    ]
    peak = max(log_terms)
    return min(1.0, math.exp(peak) * sum(math.exp(t - peak) for t in log_terms))


def calibrate_threshold(
    confidence: Sequence[float],
    wrong: Sequence[int],
    alpha: float,
    delta: float = 0.1,
    grid: int = 50,
    min_accepted: int = 10,
    procedure: str = "bonferroni",
) -> CalibrationResult:
    """Most permissive threshold whose false-cue rate is certified <= alpha.

    Candidates are confidence quantiles (``grid`` of them). For each, the null
    hypothesis "selective risk > alpha" is rejected when
    P(Binomial(n, alpha) <= k) <= delta / candidates. If no candidate passes,
    the coach must always abstain (threshold None).
    """
    if not 0 < alpha < 1 or not 0 < delta < 1:
        raise ValueError("alpha and delta must be in (0, 1)")
    if procedure not in ("bonferroni", "fixed_sequence"):
        raise ValueError("procedure must be 'bonferroni' or 'fixed_sequence'")
    conf, err = _arrays(confidence, wrong)
    levels = np.unique(np.quantile(conf, np.linspace(0.0, 1.0, grid)))
    if procedure == "fixed_sequence":
        return _fixed_sequence(conf, err, levels, alpha, delta, min_accepted)
    level = delta / len(levels)
    best: CalibrationResult | None = None
    for t in levels:
        mask = conf >= t
        n = int(mask.sum())
        if n < min_accepted:
            continue
        k = int(err[mask].sum())
        p_value = binomial_cdf(k, n, alpha)
        if p_value <= level and (best is None or n > best.accepted):
            best = CalibrationResult(float(t), alpha, delta, len(levels), n, k, n / conf.size, k / n, p_value)
    if best is None:
        return CalibrationResult(None, alpha, delta, len(levels), 0, 0, 0.0, math.nan, None)
    return best


def _fixed_sequence(conf: np.ndarray, err: np.ndarray, levels: np.ndarray, alpha: float, delta: float, min_accepted: int) -> CalibrationResult:
    # A test can only reject once n is large enough that zero errors would be
    # significant: (1 - alpha)^n <= delta. Starting the sequence there depends
    # only on n (fixed by the quantile grid), not on the error labels.
    start_n = max(min_accepted, math.ceil(math.log(delta) / math.log1p(-alpha)))
    best: CalibrationResult | None = None
    for t in levels[::-1]:
        mask = conf >= t
        n = int(mask.sum())
        if n < start_n:
            continue
        k = int(err[mask].sum())
        p_value = binomial_cdf(k, n, alpha)
        if p_value > delta:
            break
        best = CalibrationResult(float(t), alpha, delta, len(levels), n, k, n / conf.size, k / n, p_value)
    if best is None:
        return CalibrationResult(None, alpha, delta, len(levels), 0, 0, 0.0, math.nan, None)
    return best


def clopper_pearson_upper(k: int, n: int, confidence: float = 0.95) -> float:
    """One-sided exact upper bound on a rate after k events in n trials."""
    if n <= 0:
        return 1.0
    if k >= n:
        return 1.0
    lo, hi = k / n, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if binomial_cdf(k, n, mid) > 1 - confidence:
            lo = mid
        else:
            hi = mid
    return hi


def apply_threshold(
    confidence: Sequence[float],
    wrong: Sequence[int],
    threshold: float | None,
) -> RiskCoveragePoint:
    """Coverage and false-cue rate of a fixed threshold on new data."""
    conf, err = _arrays(confidence, wrong)
    if threshold is None:
        return RiskCoveragePoint(math.inf, 0, 0, 0.0, math.nan)
    mask = conf >= threshold
    n = int(mask.sum())
    k = int(err[mask].sum())
    return RiskCoveragePoint(threshold, n, k, n / conf.size, k / n if n else math.nan)

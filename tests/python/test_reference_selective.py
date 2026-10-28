import math

import numpy as np
import pytest

from qawam_ml.reference import compare_to_reference, dtw_path, symmetry_index
from qawam_ml.selective import (
    apply_threshold,
    binomial_cdf,
    calibrate_threshold,
    risk_coverage_curve,
)


def _rep(peak: float, n: int) -> list[float]:
    t = np.linspace(0, np.pi, n)
    return list(peak * np.sin(t))


def test_dtw_identical_curves_cost_zero():
    curve = _rep(90, 40)
    total, path = dtw_path(curve, curve)
    assert total == pytest.approx(0.0)
    assert path[0] == (0, 0) and path[-1] == (39, 39)


def test_slower_rep_matches_shape():
    result = compare_to_reference(_rep(90, 80), _rep(90, 40))
    assert result.tempo_ratio == pytest.approx(2.0)
    assert result.rom_ratio == pytest.approx(1.0, abs=0.01)
    assert result.dtw_mean_abs_deg < 3.0


def test_shallow_rep_shows_in_rom_and_peak():
    result = compare_to_reference(_rep(60, 40), _rep(90, 40))
    assert result.rom_ratio == pytest.approx(60 / 90, abs=0.01)
    assert result.peak_difference_deg == pytest.approx(-30, abs=0.5)


def test_reference_rejects_gaps():
    with pytest.raises(ValueError):
        compare_to_reference([0.0, math.nan, 10.0], _rep(90, 10))


def test_symmetry_index():
    assert symmetry_index(80, 100) == pytest.approx(80.0)
    with pytest.raises(ValueError):
        symmetry_index(80, 0)


def test_binomial_cdf_matches_known_values():
    assert binomial_cdf(0, 10, 0.5) == pytest.approx(1 / 1024)
    assert binomial_cdf(5, 10, 0.5) == pytest.approx(638 / 1024)
    assert binomial_cdf(10, 10, 0.3) == 1.0


def test_risk_coverage_curve_is_monotone_in_coverage():
    conf = [0.9, 0.8, 0.7, 0.6]
    wrong = [0, 0, 1, 1]
    points = risk_coverage_curve(conf, wrong)
    assert [p.coverage for p in points] == [0.25, 0.5, 0.75, 1.0]
    assert [p.risk for p in points] == [0.0, 0.0, pytest.approx(1 / 3), 0.5]


def test_calibration_finds_safe_threshold_on_separable_data():
    rng = np.random.default_rng(0)
    good = rng.uniform(0.7, 1.0, 400)
    bad = rng.uniform(0.0, 0.5, 200)
    conf = np.concatenate([good, bad])
    wrong = np.concatenate([np.zeros(400, int), np.ones(200, int)])
    result = calibrate_threshold(conf, wrong, alpha=0.1, delta=0.1)
    assert not result.abstain_always
    assert result.empirical_risk <= 0.1
    assert result.coverage > 0.6


def test_calibration_abstains_when_confidence_is_useless():
    rng = np.random.default_rng(1)
    conf = rng.uniform(0, 1, 300)
    wrong = rng.integers(0, 2, 300)
    assert calibrate_threshold(conf, wrong, alpha=0.05, delta=0.1).abstain_always


def test_calibration_guarantee_holds_on_fresh_data():
    rng = np.random.default_rng(2)

    def draw(n):
        conf = rng.uniform(0, 1, n)
        wrong = (rng.uniform(0, 1, n) < 0.6 * (1 - conf) ** 2).astype(int)
        return conf, wrong

    alpha, violations, trials = 0.1, 0, 200
    for _ in range(trials):
        result = calibrate_threshold(*draw(500), alpha=alpha, delta=0.1)
        if result.abstain_always:
            continue
        test = apply_threshold(*draw(20000), result.threshold)
        violations += int(test.risk > alpha)
    assert violations / trials <= 0.1


def test_apply_threshold_none_means_abstain():
    point = apply_threshold([0.5, 0.9], [0, 0], None)
    assert point.accepted == 0 and point.coverage == 0.0


def test_fixed_sequence_certifies_where_bonferroni_cannot():
    # 70 calibration reps: the 30 most confident hold 1 error, the rest are mostly wrong.
    conf = np.linspace(1.0, 0.0, 70)
    wrong = np.array([0] * 29 + [1] + [1, 0] * 20)
    bonf = calibrate_threshold(conf, wrong, alpha=0.1, delta=0.1)
    fixed = calibrate_threshold(conf, wrong, alpha=0.1, delta=0.1, procedure="fixed_sequence")
    assert bonf.abstain_always
    assert not fixed.abstain_always
    assert fixed.empirical_risk <= 0.1
    with pytest.raises(ValueError):
        calibrate_threshold(conf, wrong, alpha=0.1, procedure="other")


def test_fixed_sequence_keeps_its_guarantee_in_simulation():
    rng = np.random.default_rng(7)
    failures = 0
    trials = 300
    for _ in range(trials):
        conf = rng.random(400)
        wrong = (rng.random(400) < 0.4 * (1 - conf)).astype(int)
        result = calibrate_threshold(conf, wrong, alpha=0.1, delta=0.1, procedure="fixed_sequence")
        if result.threshold is not None:
            true_risk = 0.4 * (1 - (1 + result.threshold) / 2)  # E[wrong | conf >= t]
            failures += true_risk > 0.1
    assert failures / trials <= 0.1 + 0.05


def test_clopper_pearson_upper_matches_known_values():
    from qawam_ml.selective import clopper_pearson_upper

    assert clopper_pearson_upper(0, 29) == pytest.approx(1 - 0.05 ** (1 / 29), abs=1e-6)
    assert 0.08 < clopper_pearson_upper(3, 88) < 0.09
    assert clopper_pearson_upper(5, 5) == 1.0

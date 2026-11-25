"""A small trained model on KERAAL: does this recording need the physio's attention, or "not sure"?

Labels: a recording needs attention if the clinician did not call it Correct. Training uses
only recordings both clinicians agree on. Error types cannot be trained on groups 1A + 2A:
where clinicians agree, each exercise has about one error type, partly tied to one patient.

Split: leave one patient out (6 patients); healthy people only ever train. Five seeds per
fold, probabilities averaged. Settings below were fixed before the first run and are not
tuned on these patients.

Scores are within each exercise, then averaged. Pooled scores would look better than they
are, because the share of errors differs by exercise (flank stretch 81%, torso rotation 30%).

Baselines to beat: the majority answer per exercise, a linear model on summary numbers
(mean, spread, range of each channel), and DTW to healthy recordings (keraal_eval.py).

Abstention: answer only when confidence >= t, with t chosen on the other patients'
out-of-fold predictions so that the exact 95% upper bound on wrong answers is <= 0.10.
That is cross-fitting, not a sealed test: those predictions came from models that saw the
held-out patient during training, so treat the result as optimistic.

Needs PyTorch (tested with 2.12.0, CPU), which CI does not install.

  py -3.14 ml\\eval\\keraal_model.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

EVAL_DIR = Path(__file__).resolve().parent
ML_ROOT = EVAL_DIR.parent
for path in (str(ML_ROOT), str(EVAL_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

from gate_eval import auroc  # noqa: E402
from keraal_eval import DEFAULT_ROOT, angle_features, both_correct, dtw, load  # noqa: E402
from qawam_ml.rehab24 import REPO_ROOT  # noqa: E402
from qawam_ml.selective import clopper_pearson_upper  # noqa: E402

DEFAULT_OUT = REPO_ROOT / "data" / "derived" / "keraal-model"
EXERCISES = ("CTK", "ELK", "RTK")
FRAMES = 64
SEEDS = 5
EPOCHS = 150
BATCH = 16
LR, WEIGHT_DECAY, DROPOUT, NOISE = 1e-3, 1e-3, 0.3, 0.02
TARGET_RISK = 0.10


def to_input(positions: np.ndarray) -> np.ndarray:
    """(FRAMES, 23): normalised joints plus the app's angles, resampled to a fixed length."""
    x = np.concatenate([positions, angle_features(positions)], axis=1)
    grid = np.linspace(0, len(x) - 1, FRAMES)
    return np.stack([np.interp(grid, np.arange(len(x)), x[:, c]) for c in range(x.shape[1])], axis=1)


def agreed_label(r: Mapping[str, Any]) -> int | None:
    a, b = r["verdict_A"] != "Correct", r["verdict_B"] != "Correct"
    return int(a) if a == b else None


def exercise_one_hot(exercises: Sequence[str]) -> np.ndarray:
    return np.array([[float(e == x) for x in EXERCISES] for e in exercises], dtype=np.float32)


def balanced_weights(y: np.ndarray, exercises: Sequence[str]) -> np.ndarray:
    """Each class counts equally within each exercise, so the prior per exercise is not the easy answer."""
    w = np.zeros(len(y), dtype=np.float32)
    ex = np.asarray(exercises)
    for e in EXERCISES:
        for c in (0, 1):
            mask = (ex == e) & (y == c)
            if mask.any():
                w[mask] = ((ex == e).sum() / 2) / mask.sum()
    return w


def build_net(channels: int, outputs: int = 1):
    import torch
    from torch import nn

    class SeparableBlock(nn.Module):
        def __init__(self, c_in: int, c_out: int, kernel: int, dilation: int):
            super().__init__()
            pad = dilation * (kernel - 1) // 2
            self.net = nn.Sequential(
                nn.Conv1d(c_in, c_in, kernel, padding=pad, dilation=dilation, groups=c_in, bias=False),
                nn.Conv1d(c_in, c_out, 1, bias=False),
                nn.BatchNorm1d(c_out),
                nn.ReLU(),
                nn.Dropout(DROPOUT),
            )

        def forward(self, x):
            return self.net(x)

    class Net(nn.Module):
        """LITE-style: depthwise separable convolutions, so it stays small enough for a phone."""

        def __init__(self):
            super().__init__()
            self.body = nn.Sequential(
                SeparableBlock(channels, 32, 9, 1),
                SeparableBlock(32, 32, 9, 2),
                SeparableBlock(32, 48, 9, 4),
            )
            self.head = nn.Linear(48 + len(EXERCISES), outputs)

        def forward(self, x, ex):
            pooled = self.body(x.transpose(1, 2)).mean(dim=2)
            out = self.head(torch.cat([pooled, ex], dim=1))
            return out.squeeze(1) if outputs == 1 else out

    return Net()


def fit_predict(train: Sequence[Mapping[str, Any]], test: Sequence[Mapping[str, Any]], seed: int,
                epochs: int = EPOCHS) -> np.ndarray:
    import torch

    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    x = np.stack([r["input"] for r in train]).astype(np.float32)
    mean, std = x.mean(axis=(0, 1), keepdims=True), x.std(axis=(0, 1), keepdims=True) + 1e-6
    y = np.array([r["label"] for r in train], dtype=np.float32)
    ex = exercise_one_hot([r["exercise"] for r in train])
    weights = balanced_weights(y, [r["exercise"] for r in train])
    net = build_net(x.shape[2])
    opt = torch.optim.AdamW(net.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    x_t = torch.from_numpy((x - mean) / std)
    net.train()
    for _ in range(epochs):
        for batch in np.array_split(rng.permutation(len(x)), max(1, len(x) // BATCH)):
            idx = torch.from_numpy(batch)
            noisy = x_t[idx] + NOISE * torch.randn_like(x_t[idx])
            loss = torch.nn.functional.binary_cross_entropy_with_logits(
                net(noisy, torch.from_numpy(ex[batch])), torch.from_numpy(y[batch]),
                weight=torch.from_numpy(weights[batch]))
            opt.zero_grad()
            loss.backward()
            opt.step()
    net.eval()
    x_test = (np.stack([r["input"] for r in test]).astype(np.float32) - mean) / std
    with torch.no_grad():
        logits = net(torch.from_numpy(x_test), torch.from_numpy(exercise_one_hot([r["exercise"] for r in test])))
    return torch.sigmoid(logits).numpy()


def summary_features(x: np.ndarray) -> np.ndarray:
    return np.concatenate([x.mean(axis=0), x.std(axis=0), x.max(axis=0) - x.min(axis=0)])


def fit_predict_linear(train: Sequence[Mapping[str, Any]], test: Sequence[Mapping[str, Any]]) -> np.ndarray:
    """Weighted logistic regression on summary numbers (full-batch gradient descent, L2)."""
    a = np.stack([summary_features(r["input"]) for r in train])
    mean, std = a.mean(axis=0), a.std(axis=0) + 1e-6
    design = lambda rows, f: np.concatenate(  # noqa: E731
        [(f - mean) / std, exercise_one_hot([r["exercise"] for r in rows])], axis=1)
    a = design(train, a)
    y = np.array([r["label"] for r in train], dtype=float)
    weights = balanced_weights(y, [r["exercise"] for r in train])
    w = np.zeros(a.shape[1])
    for _ in range(3000):
        p = 1 / (1 + np.exp(-(a @ w)))
        w -= 0.1 * (a.T @ (weights * (p - y)) / len(y) + 0.1 * w)
    b = design(test, np.stack([summary_features(r["input"]) for r in test]))
    return 1 / (1 + np.exp(-(b @ w)))


def out_of_fold(rows: Sequence[dict[str, Any]], healthy: Sequence[Mapping[str, Any]], seeds: int = SEEDS,
                epochs: int = EPOCHS) -> None:
    """Adds p_model and p_linear to every patient row, always from models that never saw that patient."""
    for person in sorted({r["person"] for r in rows}):
        held = [r for r in rows if r["person"] == person]
        train = [r for r in rows if r["person"] != person and r["label"] is not None]
        train += [r for r in healthy if r["label"] is not None]
        ps = np.mean([fit_predict(train, held, seed, epochs) for seed in range(seeds)], axis=0)
        linear = fit_predict_linear(train, held)
        for r, p, q in zip(held, ps, linear):
            r["p_model"], r["p_linear"] = float(p), float(q)
        print(f"patient {person} done: {len(held)} recordings, trained on {len(train)}", flush=True)


def within_exercise_auc(rows: Sequence[Mapping[str, Any]], score: str, label: str) -> dict[str, Any]:
    per = {}
    for e in EXERCISES:
        part = [r for r in rows if r["exercise"] == e and r[label] is not None and r.get(score) is not None]
        a = auroc([r[score] for r in part], [r[label] for r in part])  # higher score = needs attention
        per[e] = None if a is None else round(a, 3)
    vals = [v for v in per.values() if v is not None]
    return {"mean": round(float(np.mean(vals)), 3) if vals else None, **per}


def auc_ci(rows: Sequence[Mapping[str, Any]], score: str, label: str, rounds: int = 2000, seed: int = 20261104) -> list[float]:
    people = sorted({r["person"] for r in rows})
    by = {p: [r for r in rows if r["person"] == p] for p in people}
    rng = np.random.default_rng(seed)
    means = []
    for _ in range(rounds):
        sample = [r for k in rng.integers(0, len(people), len(people)) for r in by[people[k]]]
        m = within_exercise_auc(sample, score, label)["mean"]
        if m is not None:
            means.append(m)
    lo, hi = np.percentile(means, [2.5, 97.5])
    return [round(float(lo), 3), round(float(hi), 3)]


def majority_wrong(rows: Sequence[Mapping[str, Any]], label: str) -> tuple[int, int]:
    """Wrong answers if we always give each exercise's most common label (an optimistic baseline)."""
    wrong, total = 0, 0
    for e in EXERCISES:
        y = [r[label] for r in rows if r["exercise"] == e and r[label] is not None]
        wrong += min(sum(y), len(y) - sum(y))
        total += len(y)
    return wrong, total


def wrong_rate(rows: Sequence[Mapping[str, Any]], key: str, label: str) -> tuple[int, int]:
    part = [r for r in rows if r[label] is not None]
    return sum((r[key] >= 0.5) != bool(r[label]) for r in part), len(part)


def risk_coverage(rows: Sequence[Mapping[str, Any]], label: str) -> list[dict[str, Any]]:
    part = sorted((r for r in rows if r[label] is not None), key=lambda r: -abs(r["p_model"] - 0.5))
    out = []
    for cov in (0.2, 0.4, 0.6, 0.8, 1.0):
        n = max(1, round(cov * len(part)))
        k = sum((r["p_model"] >= 0.5) != bool(r[label]) for r in part[:n])
        out.append({"coverage": cov, "answered": n, "wrong": k, "rate": round(k / n, 3),
                    "upper95": round(clopper_pearson_upper(k, n), 3)})
    return out


def pick_threshold(rows: Sequence[Mapping[str, Any]], label: str) -> float | None:
    """Lowest confidence whose answered set has an exact 95% upper bound on wrong answers <= target."""
    part = [(abs(r["p_model"] - 0.5), (r["p_model"] >= 0.5) != bool(r[label])) for r in rows if r[label] is not None]
    part.sort(key=lambda t: -t[0])
    best, wrong = None, 0
    for n, (conf, is_wrong) in enumerate(part, 1):
        wrong += int(is_wrong)
        if clopper_pearson_upper(wrong, n) <= TARGET_RISK:
            best = conf
    return best


def abstention(rows: Sequence[Mapping[str, Any]], label: str) -> dict[str, Any]:
    answered, wrong, per_person = 0, 0, []
    part = [r for r in rows if r[label] is not None]
    for person in sorted({r["person"] for r in part}):
        held = [r for r in part if r["person"] == person]
        t = pick_threshold([r for r in part if r["person"] != person], label)
        chosen = [] if t is None else [r for r in held if abs(r["p_model"] - 0.5) >= t]
        bad = sum((r["p_model"] >= 0.5) != bool(r[label]) for r in chosen)
        answered, wrong = answered + len(chosen), wrong + bad
        per_person.append({"person": person, "answered": len(chosen), "wrong": bad, "of": len(held)})
    return {"answered": answered, "wrong": wrong, "of": len(part),
            "upper95": None if not answered else round(clopper_pearson_upper(wrong, answered), 3),
            "per_person": per_person}


def build_report(rows: Sequence[dict[str, Any]], parameters: int | None) -> dict[str, Any]:
    n = len(rows)
    agree = sum((r["verdict_A"] == "Correct") == (r["verdict_B"] == "Correct") for r in rows)
    report: dict[str, Any] = {
        "patients": sorted({r["person"] for r in rows}),
        "recordings": n,
        "parameters": parameters,
        "clinician_agreement": round(agree / n, 3),
        "model_vs_clinician": {
            lab: round(sum((r["p_model"] >= 0.5) == bool(r[lab]) for r in rows) / n, 3) for lab in ("label_A", "label_B")},
    }
    for lab in ("label", "label_A", "label_B"):
        scored = {"model": "p_model", "linear": "p_linear", "dtw_healthy": "dtw_healthy"}
        report[lab] = {name: {**within_exercise_auc(rows, key, lab), "ci95": auc_ci(rows, key, lab)}
                       for name, key in scored.items() if any(r.get(key) is not None for r in rows)}
    report["wrong_at_full_coverage"] = {"majority_per_exercise": majority_wrong(rows, "label"),
                                        "model": wrong_rate(rows, "p_model", "label"),
                                        "linear": wrong_rate(rows, "p_linear", "label")}
    report["risk_coverage"] = risk_coverage(rows, "label")
    report["abstention_at_target"] = abstention(rows, "label")
    return report


def markdown(report: Mapping[str, Any]) -> str:
    lines = [f"KERAAL attention model: {report['recordings']} recordings, patients {report['patients']}, "
             f"{report['parameters']} parameters", "",
             f"Clinicians agree with each other: {report['clinician_agreement']}; model agrees with "
             f"A {report['model_vs_clinician']['label_A']}, B {report['model_vs_clinician']['label_B']}", ""]
    for lab, title in (("label", "Where both clinicians agree"), ("label_A", "Clinician A"), ("label_B", "Clinician B")):
        lines += [f"## {title} (AUC within exercise)", "", "| Method | Mean | 95% CI | CTK | ELK | RTK |",
                  "| --- | --- | --- | --- | --- | --- |"]
        for name, r in report[lab].items():
            lines.append(f"| {name} | {r['mean']} | {r['ci95']} | {r['CTK']} | {r['ELK']} | {r['RTK']} |")
        lines.append("")
    lines += ["Wrong at full coverage (wrong, total): " + json.dumps(report["wrong_at_full_coverage"]), "",
              "| Coverage | Answered | Wrong | Rate | 95% upper |", "| --- | --- | --- | --- | --- |"]
    lines += [f"| {r['coverage']} | {r['answered']} | {r['wrong']} | {r['rate']} | {r['upper95']} |" for r in report["risk_coverage"]]
    lines += ["", "Abstention at target: " + json.dumps(report["abstention_at_target"])]
    return "\n".join(lines) + "\n"


def prepare(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows, healthy = [], []
    for r in load(root):
        item = {**r, "input": to_input(r["x"]), "angles": angle_features(r["x"]), "label": agreed_label(r),
                "label_A": int(r["verdict_A"] != "Correct"), "label_B": int(r["verdict_B"] != "Correct")}
        (rows if r["patient"] else healthy).append(item)
    return rows, healthy


def add_dtw_baseline(rows: Sequence[dict[str, Any]], healthy: Sequence[Mapping[str, Any]]) -> None:
    for e in EXERCISES:
        refs = [h["angles"] for h in healthy if h["exercise"] == e and both_correct(h)]
        for r in (r for r in rows if r["exercise"] == e):
            r["dtw_healthy"] = float(np.median([dtw(r["angles"], ref) for ref in refs])) if refs else None


def count_parameters(channels: int = 23) -> int:
    return sum(p.numel() for p in build_net(channels).parameters())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--seeds", type=int, default=SEEDS)
    parser.add_argument("--epochs", type=int, default=EPOCHS)
    args = parser.parse_args(argv)
    rows, healthy = prepare(args.root)
    if not rows:
        print(f"no KERAAL patient recordings under {args.root}", file=sys.stderr)
        return 1
    add_dtw_baseline(rows, healthy)
    out_of_fold(rows, healthy, args.seeds, args.epochs)
    report = build_report(rows, count_parameters())
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (args.out / "summary.md").write_text(markdown(report), encoding="utf-8")
    keep = ("person", "exercise", "take", "verdict_A", "verdict_B", "label", "p_model", "p_linear", "dtw_healthy")
    (args.out / "predictions.json").write_text(json.dumps([{k: r.get(k) for k in keep} for r in rows]), encoding="utf-8")
    print(markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

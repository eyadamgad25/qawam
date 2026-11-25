"""Compare several models: train on KERAAL group 3 (simulated errors), test on real patients.

Group 3 has 3 trained people simulating errors, 45 recordings of each class per exercise, so
error types can be learned there. Each exercise gets its own model with four classes: correct,
Error1, Error2, Error3. This is scenario 1 of Marusic et al. 2025 (train group 3, test 1A + 2A).

Models: 5-nearest-neighbour DTW on the app's angles, a linear model on summary numbers, the
small CNN from keraal_model.py, and a small GRU.

Nothing about the test patients is used to choose anything:
- main model = best macro-F1 in leave-one-person-out inside group 3;
- the "not sure" threshold also comes from those group 3 predictions.
Then each model is fitted on all of group 3 and tested once.

Reports: accuracy with the always-majority baseline (accuracy alone misleads, because most test
recordings are correct), balanced accuracy, macro-F1, within-exercise AUC for "needs attention",
and wrong answers among those it chose to answer.

BlazePose coordinates are fractions of the image, and the groups differ (group 3 is 960 x 540,
1A and 2A are 480 x 360), so x is scaled by each group's aspect ratio. Needs PyTorch.

  py -3.14 ml\\eval\\keraal_compare.py
"""

from __future__ import annotations

import argparse
import json
import re
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

import keraal_eval as ke  # noqa: E402
import keraal_model as km  # noqa: E402
from qawam_ml.rehab24 import REPO_ROOT  # noqa: E402
from qawam_ml.selective import clopper_pearson_upper  # noqa: E402

DEFAULT_GROUP3 = REPO_ROOT / "data" / "raw"
DEFAULT_OUT = REPO_ROOT / "data" / "derived" / "keraal-compare"
CLASSES = ("C", "Error1", "Error2", "Error3")
ASPECT_GROUP3, ASPECT_TEST = 960 / 540, 480 / 360
STEP = 2
SEEDS = 5
CNN_EPOCHS, GRU_EPOCHS = 150, 100
NAME = re.compile(r"G3-BP-(?P<exercise>[A-Z]{3})-(?P<person>P\d)T\d-\w+-(?P<label>C|E\dB\d)-\d+$")
MODELS = ("knn_dtw", "linear", "cnn", "gru")


def class_of_group3(label: str) -> int:
    return 0 if label == "C" else int(label[1])


def class_of_clinician(verdict: str | None, error_type: str | None) -> int | None:
    """The four classes; Incomplete, Motionless and Other have no group 3 equivalent."""
    if verdict == "Correct":
        return 0
    if verdict == "Incorrect" and error_type in CLASSES:
        return CLASSES.index(error_type)
    return None


def load_group3(raw: Path) -> list[dict[str, Any]]:
    rows = []
    for pose in sorted((raw / "blazepose").glob("G3-BP-*.json")):
        match = NAME.match(pose.stem)
        x = ke.features(pose, ASPECT_GROUP3, STEP) if match else None
        if x is not None and len(x):
            rows.append({"exercise": match["exercise"], "person": match["person"], "y": class_of_group3(match["label"]),
                         "input": km.to_input(x)})
    return rows


def load_test(root: Path) -> list[dict[str, Any]]:
    rows = []
    for r in ke.load(root, ASPECT_TEST, STEP):
        a, b = class_of_clinician(r["verdict_A"], r["type_A"]), class_of_clinician(r["verdict_B"], r["type_B"])
        rows.append({
            "exercise": r["exercise"], "person": r["person"], "take": r["take"], "patient": r["patient"],
            "input": km.to_input(r["x"]), "y_A": a, "y_B": b, "y_agreed": a if a == b else None,
            "label": km.agreed_label(r), "label_A": int(r["verdict_A"] != "Correct"), "label_B": int(r["verdict_B"] != "Correct"),
        })
    return rows


def standardise(train: np.ndarray, *others: np.ndarray) -> list[np.ndarray]:
    axes = tuple(range(train.ndim - 1))
    mean, std = train.mean(axis=axes, keepdims=True), train.std(axis=axes, keepdims=True) + 1e-6
    return [((a - mean) / std).astype(np.float32) for a in (train, *others)]


def knn_dtw(train: Sequence[Mapping[str, Any]], test: Sequence[Mapping[str, Any]], k: int = 5) -> np.ndarray:
    """Class shares among the k nearest training recordings, on the app's five angles."""
    probs = np.zeros((len(test), len(CLASSES)))
    refs = [(r["input"][:, -5:], r["y"]) for r in train]
    for i, r in enumerate(test):
        dists = sorted((ke.dtw(r["input"][:, -5:], x), y) for x, y in refs)
        for _, y in dists[:k]:
            probs[i, y] += 1 / k
    return probs


def linear(train: Sequence[Mapping[str, Any]], test: Sequence[Mapping[str, Any]]) -> np.ndarray:
    """Softmax regression on summary numbers (full-batch gradient descent, L2)."""
    a, b = standardise(np.stack([km.summary_features(r["input"]) for r in train]),
                       np.stack([km.summary_features(r["input"]) for r in test]))
    y = np.eye(len(CLASSES))[[r["y"] for r in train]]
    w = np.zeros((a.shape[1], len(CLASSES)))

    def softmax(z):
        z = np.exp(z - z.max(axis=1, keepdims=True))
        return z / z.sum(axis=1, keepdims=True)

    for _ in range(3000):
        w -= 0.1 * (a.T @ (softmax(a @ w) - y) / len(a) + 0.1 * w)
    return softmax(b @ w)


def build_gru(channels: int):
    from torch import nn

    class Gru(nn.Module):
        def __init__(self):
            super().__init__()
            self.gru = nn.GRU(channels, 24, batch_first=True)
            self.drop = nn.Dropout(km.DROPOUT)
            self.head = nn.Linear(24, len(CLASSES))

        def forward(self, x):
            return self.head(self.drop(self.gru(x)[1][0]))

    return Gru()


def deep(train: Sequence[Mapping[str, Any]], test: Sequence[Mapping[str, Any]], kind: str, seeds: int,
         epochs: int) -> np.ndarray:
    import torch

    x, x_test = standardise(np.stack([r["input"] for r in train]), np.stack([r["input"] for r in test]))
    y = torch.tensor([r["y"] for r in train])
    out = []
    for seed in range(seeds):
        torch.manual_seed(seed)
        rng = np.random.default_rng(seed)
        net = build_gru(x.shape[2]) if kind == "gru" else km.build_net(x.shape[2], len(CLASSES))
        ex = torch.zeros(1, len(km.EXERCISES))  # one model per exercise, so this input is constant
        forward = (lambda n, b: n(b)) if kind == "gru" else (lambda n, b: n(b, ex.expand(len(b), -1)))
        opt = torch.optim.AdamW(net.parameters(), lr=km.LR, weight_decay=km.WEIGHT_DECAY)
        x_t = torch.from_numpy(x)
        net.train()
        for _ in range(epochs):
            for batch in np.array_split(rng.permutation(len(x)), max(1, len(x) // km.BATCH)):
                idx = torch.from_numpy(batch)
                noisy = x_t[idx] + km.NOISE * torch.randn_like(x_t[idx])
                loss = torch.nn.functional.cross_entropy(forward(net, noisy), y[idx])
                opt.zero_grad()
                loss.backward()
                opt.step()
        net.eval()
        with torch.no_grad():
            out.append(torch.softmax(forward(net, torch.from_numpy(x_test)), dim=1).numpy())
    return np.mean(out, axis=0)


def predict(name: str, train: Sequence[Mapping[str, Any]], test: Sequence[Mapping[str, Any]], seeds: int, epochs: float) -> np.ndarray:
    if name == "knn_dtw":
        return knn_dtw(train, test)
    if name == "linear":
        return linear(train, test)
    full = GRU_EPOCHS if name == "gru" else CNN_EPOCHS
    return deep(train, test, name, seeds, max(1, round(full * epochs)))


def predict_by_exercise(name: str, train: Sequence[Mapping[str, Any]], test: Sequence[dict[str, Any]], key: str,
                        seeds: int, epochs: float) -> None:
    for e in km.EXERCISES:
        part = [r for r in test if r["exercise"] == e]
        if part:
            for r, p in zip(part, predict(name, [t for t in train if t["exercise"] == e], part, seeds, epochs)):
                r[key] = p


def scores(rows: Sequence[Mapping[str, Any]], key: str, label: str) -> dict[str, Any]:
    """Accuracy, majority baseline, balanced accuracy and macro-F1, over the classes present."""
    part = [r for r in rows if r[label] is not None]
    if not part:
        return {"n": 0}
    y = np.array([r[label] for r in part])
    pred = np.array([int(np.argmax(r[key])) for r in part])
    present = sorted(set(y.tolist()))
    recalls, f1s = [], []
    for c in present:
        tp = int(((y == c) & (pred == c)).sum())
        recalls.append(tp / (y == c).sum())
        denom = (y == c).sum() + (pred == c).sum()
        f1s.append(2 * tp / denom if denom else 0.0)
    return {"n": len(part), "accuracy": round(float((y == pred).mean()), 3),
            "majority": round(max((y == c).mean() for c in present), 3),
            "balanced": round(float(np.mean(recalls)), 3), "macro_f1": round(float(np.mean(f1s)), 3),
            "classes": {CLASSES[c]: int((y == c).sum()) for c in present}}


def confidence_threshold(pairs: Sequence[tuple[float, bool]], target: float = km.TARGET_RISK) -> float | None:
    """Lowest confidence whose answered set has an exact 95% upper bound on wrong answers <= target."""
    best, wrong = None, 0
    for n, (conf, is_wrong) in enumerate(sorted(pairs, key=lambda t: -t[0]), 1):
        wrong += int(is_wrong)
        if clopper_pearson_upper(wrong, n) <= target:
            best = conf
    return best


def attention_pairs(rows: Sequence[Mapping[str, Any]], key: str, label: str) -> list[tuple[float, bool]]:
    """(confidence, wrong) for the question "needs attention?": P(attention) = 1 - P(correct)."""
    pairs = []
    for r in rows:
        if r[label] is not None:
            p = 1 - float(r[key][0])
            pairs.append((max(p, 1 - p), (p >= 0.5) != bool(r[label])))
    return pairs


def build_report(group3: Sequence[Mapping[str, Any]], test: Sequence[Mapping[str, Any]], seeds: int, epochs: float) -> dict[str, Any]:
    report: dict[str, Any] = {"group3_recordings": len(group3), "test_recordings": len(test), "models": {}}
    people = sorted({r["person"] for r in group3})
    for r in group3:
        r["attention"] = int(r["y"] != 0)
    for name in MODELS:
        for person in people:
            predict_by_exercise(name, [r for r in group3 if r["person"] != person],
                                [r for r in group3 if r["person"] == person], f"oof_{name}", seeds, epochs)
        print(f"{name}: group 3 leave-one-person-out done", flush=True)
        predict_by_exercise(name, group3, test, f"p_{name}", seeds, epochs)
        print(f"{name}: fitted on all of group 3 and tested", flush=True)
    patients = [r for r in test if r["patient"]]
    for name in MODELS:
        key = f"p_{name}"
        for r in test:
            r[f"attention_{name}"] = 1 - float(r[key][0])
        t = confidence_threshold(attention_pairs(group3, f"oof_{name}", "attention"))
        chosen = [] if t is None else [c for c in attention_pairs(patients, key, "label") if c[0] >= t]
        wrong = sum(c[1] for c in chosen)
        report["models"][name] = {
            "group3_cv": scores(group3, f"oof_{name}", "y"),
            "published_style_A_1A_2A": {e: scores([r for r in test if r["exercise"] == e], key, "y_A") for e in km.EXERCISES},
            "patients_agreed_4class": {e: scores([r for r in patients if r["exercise"] == e], key, "y_agreed") for e in km.EXERCISES},
            "attention_auc": {lab: {**km.within_exercise_auc(patients, f"attention_{name}", lab),
                                    "ci95": km.auc_ci(patients, f"attention_{name}", lab)} for lab in ("label", "label_A", "label_B")},
            "attention_wrong_full": km.wrong_rate(patients, f"attention_{name}", "label"),
            "abstention": {"threshold_from_group3": None if t is None else round(t, 3), "answered": len(chosen), "wrong": wrong,
                           "of": len(attention_pairs(patients, key, "label")),
                           "upper95": round(clopper_pearson_upper(wrong, len(chosen)), 3) if chosen else None},
        }
    report["main_model"] = max(MODELS, key=lambda m: report["models"][m]["group3_cv"]["macro_f1"])
    report["majority_wrong_attention"] = km.majority_wrong(patients, "label")
    return report


def markdown(report: Mapping[str, Any]) -> str:
    main = report["main_model"]
    lines = [f"Group 3 {report['group3_recordings']} recordings -> test {report['test_recordings']}. "
             f"Main model chosen on group 3 only: **{main}**", "",
             "## Inside group 3, leave one person out", "", "| Model | Accuracy | Macro-F1 |", "| --- | --- | --- |"]
    lines += [f"| {m} | {r['group3_cv']['accuracy']} | {r['group3_cv']['macro_f1']} |" for m, r in report["models"].items()]
    lines += ["", "## Four classes, clinician A, patients + healthy (the published setup)", "",
              "| Model | Exercise | n | Accuracy | Always-majority | Balanced | Macro-F1 |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for m, r in report["models"].items():
        for e, s in r["published_style_A_1A_2A"].items():
            lines.append(f"| {m} | {e} | {s['n']} | {s['accuracy']} | {s['majority']} | {s['balanced']} | {s['macro_f1']} |")
    lines += ["", "## Needs attention?, patients where both clinicians agree", "",
              "| Model | AUC within exercise | 95% CI | CTK | ELK | RTK | Wrong, all answered | Threshold | Answered | Wrong | 95% upper |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for m, r in report["models"].items():
        a, b = r["attention_auc"]["label"], r["abstention"]
        lines.append(f"| {m} | {a['mean']} | {a['ci95']} | {a['CTK']} | {a['ELK']} | {a['RTK']} | {r['attention_wrong_full']} | "
                     f"{b['threshold_from_group3']} | {b['answered']} / {b['of']} | {b['wrong']} | {b['upper95']} |")
    lines += ["", f"Always the commonest answer per exercise, wrong: {report['majority_wrong_attention']}"]
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--group3", type=Path, default=DEFAULT_GROUP3)
    parser.add_argument("--root", type=Path, default=ke.DEFAULT_ROOT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--seeds", type=int, default=SEEDS)
    parser.add_argument("--epochs", type=float, default=1.0, help="fraction of the fixed epochs, for quick tests only")
    args = parser.parse_args(argv)
    group3, test = load_group3(args.group3), load_test(args.root)
    if not group3 or not test:
        print(f"need group 3 under {args.group3} and groups 1A/2A under {args.root}", file=sys.stderr)
        return 1
    print(f"group 3: {len(group3)}; test: {len(test)}", flush=True)
    report = build_report(group3, test, args.seeds, args.epochs)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (args.out / "summary.md").write_text(markdown(report), encoding="utf-8")
    print(markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

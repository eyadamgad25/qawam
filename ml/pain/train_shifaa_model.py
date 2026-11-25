"""Retrain the pain flag model with real Arabic titles (Shifaa, even consultation numbers) plus the synthetic notes.

Rules: docs/superpowers/specs/2026-11-25-pain-check-real-text.md. Same features and app code as the shipped model
(character 2-4-grams, logistic regression); only the training text and the threshold change. Fixed before any score:
- positive = symptom categories, negative = bone/muscle/sports titles outside them and 6,000 other titles; both halves even only;
- synthetic training notes and real titles count equally in total;
- 4,000 largest weights are kept, so the file stays phone-sized;
- threshold = the lowest at which at most 15% of ordinary titles are flagged, on the fifth of the even half kept out of training.

Writes data/derived/shifaa/model.json and scores it once. Needs scikit-learn (research only). --export only writes the same
model to web/src/painModel.json for the app (project owner's decision, docs/decisions.md 2026-11-25) and scores nothing.

  py -3.14 ml\\pain\\train_shifaa_model.py [--export]
"""

from __future__ import annotations

import json
import math
import random
import sys
from typing import Any

import numpy as np
from pain_text import char_ngrams
from shifaa_eval import OUT, REPO, SEED, blind_sample, confusion, load, run_app_check, target
from train_flag_model import load as load_notes

KEEP, MIN_DF, C, MAX_FALSE, OTHERS = 4000, 5, 1.0, 0.15, 6000


def features(texts: list[str], vocab: dict[str, int] | None = None):
    from scipy.sparse import csr_matrix

    grams = [char_ngrams(t) for t in texts]
    if vocab is None:
        df: dict[str, int] = {}
        for g in grams:
            for x in g:
                df[x] = df.get(x, 0) + 1
        vocab = {g: i for i, g in enumerate(sorted(g for g, c in df.items() if c >= MIN_DF))}
    rows, cols, vals = [], [], []
    for i, g in enumerate(grams):
        v = 1 / math.sqrt(max(1, len(g)))
        for x in g:
            if x in vocab:
                rows.append(i)
                cols.append(vocab[x])
                vals.append(v)
    return csr_matrix((vals, (rows, cols)), shape=(len(texts), len(vocab)), dtype=np.float32), vocab


def train_model(rows: list[dict[str, Any]], notes: list[dict[str, Any]]) -> dict[str, Any]:
    from sklearn.linear_model import LogisticRegression

    rng = random.Random(SEED)
    even = sorted((r for r in rows if r["id"] % 2 == 0), key=lambda r: r["id"])
    held = [r for r in even if r["id"] % 10 == 0]
    fit = [r for r in even if r["id"] % 10]
    pos = [r["title"] for r in fit if r["kind"] == "symptom"]
    neg = [r["title"] for r in fit if target(r) and r["kind"] != "symptom"]
    neg += rng.sample([r["title"] for r in fit if not target(r) and r["kind"] == "other"], OTHERS)
    texts = [*pos, *neg, *(n["text"] for n in notes)]
    y = np.array([1] * len(pos) + [0] * len(neg) + [int(n["red_flag"]) for n in notes])
    weight = np.empty(len(y))
    real = len(pos) + len(neg)
    for block in (slice(0, real), slice(real, None)):
        for c in (0, 1):
            mask = np.zeros(len(y), bool)
            mask[block] = True
            mask &= y == c
            weight[mask] = len(y) / 4 / mask.sum()
    x, vocab = features(texts)
    clf = LogisticRegression(C=C, max_iter=2000).fit(x, y, sample_weight=weight)
    w, b = clf.coef_[0], float(clf.intercept_[0])
    top = set(np.argsort(-np.abs(w))[:KEEP].tolist())
    weights = {g: round(float(w[i]), 4) for g, i in vocab.items() if i in top}

    def score(text: str) -> float:
        g = char_ngrams(text)
        return b + sum(weights.get(x, 0.0) for x in g) / math.sqrt(max(1, len(g)))

    ordinary = sorted(score(r["title"]) for r in held if target(r) and r["kind"] != "symptom")
    threshold = ordinary[min(len(ordinary) - 1, math.ceil((1 - MAX_FALSE) * len(ordinary)))]
    print(f"train: {len(pos)} symptom, {len(neg)} other titles, {len(notes)} notes; kept {len(weights)}; "
          f"threshold {threshold:.3f} from {len(ordinary)} held-out ordinary titles")
    return {"about": "research candidate, not shipped", "ngram": [2, 4], "bias": round(b, 4), "threshold": round(threshold, 4),
            "weights": weights, "checks": []}


def export(model: dict[str, Any]) -> None:
    """The app's model file, with check scores so that a web test catches any drift between Python and TypeScript."""

    def score(text: str) -> float:
        g = char_ngrams(text)
        return model["bias"] + sum(model["weights"].get(x, 0.0) for x in g) / math.sqrt(len(g))

    model = {**model, "about": "Pain red-flag model: logistic regression on character n-grams. Trained on titles of published Arabic "
             "consultations (Shifaa, Kaggle, Apache 2.0, even consultation numbers) and synthetic notes (ml/pain/training-notes.jsonl); "
             "not reviewed by a clinician. Used only together with the word list (flag if either flags).",
             "checks": [{"text": n["text"], "score": round(score(n["text"]), 6)} for n in load_notes("synthetic-notes.jsonl")[::10]]}
    path = REPO / "web" / "src" / "painModel.json"
    path.write_text(json.dumps(model, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{path.stat().st_size / 1024:.0f} KB -> {path}")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    rows = load()
    model = train_model(rows, load_notes("training-notes.jsonl"))
    if "--export" in sys.argv[1:]:
        export(model)
        return 0
    path = OUT / "model.json"
    path.write_text(json.dumps(model, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{path.stat().st_size / 1024:.0f} KB")
    blind = blind_sample(rows)
    labels = json.loads((OUT / "labels.json").read_text(encoding="utf-8"))
    y = [bool(labels[str(i + 1)]) for i in range(len(blind))]
    notes = load_notes("synthetic-notes.jsonl")
    test = [n for n in notes if n["split"] == "test"]
    report: dict[str, Any] = {}
    for name, alt in (("shipped model", None), ("retrained model", path)):
        flags = run_app_check([r["title"] for r in blind], alt)
        full = [f["list"] or f["temp"] or f["model"] for f in flags]
        block: dict[str, Any] = {}
        for group in ("all", "target", "symptom"):
            idx = [i for i, r in enumerate(blind) if group in ("all", r["group"])]
            block[f"blind {group}, check"] = confusion([y[i] for i in idx], [full[i] for i in idx])
            block[f"blind {group}, model alone"] = confusion([y[i] for i in idx], [flags[i]["model"] for i in idx])
        for split, part in (("synthetic test", test), ("synthetic all", notes)):
            f = run_app_check([n["text"] for n in part], alt)
            block[split] = confusion([n["red_flag"] for n in part], [a["list"] or a["temp"] or a["model"] for a in f])
        report[name] = block
    (OUT / "retrained.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    for name, block in report.items():
        print(name)
        for k, v in block.items():
            print(f"   {k}: caught {v['tp']}/{v['positive']} ({v['recall']}), false alarms {v['fp']}/{v['fp'] + v['tn']} "
                  f"({v['false_alarm_rate']}), accuracy {v['accuracy']}, F1 {v['f1']}, macro-F1 {v['macro_f1']}")
    return 0


if __name__ == "__main__":
    assert REPO.exists()
    raise SystemExit(main())

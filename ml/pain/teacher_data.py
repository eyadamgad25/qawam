"""The training labels of the pain model, shared by the phone model (train_shifaa_model.py) and the Kaggle teachers.

Fixed in docs/superpowers/specs/2026-11-25-pain-check-real-text.md: even consultation numbers only, those ending in 0 held out;
titles = symptom categories, bone/muscle/sports titles outside them and 6,000 other titles; synthetic notes and real titles
count equally in total, and so do the two classes inside each. By default a title's label is its category (symptom = 1);
`labels` replaces it (LLM labels, docs/superpowers/specs/2026-11-26-llm-pain-labels-design.md).
"""

from __future__ import annotations

import random
from typing import Any

import numpy as np
from shifaa_eval import SEED, target

OTHERS = 6000


def fit_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(training titles, held-out titles): even numbers only; held out = divisible by 10."""
    even = sorted((r for r in rows if r["id"] % 2 == 0), key=lambda r: r["id"])
    return [r for r in even if r["id"] % 10], [r for r in even if r["id"] % 10 == 0]


def training_rows(rows: list[dict[str, Any]], others: int = OTHERS) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(symptom-category titles, other titles) used for training, in a fixed order."""
    rng = random.Random(SEED)
    fit, _ = fit_rows(rows)
    pos = [r for r in fit if r["kind"] == "symptom"]
    neg = [r for r in fit if target(r) and r["kind"] != "symptom"]
    neg += rng.sample([r for r in fit if not target(r) and r["kind"] == "other"], others)
    return pos, neg


def training_set(rows: list[dict[str, Any]], notes: list[dict[str, Any]], others: int = OTHERS,
                 labels: dict[int, int] | None = None):
    """(texts, y, weight) in the order symptom-category titles, other titles, notes."""
    pos, neg = training_rows(rows, others)
    titles = pos + neg
    if labels is None:
        title_y = [1] * len(pos) + [0] * len(neg)
    else:
        missing = [r["id"] for r in titles if r["id"] not in labels]
        if missing:
            raise ValueError(f"{len(missing)} training titles have no label")
        title_y = [int(labels[r["id"]]) for r in titles]
    texts = [*(r["title"] for r in titles), *(n["text"] for n in notes)]
    y = np.array(title_y + [int(n["red_flag"]) for n in notes])
    weight = np.empty(len(y))
    real = len(titles)
    for block in (slice(0, real), slice(real, None)):
        for c in (0, 1):
            mask = np.zeros(len(y), bool)
            mask[block] = True
            mask &= y == c
            weight[mask] = len(y) / 4 / max(1, mask.sum())
    return texts, y, weight

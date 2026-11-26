"""Choose the LLM's yes-threshold on blind set 1, then run the gate once on blind set 2.

Spec: docs/superpowers/specs/2026-11-26-llm-pain-labels-design.md. Gate: Cohen's kappa with the assistant's labels >= 0.60
and above the kappa of the category label (symptom category = yes). Writes data/derived/shifaa/llm_gate.json. Counts only.

  py -3.14 ml\\pain\\llm_gate.py data\\derived\\shifaa\\llm_scores.csv
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
from shifaa_eval import OUT, blind_sample, blind_sample2, confusion, load

MIN_KAPPA = 0.60


def cohen_kappa(a, b) -> float:
    a, b = np.asarray(a, bool), np.asarray(b, bool)
    observed = np.mean(a == b)
    chance = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
    return 1.0 if chance == 1 else float((observed - chance) / (1 - chance))


def best_threshold(p, y) -> float:
    """The candidate threshold (each distinct score, flag if p >= t) with the highest macro-F1; the higher one on a tie."""
    p, y = np.asarray(p), list(map(bool, y))
    best, best_t = -1.0, 0.5
    for t in sorted(set(p.tolist()), reverse=True):
        f = confusion(y, (p >= t).tolist())["macro_f1"]
        if f > best:
            best, best_t = f, t
    return float(best_t)


def read_llm(path: Path) -> dict[str, dict[int, float]]:
    out: dict[str, dict[int, float]] = {}
    with path.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            out.setdefault(r["set"], {})[int(r["id"])] = float(r["p_yes"])
    return out


def labels_of(name: str, sample) -> list[bool]:
    labels = json.loads((OUT / name).read_text(encoding="utf-8"))
    return [bool(labels[str(i + 1)]) for i in range(len(sample))]


def main(argv: list[str]) -> int:
    rows = load()
    llm = read_llm(Path(argv[0]))
    first, second = blind_sample(rows), blind_sample2(rows)
    for name, part in (("blind1", first), ("blind2", second)):
        if {r["id"] for r in part} - set(llm.get(name, {})):
            raise ValueError(f"llm_scores.csv lacks titles of {name}")
    y1, y2 = labels_of("labels.json", first), labels_of("labels2.json", second)
    t = best_threshold([llm["blind1"][r["id"]] for r in first], y1)
    flags = [llm["blind2"][r["id"]] >= t for r in second]
    category = [r["kind"] == "symptom" for r in second]
    k_llm, k_cat = cohen_kappa(flags, y2), cohen_kappa(category, y2)
    report = {"threshold (chosen on blind set 1)": round(t, 5), "kappa_llm": round(k_llm, 3), "kappa_category": round(k_cat, 3),
              "llm on blind set 2": confusion(y2, flags), "category on blind set 2": confusion(y2, category),
              "passes": k_llm >= MIN_KAPPA and k_llm > k_cat}
    (OUT / "llm_gate.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if not isinstance(v, dict)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

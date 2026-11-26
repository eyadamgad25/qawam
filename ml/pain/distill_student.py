"""Teach the phone pain model from a Kaggle teacher's scores (distillation), then run the one-time test on the second blind set.

Spec and pass rule: docs/superpowers/specs/2026-11-26-arabic-pain-model-design.md (only the CAMeLBERT-DA student can ship).
Same features, weight cap and app code as today's model; only the training targets change (teacher probabilities).
Writes data/derived/shifaa/student_<teacher>.json and distill.json. Counts only, no text.
With --blind 3 (docs/superpowers/specs/2026-11-26-llm-pain-labels-design.md): blind set 3, all three blind sets removed from
distillation, macro-F1 gain, student_llm_<teacher>.json and distill3.json; --llm <llm_scores.csv> <threshold> adds the LLM ceiling.

  py -3.14 ml\\pain\\distill_student.py data\\derived\\shifaa\\teacher_scores.csv
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
from pain_text import char_ngrams, normalize
from shifaa_eval import OUT, REPO, SEED, blind_sample, blind_sample2, blind_sample3, confusion, load, run_app_check, target
from teacher_data import fit_rows
from train_flag_model import load as load_notes
from train_shifaa_model import C, KEEP, features

SHIPPABLE = "camelbert"
NOTE_FILES = ("synthetic-notes.jsonl", "training-notes.jsonl")


def read_scores(path: Path, rows: list[dict[str, Any]], note_counts: dict[str, int]) -> dict[tuple[str, str], dict[str, float]]:
    """{(kind, key): {teacher: p}}; raises if any title or note is missing or unknown."""
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        teachers = [c for c in reader.fieldnames or [] if c not in ("kind", "key")]
        got = {(r["kind"], r["key"]): {t: float(r[t]) for t in teachers} for r in reader}
    want = {("title", str(r["id"])) for r in rows} | {("note", f"{n}:{i}") for n, c in note_counts.items() for i in range(c)}
    if set(got) != want:
        raise ValueError(f"teacher scores do not match the data: {len(want - set(got))} missing, {len(set(got) - want)} unknown")
    return got


def soft_fit(x, p: np.ndarray, weight: np.ndarray) -> tuple[float, np.ndarray]:
    """Logistic regression on soft targets: each text counts as yes with weight w*p and as no with weight w*(1-p)."""
    from scipy.sparse import vstack
    from sklearn.linear_model import LogisticRegression

    yes, no = weight * p > 0, weight * (1 - p) > 0
    xx = vstack([x[yes], x[no]]) if hasattr(x, "tocsr") else np.vstack([x[yes], x[no]])
    y = np.r_[np.ones(yes.sum()), np.zeros(no.sum())]
    w = np.r_[(weight * p)[yes], (weight * (1 - p))[no]]
    clf = LogisticRegression(C=C, max_iter=3000).fit(xx, y, sample_weight=w)
    return float(clf.intercept_[0]), clf.coef_[0]


def threshold_matching(scores: np.ndarray, target_rate: float) -> float:
    """Lowest threshold at which at most target_rate of these scores are strictly above it."""
    s = np.sort(np.asarray(scores))[::-1]
    allowed = math.floor(target_rate * len(s) + 1e-9)
    return float(s[allowed]) if allowed < len(s) else float(s[-1]) - 1e-6


def model_score(model: dict[str, Any], text: str) -> float:
    g = char_ngrams(text)
    return model["bias"] + sum(model["weights"].get(x, 0.0) for x in g) / math.sqrt(max(1, len(g)))


def distillation_titles(rows, blind: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every title except the held-out even ones and the blind sets, matched by number and by normalised text."""
    held = {r["id"] for r in fit_rows(rows)[1]}
    ids, texts = {r["id"] for r in blind}, {normalize(r["title"]) for r in blind}
    return [r for r in rows if r["id"] not in held and r["id"] not in ids and normalize(r["title"]) not in texts]


def distil(rows, scores, teacher: str, blind: list[dict[str, Any]]):
    titles = distillation_titles(rows, blind)
    notes = load_notes("training-notes.jsonl")
    texts = [r["title"] for r in titles] + [n["text"] for n in notes]
    p = np.array([scores[("title", str(r["id"]))][teacher] for r in titles]
                 + [scores[("note", f"training-notes.jsonl:{i}")][teacher] for i in range(len(notes))])
    weight = np.r_[np.full(len(titles), 0.5 / len(titles)), np.full(len(notes), 0.5 / len(notes))] * len(texts)
    x, vocab = features(texts)
    b, w = soft_fit(x, p, weight)
    top = set(np.argsort(-np.abs(w))[:KEEP].tolist())
    return {"about": f"research candidate distilled from {teacher}, not shipped", "ngram": [2, 4], "bias": round(b, 4),
            "weights": {g: round(float(w[i]), 4) for g, i in vocab.items() if i in top}, "checks": []}, len(titles), len(notes)


def gain_interval(y, old, new, n=2000, metric: str = "recall", seed: int = SEED) -> list[float]:
    """95% interval of new minus old, resampling titles: recall (distillation test) or macro_f1 (LLM-label test)."""
    rng = np.random.default_rng(seed)
    y, old, new = (np.asarray(a, bool) for a in (y, old, new))
    out = []
    for _ in range(n):
        i = rng.integers(0, len(y), len(y))
        if metric == "recall":
            out.append(((new[i] & y[i]).sum() - (old[i] & y[i]).sum()) / max(1, y[i].sum()))
        else:
            out.append(confusion(y[i].tolist(), new[i].tolist())[metric] - confusion(y[i].tolist(), old[i].tolist())[metric])
    return [round(float(q), 4) for q in np.percentile(out, [2.5, 97.5])]


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    rows = load()
    note_counts = {n: len(load_notes(n)) for n in NOTE_FILES}
    scores = read_scores(Path(argv[0]), rows, note_counts)
    first, second = blind_sample(rows), blind_sample2(rows)
    third = "--blind" in argv and argv[argv.index("--blind") + 1] == "3"
    removed = first + second
    metric, seed, tag, label_file = "recall", SEED, "", "labels2.json"
    if third:
        second = blind_sample3(rows)
        removed = removed + second
        metric, seed, tag, label_file = "macro_f1", 20261127, "3", "labels3.json"
    labels = json.loads((OUT / label_file).read_text(encoding="utf-8"))
    y = [bool(labels[str(i + 1)]) for i in range(len(second))]
    _, held = fit_rows(rows)
    ordinary = [r["title"] for r in held if target(r) and r["kind"] != "symptom"]
    today = json.loads((REPO / "web" / "src" / "painModel.json").read_text(encoding="utf-8"))
    rate = float(np.mean([model_score(today, t) > today["threshold"] for t in ordinary]))
    texts = [r["title"] for r in second]
    old = run_app_check(texts)
    old_full = [f["list"] or f["temp"] or f["model"] for f in old]
    synth = [n for n in load_notes("synthetic-notes.jsonl") if n["split"] == "test"]
    report: dict[str, Any] = {"held-out ordinary titles": len(ordinary), "today's flag rate there": round(rate, 4),
                              f"blind{tag or 2} positives": sum(y), "rule": f"{metric} gain interval above 0", "today": {}}
    for group in ("all", "target", "symptom"):
        idx = [i for i, r in enumerate(second) if group in ("all", r["group"])]
        report["today"][group] = confusion([y[i] for i in idx], [old_full[i] for i in idx])
    report["today"]["synthetic test"] = confusion([n["red_flag"] for n in synth],
                                                  [a["list"] or a["temp"] or a["model"] for a in run_app_check([n["text"] for n in synth])])
    if third:  # also reported: the category-label student of the last test, and the LLM itself, on blind set 3

        def block_of(flags):
            idx = {g: [i for i, r in enumerate(second) if g in ("all", r["group"])] for g in ("all", "target", "symptom")}
            return {g: confusion([y[i] for i in ix], [flags[i] for i in ix]) for g, ix in idx.items()}

        if (OUT / "student_camelbert.json").exists():
            cat = run_app_check(texts, OUT / "student_camelbert.json")
            report["category-label student"] = block_of([f["list"] or f["temp"] or f["model"] for f in cat])
        if "--llm" in argv:
            from llm_gate import read_llm

            j = argv.index("--llm")
            llm, cut = read_llm(Path(argv[j + 1]))["blind3"], float(argv[j + 2])
            report["LLM (ceiling)"] = block_of([o["list"] or o["temp"] or llm[r["id"]] >= cut for o, r in zip(old, second)])
    for teacher in list(next(iter(scores.values()))):
        model, n_titles, n_notes = distil(rows, scores, teacher, removed)
        model["threshold"] = round(threshold_matching(np.array([model_score(model, t) for t in ordinary]), rate), 4)
        path = OUT / f"student{'_llm' if third else ''}_{teacher}.json"
        path.write_text(json.dumps(model, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        new = run_app_check(texts, path)
        new_full = [f["list"] or f["temp"] or f["model"] for f in new]
        t_held = np.array([scores[("title", str(r["id"]))][teacher] for r in held if target(r) and r["kind"] != "symptom"])
        t_cut = threshold_matching(t_held, rate)
        t_full = [o["list"] or o["temp"] or scores[("title", str(r["id"]))][teacher] > t_cut for o, r in zip(old, second)]
        block: dict[str, Any] = {"distilled on": {"titles": n_titles, "notes": n_notes}, "student KB": round(path.stat().st_size / 1024)}
        for name, flags in (("student", new_full), ("teacher (ceiling)", t_full)):
            block[name] = {}
            for group in ("all", "target", "symptom"):
                idx = [i for i, r in enumerate(second) if group in ("all", r["group"])]
                block[name][group] = confusion([y[i] for i in idx], [flags[i] for i in idx])
        block["student"]["synthetic test"] = confusion(
            [n["red_flag"] for n in synth], [a["list"] or a["temp"] or a["model"] for a in run_app_check([n["text"] for n in synth], path)])
        key = f"{metric} gain, 95% interval"
        block[key] = gain_interval(y, old_full, new_full, metric=metric, seed=seed)
        s, o = block["student"]["target"], report["today"]["target"]
        block["passes"] = block[key][0] > 0 and s["fn"] <= o["fn"]
        report[teacher] = block
        print(f"{teacher}: student caught {block['student']['all']['tp']}/{sum(y)} vs today {report['today']['all']['tp']}; "
              f"interval {block[key]}; target misses {s['fn']} vs {o['fn']}; passes {block['passes']}")
    report["ships"] = SHIPPABLE if SHIPPABLE in report and report[SHIPPABLE]["passes"] else None
    (OUT / f"distill{tag}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("ships:", report["ships"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

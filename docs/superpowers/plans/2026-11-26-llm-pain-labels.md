# LLM Pain Labels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the category labels of the pain model's training titles with an open LLM's codebook labels, gate them, retrain the CAMeLBERT teacher and the 64 KB student, and test once on a third blind set.

**Architecture:** Kaggle run 1 scores titles with Qwen2.5-7B-Instruct (`ml/pain/llm_label.py`). The laptop picks a threshold and runs the gate (`ml/pain/llm_gate.py`). Kaggle run 2 trains CAMeLBERT on the LLM labels (`teacher_train.py --llm`). The laptop distils and tests (`distill_student.py`, generalised).

**Tech Stack:** Python 3.14, NumPy, scikit-learn (laptop); torch + transformers + accelerate on Kaggle.

**Spec:** `docs/superpowers/specs/2026-11-26-llm-pain-labels-design.md`

## Global Constraints
- Third blind set: 400 odd titles not in blind sets 1 and 2; 240 target, 160 symptom; seed 20261127; labelled before any LLM output; SHA-256 recorded in the spec.
- Prompt fixed in code and committed before run 1; only the threshold is tuned, on blind set 1.
- Gate: kappa with the assistant's labels on blind set 2 >= 0.60 and above the category label's kappa. Run once.
- Ship: macro-F1 gain on blind set 3, 95% interval above 0 (2,000 resamples, seed 20261127), and target misses <= today's. Run once.
- Only numbers leave Kaggle. CAMeLBERT-DA is the only teacher. The LLM never ships.

## Review Focus
- An LLM answer that is neither yes nor no: P(yes) still comes from the two answer-token logits, so every title gets a number (test in Task 2).
- `llm_scores.csv` missing a training title: run 2 must stop, not train on fewer (test in Task 3).
- `distill_student.py` must still read the two-teacher file of the last test and the one-teacher file of this one (test in Task 4).
- Blind set 3 must never be among the LLM-labelled training titles (they are even; test in Task 1).

---

### Task 1: Third blind set
**Files:** Modify `ml/pain/shifaa_eval.py`, `tests/python/test_shifaa_eval.py`
**Interfaces:** Produces `blind_sample3(rows) -> list[dict]` (same shape as `blind_sample2`); CLI `sample3` writes `data/derived/shifaa/blind3.jsonl`.
- [ ] Test: 400 odd ids, none in sets 1 or 2, 240 target.
- [ ] Implement; draw; label by the codebook into `labels3.json`; record SHA-256 in the spec.

### Task 2: LLM labelling (Kaggle run 1)
**Files:** Create `ml/pain/llm_label.py`, `notebooks/pain_llm_labels_kaggle.ipynb`, `tests/python/test_llm_label.py`; Modify `ml/pain/teacher_data.py`
**Interfaces:** `teacher_data.training_rows(rows) -> (pos_rows, neg_rows)` (used by `training_set`, unchanged output). `llm_label.PROMPT: str`; `yes_probability(model, tok, titles, device) -> np.ndarray`; `main([source, out])` writes `llm_scores.csv` with `set,id,p_yes` (`set` in blind1, blind2, train).
- [ ] Test with a tiny random causal LM: one probability per title in [0, 1]; `training_set` output unchanged.

### Task 3: Gate and teacher on LLM labels (Kaggle run 2)
**Files:** Create `ml/pain/llm_gate.py`, `tests/python/test_llm_gate.py`; Modify `ml/pain/teacher_train.py`, `ml/pain/teacher_data.py`
**Interfaces:** `cohen_kappa(a, b) -> float`; `best_threshold(p, y) -> float` (max macro-F1); `llm_gate.py` writes `llm_gate.json` with `threshold`, `kappa_llm`, `kappa_category`, `passes`. `training_set(rows, notes, labels: dict[int, int] | None = None)`. `teacher_train.py <shifaa> <out> --llm <llm_scores.csv> <threshold>` trains CAMeLBERT only and writes `teacher_scores_llm.csv` (`kind,key,camelbert`).
- [ ] Tests: kappa on known cases; threshold picks the best macro-F1; a missing training id raises.

### Task 4: Test on blind set 3
**Files:** Modify `ml/pain/distill_student.py`, `tests/python/test_distill_student.py`
**Interfaces:** `distill_student.py <scores.csv> --blind 3` uses the teachers present in the file, blind set 3 and `labels3.json`, macro-F1 gain; writes `distill3.json`. The default (`--blind 2`) keeps the last test's rule.
- [ ] Test: `read_scores` with one teacher column; macro-F1 gain interval sign on a toy case.

### Task 5: Commit, push, hand over both Kaggle runs; after them record the result in `docs/experiments.md`, `docs/metrics.md`.

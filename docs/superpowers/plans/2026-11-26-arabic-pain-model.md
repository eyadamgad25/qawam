# Arabic Pain Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Teach the 64 KB on-phone pain model from two Arabic language models trained on Kaggle, and replace it only if a test fixed in advance says so.

**Architecture:** A Kaggle notebook fine-tunes MARBERTv2 and CAMeLBERT-DA on the same weak labels as today's model and writes one score per Shifaa title. A laptop script trains the existing character n-gram model on those scores (distillation) and runs the one-time test against today's model.

**Tech Stack:** Python 3.14, NumPy, scikit-learn (research only), PyTorch + transformers on Kaggle, the app's TypeScript check via `ml/pain/pain_batch.ts`.

**Spec:** `docs/superpowers/specs/2026-11-26-arabic-pain-model-design.md`

## Global Constraints
- Shifaa text never enters git or the notebook output; only ids and scores do.
- New blind set: 300 odd-numbered titles not among the earlier 250, 180 bone/muscle/sports and 120 symptom-category, labelled with the codebook in `docs/superpowers/specs/2026-11-25-pain-check-real-text.md` **before any model is trained**; labels frozen in `data/derived/shifaa/labels2.json`.
- Held-out even titles: consultation number divisible by 10 (as in `train_shifaa_model.py`); never trained on.
- Distillation never uses a blind-set title.
- Pass rule: at a threshold matching today's false-alarm rate on held-out ordinary titles, the student catches more signs on the new blind set (95% interval of the gain, resampling titles, above 0) and misses no more on bone/muscle/sports titles. Measured once.
- MARBERTv2 is research-only (no licence stated). Teachers never ship.

## Review Focus
- Kaggle unzips datasets into folders: the loader must read a folder of CSVs as well as the zip (test in Task 1).
- A title shared by a blind set and the distillation data would leak: distillation must drop it by normalised text, not only by id (test in Task 3).
- A teacher score file with missing or extra ids must fail loudly, not silently train on fewer rows (test in Task 3).
- The note before use must change only if the student is shipped, with the new measured numbers (Task 4).
- Training on Kaggle without a graphics card must stop with a clear message rather than run for hours (Task 2).

---

### Task 1: Second blind set and a folder-capable loader
**Files:** Modify `ml/pain/shifaa_eval.py`; Test `tests/python/test_shifaa_eval.py`
**Interfaces:** Produces `load(source: Path | None = None) -> list[dict]` (zip or folder of CSVs) and `blind_sample2(rows) -> list[dict]` (same dict shape as `blind_sample`); `py -3.14 ml\pain\shifaa_eval.py sample2` writes `data/derived/shifaa/blind2.jsonl`.
- [ ] Test: a folder with the same CSVs loads the same rows as the zip; `blind_sample2` returns 300 odd ids, none in `blind_sample`, 180 target and 120 symptom.
- [ ] Implement; run tests; draw the sample; label it by the codebook into `labels2.json` before Task 2.

### Task 2: Kaggle teacher notebook
**Files:** Create `ml/pain/teacher_data.py`, `notebooks/pain_teacher_kaggle.ipynb`; Modify `ml/pain/train_shifaa_model.py`; Test `tests/python/test_teacher_data.py`
**Interfaces:** Produces `training_set(rows, notes) -> (texts: list[str], y: np.ndarray, weight: np.ndarray)` used by both `train_shifaa_model.train_model` and the notebook (same labels everywhere); the notebook writes `teacher_scores.csv` with columns `kind,key,marbert,camelbert` (`kind` = `title` with key = consultation number, or `note` with key = line index in `synthetic-notes.jsonl`/`training-notes.jsonl` as `file:index`).
- [ ] Test: `training_set` reproduces the counts the current model was trained on (932 positives, 7,952 negatives, 846 notes) and the weights sum per block as before.
- [ ] Refactor `train_model` to use it; existing pain tests still pass; exported model unchanged (`painModel.json` weights identical).
- [ ] Notebook: clone the public repository, find Shifaa under `/kaggle/input`, stop if no graphics card, fine-tune each teacher (fixed: 3 epochs, learning rate 2e-5, max length 64, batch 32, seed 20261126), score every title and note, save the CSV. Smoke-run the notebook cells locally with a tiny random BERT on 40 rows.

### Task 3: Distil the student and run the one-time test
**Files:** Create `ml/pain/distill_student.py`; Test `tests/python/test_distill_student.py`
**Interfaces:** Consumes `teacher_scores.csv`, `training_set`, `features`, `run_app_check(texts, model)`. Produces `soft_fit(x, p, weight) -> (bias, weights)`, `threshold_matching(student_scores, target_rate) -> float`, and `data/derived/shifaa/student_<teacher>.json` plus `distill.json` with the test.
- [ ] Tests: soft targets of exactly 0/1 give the same model as hard labels; a blind title appearing in the distillation texts (after `normalize`) is removed; a score file missing ids raises.
- [ ] Implement; run once per teacher; record results.

### Task 4: Decide, record, and (only if it passes) ship
**Files:** Modify `docs/experiments.md`, `docs/metrics.md`, `docs/datasets.md`; if passed also `web/src/painModel.json`, `web/src/painModel.ts` (`PAIN_TEST`), `web/src/App.test.tsx`
- [ ] Write the result as measured, including teachers as the ceiling and agreement with the doctor's labels when available.
- [ ] If passed: export the student, update `PAIN_TEST` with the new blind-set numbers, run all web and Python tests, check the note in the running app.
- [ ] Commit.

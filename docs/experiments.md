# Experiments log

Append-only. Newest entry at the top. Record what was run, on what data, and the outcome. No clinical claims.

---

## 2026-10-23 — Task 1a-4 — Evidence levels and rule schema (docs only)

- **Hypothesis:** Naming three evidence levels and schema fields `status` / `approvedBy` / `approvedAt` / `provenance` stops dataset cutoffs and demo accounts from looking clinically approved.
- **Setup:** Docs only; no code, no `data/raw/`, no `ml/splits.json`.
- **Command:** none (schema/docs).
- **Data:** none.
- **Result:** Levels defined in `docs/decisions.md` and `docs/safety-case.md`. Schema updated in `docs/AI_BRIEF.md` and `rules/README.md`. Advisor recorded as TBD (unassigned); demo seed is not an approver; provisional-fire banner required.
- **Caveats / UNVERIFIED:** Banner and approval-gate enforcement are not implemented until later tasks. G1 still open.

## 2026-10-23 — Task 1a-3 — Filters, split audit, test-access log path

- **Hypothesis:** Named stdlib filters match the stated flag logic; CSV-only audit can describe the frozen 6/2/2 split without touching video/npy or `ml/splits.json`.
- **Setup:** Windows, `.venv` Python 3.14.0; pytest stdlib tests; pandas only in `audit_splits.py`.
- **Command:** `.\.venv\Scripts\python.exe -m pytest tests/python`; `.\.venv\Scripts\python.exe ml/eval/audit_splits.py`.
- **Data:** `Segmentation.csv` (semicolon, 1072 rows) + frozen `ml/splits.json`. Test split not loaded via `load_repetitions`.
- **Result:** `pytest tests/python` 14 passed. Audit: train 592 / val 238 / test 242 (CSV metadata; test not loaded). `gt_quality` cam17 train 267 val 98; cam18 train 402 val 115. Warning: validation Ex6 correctness=0 has 9 reps. `ml/splits.json` unchanged.
- **Caveats / UNVERIFIED:** Audit test-split cells are CSV metadata counts, not an evaluation run. License dual-wording recorded; we follow the stricter research-only text plus CC BY-NC 4.0.

## 2026-10-21 — Task 1a — REHAB24-6 inspect + loader tests

- **Hypothesis:** Local REHAB24-6 matches the owner’s CSV/file facts; a synthetic-fixture loader can split on `person_id` and seal the test set.
- **Setup:** Windows, `.venv` Python 3.14.0; packages from `pip show` (mediapipe 1.1.1, numpy 2.5.4, opencv-python 5.0.0.93, pandas 3.0.6, matplotlib 3.11.2). pytest was **not** in the venv; pin remains 9.1.1.
- **Command:** pandas/OpenCV probes on `data/raw/rehab24-6` (gitignored); `python -m pytest tests/python`.
- **Data:** REHAB24-6 local extract. CSV 1072 rows. Ex1/PM_000 Camera17 1304×30fps 1920×1080; c17 npy (1304,26,2). Camera18 transposed video 1080×1920, c18 npy (1304,26,2). 120fps npy (5215,26,2). Clean subset 521 rows. Split train `[8,5,6,2,3,10]` val `[4,1]` test `[7,9]`.
- **Result:** `pytest tests/python` 8 passed (7 loader + 1 scaffold). Real CSV (not committed): 1072 rows; train 592 (persons 2,3,5,6,8,10); validation 238 (1,4); train clean 267; `load_repetitions('test')` raises `SealedTestSplitError` with no log file. Test split not opened.
- **Caveats / UNVERIFIED:** joint origin; c18 npy vs transposed pixels; MediaPipe landmark map; Segmentation.txt `side`/`camera17` typos. No MediaPipe inference. Zips not re-hashed here (owner reported MD5 match).
- **Next:** Task 1b overlay + MediaPipe 1.1.1 (read *installed* docs; no legacy `mp.solutions.pose` unless it exists).

## 2026-10-21 — Task 0 — Scaffold smoke

- **Hypothesis:** Root lint, typecheck, JS unit tests, and pytest (scaffold only) pass on a clean install.
- **Setup:** Empty workspace → repo skeleton. Node v24.18.1, npm 11.16.0. Python 3.11 **not installed locally** (py reports 3.14.0). CI targets Python 3.11.
- **Command:** `npm install && npm run typecheck && npm run lint && npm run format:check && npm test` and `py -3.14 -m pytest` (local fallback; 3.11 preferred).
- **Data:** none.
- **Result:** After `$env:NODE_OPTIONS='--use-system-ca'` (local TLS intercept; GitHub Actions should not need this): `npm install` OK. After import-path + Prettier fixes: `typecheck`, `lint`, `format:check` pass; `npm test` 4 passed (web 2, api 2); `py -3.14 -m pytest` 1 passed. pytest **9.1.1** (Scripts folder not on PATH — always use `py -3.14 -m pytest`). Python 3.11 still missing locally.
- **Next:** Task 1 — REHAB24-6 license/structure check; no pipeline code until that report exists.

## Template

```
## YYYY-MM-DD — Task / experiment title
- Hypothesis:
- Setup (OS, versions, commit):
- Command:
- Data (id, split, N — never commit files):
- Metrics:
- Result:
- Caveats / UNVERIFIED:
```

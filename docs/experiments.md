# Experiments log

Append-only. Newest entry at the top. Record what was run, on what data, and the outcome. No clinical claims.

---

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

# Decisions log

Append-only. Newest entry at the top. Each entry: date, task, decision, alternatives, trade-off, how to reverse.

---

## 2026-10-23 — Task 1a-4 — Three evidence levels; physio advisor unassigned

- **Decision:** Every threshold or rule has one of three **evidence levels**: (1) **provisional default** — engineering placeholder, demo only; (2) **data-derived** — chosen from REHAB24-6 **training** `person_id`s only and checked on **validation** `person_id`s; still provisional because those subjects are healthy adults in a lab; (3) **clinician-approved** — reviewed by a **named human** physiotherapist. Schema fields: `status` (`provisional`|`approved`), `approvedBy`, `approvedAt`, `provenance` (`default`|`dataset-derived`|`clinician`). Physio advisor is **TBD (unassigned)**. No rule may be `approved` without a named human approver (not the demo seed). UI must show **“Prototype, not clinically approved”** whenever a provisional rule fired. Demos use seed account **Demo Physio (not a real clinician)**. No invented clinician names.
- **Alternatives:** (1) Treat dataset-derived cutoffs as clinical. (2) Allow `approvedBy` = demo seed. (3) Hide provenance from examiners.
- **Trade-off:** Dataset-derived ≠ clinician-approved keeps lab-healthy REHAB24-6 from looking like a home-rehab protocol. The banner is the patient-facing control until G1 (advisor assigned).
- **Reverse:** Drop the three levels only if a named physio replaces this policy in writing.

## 2026-10-23 — Task 1a-3 — Dual license record, named filters, CSV split audit, committed test log

- **Decision:** Record Zenodo **Rights** `cc-by-nc-4.0` and the description’s academic/non-profit noncommercial-research text; follow the **stricter** pair (research-only + cite SISAP 2024). Replace the one-off clean subset with `gt_quality` / `label_quality` / `none` in `filters.py` (cam 17|18). Camera18 view = swap front↔profile after normalizing `side`→`profile`. Audit splits from CSV + frozen `splits.json` only; do not edit the JSON. Sealed-test JSONL lives at `logs/test_access.jsonl` (committed, four fields only).
- **Alternatives:** (1) Treat CC BY-NC 4.0 as sufficient. (2) Keep a cam17-only `clean=` flag. (3) Leave the access log under gitignored `data/cache/`.
- **Trade-off:** Named filters make Camera18 extra-person and label-only subsets explicit for examiners. A committed empty JSONL proves sealing without storing row data.
- **Reverse:** Restore `clean=True` + `data/cache/sealed-test-access.jsonl`; do not reshuffle `ml/splits.json`.
- **UNVERIFIED:** Whether a student GitHub repo of **code only** needs extra permission beyond CC BY-NC + the description text.

## 2026-10-21 — Task 1a — Python 3.14, frozen subject split, stdlib loader

- **Decision:** Standardize the project on **Python 3.14** (local `.venv` 3.14.0 + CI `python-version: '3.14'`). Pin runtime libs from `pip show` in that venv. Keep pytest/jupyter in `ml/requirements-dev.txt`. Split **by `person_id`**, not `video_id`, 6/2/2 with seed `20261021`, lists frozen in `ml/splits.json`. Loader (`ml/qawam_ml/rehab24.py`) uses the stdlib `csv` module (semicolon), constructs paths, applies the stated clean filter, and **refuses the test split** unless `final=True` (JSONL access log). CI installs **pytest only**, not MediaPipe/OpenCV/jupyter (loader tests are synthetic and stdlib).
- **Alternatives:** (1) Stay on 3.11 as the original brief said and maintain a second venv. (2) Re-shuffle splits inside the loader each run. (3) Use pandas in the loader. (4) Install the full ML stack on GitHub Actions now.
- **Trade-off:** 3.14 matches the machine that already imports MediaPipe 1.1.1; fighting back to 3.11 would be unpaid risk. Frozen JSON beats live `random.shuffle` if CPython ever changes the PRNG. Stdlib CSV keeps CI off heavy wheels until Task 1b. Person 10 only exists in Ex3, so train is uneven — that is honest subject-wise splitting, not a bug to “repair” by leaking subjects.
- **Reverse:** Change `ci.yml` + README together; never silently move `test: [7, 9]`.
- **UNVERIFIED:** Whether `actions/setup-python` 3.14 + `opencv-python==5.0.0.93` wheels exist on `ubuntu-latest` (CI currently does not install them). MediaPipe 1.1.1 API vs old `mp.solutions.pose` — Task 1b.

## 2026-10-21 — Task 0 — Monorepo at workspace root

- **Decision:** Treat `Grad_1` as the Qawam repository root (not a nested `qawam/` folder). npm workspaces: `web/` and `api/`. Shared ESLint/Prettier/CI at root. Python lives in `ml/` + `tests/python/` with pytest, not in the npm workspace.
- **Alternatives:** (1) Nested `qawam/` directory matching the brief tree literally. (2) Separate git repos for web/api/ml.
- **Trade-off:** One repo matches a student graduation project and a single CI pipeline. Nested extra folder would fight the existing Cursor workspace path. Multiple repos would make Task 0–6 slower to review.
- **Reverse:** Move folders later; git history can follow with `git mv`.
- **UNVERIFIED:** Node 24 vs “LTS” — confirm on https://nodejs.org. Python 3.11 is specified; this machine currently has 3.14 only.
- **Follow-up:** `web/` uses TypeScript `moduleResolution: bundler` (Vite later). `api/` keeps `NodeNext` and `.js` specifiers. Local npm needed `NODE_OPTIONS=--use-system-ca`; we did not disable TLS verification.

## Template

```
## YYYY-MM-DD — Task N — Title
- Decision:
- Alternatives:
- Trade-off (examiner one-liner):
- Reverse:
```

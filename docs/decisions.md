# Decisions log

Append-only. Newest entry at the top. Each entry: date, task, decision, alternatives, trade-off, how to reverse.

---

## 2026-10-29 — No advisor yet: literature-backed values, synthetic data labelled as such

- **Decision:** Until a named physiotherapist approves, numbers enter packs only as (1) placeholders, (2) dataset-derived values (train subjects, checked on validation), or (3) **literature goals**: a published value with full citation and https link in `literatureGoals`, used as display goals or context, never alone to judge a rep. Synthetic patients, pain notes or sessions may be generated for tests and demos, always marked `synthetic` and never described as clinical data or as advice from a doctor. First literature goal: knee flexion 110 deg (Rowe et al., Gait & Posture 2000).
- **Alternatives:** (1) Fabricate "doctor-approved" thresholds from online advice. (2) Block all rules until an advisor exists.
- **Trade-off:** Keeps the system honest and demo-able; every number can be traced to a dataset split or a paper an examiner can open.
- **Reverse:** A named physiotherapist replaces literature goals with approved rules (`status: approved`, `provenance: clinician`).

## 2026-10-29 — Datasets for the cross-dataset claim

- **Decision:** Add REHAB26-ViewAngles (MediaPipe skeletons, 29 viewing angles, error types), IntelliRehabDS (30 people, Kinect skeletons, CC BY 4.0) and UCOPhyRehab++ (physio quality scores, CC BY 4.0) next to REHAB24-6. KIMORE stays pending (Google Drive folder not listable through the API). Register in `docs/datasets.md`.
- **Trade-off:** Different sensors and labels need one loader per dataset into the pack angle format; the payoff is testing on people, cameras and labs the method never saw.
- **Reverse:** Each dataset is optional; evaluations take a dataset root argument.

## 2026-10-28 — Scope v2: platform of exercise packs, lower limb first

- **Decision:** Qawam targets anyone who needs physiotherapy (post-surgery, athletes, chronic pain, older adults) through versioned **exercise packs** in `rules/packs/` (schema `pack.schema.json`, validator `ml/qawam_ml/packs.py`). The lower-limb pack (squat, lunge, leg abduction; REHAB24-6 Ex6, Ex5, Ex4) is built and validated first; shoulder second. Three research contributions: (1) a confidence gate whose false-cue rate is certified <= alpha on held-out subjects (`ml/qawam_ml/selective.py`), (2) comparison against a physio-recorded personal reference with DTW (`ml/qawam_ml/reference.py`) plus a view-aware setup wizard, (3) Egyptian-dialect pain triage with lexicon OR model. Cut: athlete injury prediction, progression recommender, nudge bandit, engagement layer.
- **Alternatives:** (1) Keep C1–C10 as one scope. (2) Narrow the product to the knee only. (3) Universal clinical thresholds per exercise.
- **Trade-off:** Packs keep the product inclusive while the evidence stays focused. A personal reference removes the dependency on universal thresholds that no advisor has signed. Competitor Limb (UAE, 2026) already offers Arabic camera feedback, so the edge is measured trust and Egyptian fit, not the camera.
- **Reverse:** Packs can be removed one by one; the gate and reference modules do not depend on a specific pack.

## 2026-10-28 — REHAB24-6 joint mapping accepted

- **Decision:** Use the documented hypothesis as the mapping: `LeftArm`→shoulder, `LeftForeArm`→elbow, `LeftHand`→wrist, `LeftUpLeg`→hip, `LeftLeg`→knee, `LeftFoot`→ankle (and Right mirrors). It is now code: `REHAB24_JOINT_FOR_LANDMARK` in `ml/qawam_ml/packs.py`.
- **Alternatives:** (1) Keep it UNVERIFIED until the dataset authors answer. (2) The adjacent-joint or left/right-swapped candidates.
- **Trade-off:** In OptiTrack/BVH-style skeletons a bone's name marks the joint where the bone starts, and the PM_039/PM_101 check already favoured this mapping (1.80% vs 3.85% and 7.14% mean normalised distance). Waiting longer blocked every exercise measurement.
- **Reverse:** Change the one dictionary and rerun `ml/eval/angle_eval.py`; every result records the code version.

## 2026-10-28 — Gate calibration: Learn-then-Test with an exact binomial test

- **Decision:** Calibrate the gate threshold on **repetition-level** units (rep x camera x side) from training subjects; for each candidate threshold, test "false-cue rate > alpha" with an exact binomial test at delta / number of candidates (Bonferroni) and keep the most permissive threshold that passes. If none passes, the coach always abstains. Report coverage and false-cue rate on validation subjects.
- **Alternatives:** (1) A fixed visibility cut-off (0.5 / 0.7). (2) Conformal risk control on the joint loss P(accept and wrong). (3) Frame-level calibration.
- **Trade-off:** Gives a stated guarantee on the false-cue rate among the cues actually given, which is the quantity a patient experiences. Frames inside one rep are not exchangeable, so units are reps. Subjects still differ, so the guarantee is checked on validation subjects and must be recalibrated for home recordings.
- **Reverse:** `selective.py` keeps `risk_coverage_curve` and `apply_threshold`, so a fixed cut-off can be compared or restored.

## 2026-10-28 — Evaluation runs on the laptop that holds the data

- **Decision:** `ml/eval/angle_eval.py` runs locally next to `data/raw/rehab24-6/`; only derived CSV/JSON summaries leave the machine.
- **Alternatives:** Upload videos to a cloud workspace.
- **Trade-off:** Respects the dataset's research-only terms and avoids moving ~2.6 GB of video.
- **Reverse:** None needed.

## 2026-10-24 — Align web dev server with Vite 8 toolchain

- **Decision:** Align the web workspace's Vite version with the Vite 8 version resolved by Vitest and the installed React plugin after live browser verification found the previous mixed-version setup failed during React refresh.
- **Alternatives:** (1) Pin the React plugin and Vitest to a Vite 7-compatible set. (2) Keep the versions mixed and rely only on production builds.
- **Trade-off:** A consistent toolchain restores local development and interactive manual testing; the web production build and full tests were rerun after the change.
- **Reverse:** Revert together with tested compatible versions if the repository later standardizes all workspaces on a supported Vite 7 toolchain.

## 2026-10-24 — Pain-text detector ships without a lexicon

- **Decision:** Implement Arabic normalization and the deterministic lexicon-OR-model contract, but ship no red-flag phrases. A configured lexicon hit is never suppressible by a model; empty input or absent lexicon is `CANNOT_ASSESS`; a no-match result is explicitly not a safety clearance.
- **Alternatives:** (1) Hardcode a short unreviewed Arabic red-flag list. (2) Let an NLP model classify pain text without a deterministic override.
- **Trade-off:** The safety invariant and text normalization can be tested without pretending translations or recall are clinically adequate. The helper is inert until a reviewed lexicon and pathway are supplied.
- **Reverse:** Add terms only with documented provenance and qualified review; preserve lexicon OR model semantics and the no-match caveat.

## 2026-10-24 — Browser capture gate is caller-configured

- **Decision:** Add a TypeScript visibility gate in the browser runtime and require the rule evaluator to consume its explicit result. Required landmark names and cutoff are caller inputs with no bundled exercise defaults.
- **Alternatives:** (1) Trust the caller to set a ready flag without a reusable gate. (2) Add a guessed anatomical mapping and threshold now.
- **Trade-off:** This makes the intended fail-closed handoff executable and testable in the frontend language while keeping the actual clinical configuration blocked on evidence. The Python and TypeScript helpers are parallel runtime implementations, not a shared cross-language module.
- **Reverse:** Replace or adapt the helper when real pose output and authoritative landmark correspondence are available; preserve the no-cue-on-failed-capture invariant.

## 2026-10-24 — Generic rule evaluation without bundled exercise rules

- **Decision:** Implement deterministic rule matching as a pure TypeScript helper, but require every rule and metric to be supplied by a caller. Failed capture or a missing required metric produces `CANNOT_ASSESS`; provisional matches carry an explicit warning flag. Do not bundle exercise thresholds or connect the helper to the mock UI.
- **Alternatives:** (1) Hardcode illustrative exercise rules and present resulting cues. (2) Wait to implement any rule infrastructure until a clinician is assigned.
- **Trade-off:** The core behavior can be unit-tested now without making up clinical decisions. The evaluator does not itself validate a clinician's identity; its approval metadata checks are consistency guards only.
- **Reverse:** Add exercise rules only when their metric definitions, thresholds, and evidence provenance are documented; clinician approval requires a real named physiotherapist.

## 2026-10-24 — Synthetic session summary; positive-only engagement

- **Decision:** Add a visible mock session summary to demonstrate the intended rep-count/summary surface, explicitly label every value and movement description as simulated, and state that no video was analyzed and form was not assessed. Keep rewards positive-only: reward completing the plan/check-in and, only when measurable, quality—not raw rep totals or low pain. No punishment, lost points, shame language, or streak resets.
- **Alternatives:** (1) Present mock values as model output. (2) Penalize missed sessions or low-quality movement. (3) Reward high rep count as a proxy for progress.
- **Trade-off:** A clearly synthetic result makes the UI discussable without suggesting clinical validity. Positive reinforcement supports engagement without pressuring users to exercise through pain or conceal symptoms.
- **Reverse:** Replace the mock only with real, traceable model output after the exercise pipeline is integrated and evaluated; do not introduce punitive mechanics. A future points policy should be separately simulated and tested before UI integration.

## 2026-10-24 — No simulated clinician approval

- **Decision:** Clinical review is deferred until a real, named physiotherapist is available. Demo outputs may use synthetic examples only when clearly labeled as simulated; they must never be attributed to a doctor or represented as approval. Show a bilingual educational-prototype disclaimer on the first screen.
- **Alternatives:** (1) Present fabricated decisions as if authored by a clinician. (2) Hide demo provenance until an advisor is assigned. (3) Block all interface work until clinical review.
- **Trade-off:** Synthetic fixtures allow safe UI engineering and demonstrations, while explicit provenance avoids misleading users or examiners. The disclaimer does not make the prototype suitable for clinical use.
- **Reverse:** Change only after an actual named physiotherapist reviews the specific rules and there is a documented approval process; do not retroactively relabel synthetic examples as clinician-authored.

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

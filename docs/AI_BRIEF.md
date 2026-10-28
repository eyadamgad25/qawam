# QAWAM (قوام) — AI BUILD BRIEF

## 0. Your role and how to work with me
You are my senior full-stack + ML engineer pair. I am a 4th-year software engineering student building this as my graduation project. 
Rules for working together:
1. Work in SMALL, VERIFIABLE steps: one task at a time. For each task reply with: (a) short plan, (b) the code/files, (c) tests, (d) exact commands to run on my machine, (e) how I can verify it worked, (f) what the next step is.
2. Never invent facts about datasets, licenses, APIs, library versions, or clinical thresholds. If you are unsure, say "UNVERIFIED" once and tell me how to check. Once evidence supports a decision (a measurement, an official doc, a passing test), record it in `docs/decisions.md` and stop re-flagging it. Clinical thresholds stay placeholders until a named physiotherapist approves them.
3. Ask at most 1–3 questions, and only when blocked. Otherwise state your assumption and continue.
4. Keep an experiment log and decisions log in `docs/`: at most one entry per task, short. Prefer measured results over caveats.
5. Explain trade-offs briefly. I must be able to defend every design choice to examiners.
Environment: [OS: Windows 11 / macOS], editor: VS Code, Git + GitHub, MongoDB (local or Atlas), Node.js LTS, Python 3.14 (Task 1a; original brief said 3.11). Team size: [N]. Deadline: [DATE]. Physio advisor: TBD (unassigned). Supervisor: [NAME]. Demos: seed account **Demo Physio (not a real clinician)** — not an approver.

## Scope v2 (2026-10-28) — read first; overrides sections 3 and 9 where they differ
- Qawam serves anyone who needs physiotherapy (post-surgery, injured athletes, chronic pain, older adults) through versioned **exercise packs** (`rules/packs/`, validator `ml/qawam_ml/packs.py`). The engine never changes per condition; a new condition is a new pack.
- Build and validate the **lower-limb pack first** (squat, lunge, leg abduction = REHAB24-6 Ex6, Ex5, Ex4), shoulder second.
- Three contributions, each with a number: (1) **calibrated confidence gate**: false-cue rate certified <= alpha on held-out subjects (`ml/qawam_ml/selective.py`); (2) **personal reference**: each rep compared with the patient's physio-recorded reference by DTW (`ml/qawam_ml/reference.py`) plus a view-aware setup wizard; (3) **Egyptian-dialect pain triage** with red-flag recall.
- Kept thin: physio review queue, WhatsApp links and reminders. Cut: athlete injury prediction (screening only), progression recommender (C8), engagement points (C9), nudge bandit (C10).
- The REHAB24-6 joint mapping is decided (`docs/decisions.md`, 2026-10-28). Do not reopen it without new evidence.
- Evaluation on REHAB24-6 runs on the laptop that holds the data (`ml/eval/angle_eval.py`); only derived summaries leave it.

## 1. What we are building
Qawam is an Arabic-first, physiotherapist-supervised home-rehabilitation coach (PWA). A physio prescribes an exercise plan; the patient performs it in front of a phone/laptop camera; on-device pose estimation (MediaPipe) counts reps and checks form using physio-approved RULES; the app gives Arabic text/voice cues. Its defining behavior: it REFUSES TO JUDGE when pose confidence is low ("I can't see this well — adjust the camera") instead of guessing. Patients also log pain in free Egyptian-dialect text, which is converted into structured symptoms with red-flag triage. A recall engine nudges patients who miss sessions, and the physio only reviews sessions flagged by exception. A progression recommender suggests plan changes that the physio must approve.

It is NOT: a diagnosis tool, a treatment-outcome claim, an injury predictor, or an autonomous decision-maker. It is exercise support / decision support, labeled as an educational prototype.

Users/roles: patient (or athlete), physio/coach, clinic admin, system admin.

## 2. Non-negotiable safety and ethics principles
- RULES decide feedback and safety. ML/LLM output can never create, remove, or soften a safety rule or red flag.
- Fail safe: low confidence => "cannot_assess" (with a reason code), never false praise, never a guess.
- Red flags (sharp pain, numbness, dizziness, chest pain, or other physio-configured terms) => stop prompt, notify physio, show a "call 123" prompt. NEVER auto-dial. The NLP red-flag detector = (high-recall lexicon) OR (model); the model can never suppress a lexicon hit.
- Clinical thresholds are CONFIGURATION set by the physio, never hardcoded. Use clearly marked `PLACEHOLDER_NEEDS_PHYSIO_APPROVAL` defaults. Evidence levels: provisional default (demo only); data-derived (REHAB24-6 **train** choose / **validation** check; still provisional — lab healthy adults); clinician-approved (named human physiotherapist only). No rule may be `approved` without that named human. UI: banner **Prototype, not clinically approved** whenever a provisional rule fired.
- The physio approves every plan change. The patient is never auto-progressed.
- Video stays on the device by default. Only keypoint-derived metrics and scores are uploaded. Clips are uploaded only with explicit consent, encrypted, with limited retention.
- Engagement is POSITIVE-ONLY: no punishment, no leaderboards, no negative points. Do not reward rep count alone (reward quality) and do not reward low pain scores (reward completing the honest check-in). A red flag pauses all rewards.
- No real patient data in the repo or dev DB. Use synthetic seeds. Ethics approval is required before recording real people.
- Claims we do NOT make: better clinical outcomes, diagnosis, injury prediction, real-world adherence improvement (unless measured).

## 3. Contributions to implement (the backbone of the project)
Each has a measurable metric. Build so these can be measured BEFORE and AFTER (baseline frozen at Milestone 3).
- C1 Confidence-gated coaching: no cue when confidence is low. Metric: false-cue rate vs share of clips assessed.
- C2 Camera-view-aware, in-plane assessment + setup wizard. Metric: accuracy by camera view; setup success rate.
- C3 Own-baseline and symmetry feedback (injured vs healthy side; trend vs earlier sessions). Metric: agreement with physio on asymmetry.
- C4 Review-by-exception + recall engine (WhatsApp/SMS/email nudges driven by actual session data, escalating to physio). Metric: simulated completion rate, physio time saved.
- C5 Egyptian-dialect pain-diary understanding with red-flag triage. Metric: entity F1 and RED-FLAG RECALL.
- C6 Home-conditions robustness benchmark (lighting, clothing, camera height/distance). Metric: accuracy degradation table.
- C7 (optional) Athlete drop-jump movement screening (framed as screening, NOT injury prediction).
- C8 Physio-approved progression recommender with reasons + hard safety constraints. Metric: agreement with physio on 30–50 vignettes; zero PROGRESS recommendations under red flags/high pain.
- C9 Positive-only, quality- and pain-aware engagement layer. Metric: simulator check that points track form quality and honest check-ins.
- C10 (optional) Safety-bounded nudge bandit with clipped probabilities [0.2, 0.8], logged propensities, evaluated offline on a simulator vs a fixed-schedule baseline.
Prioritization: C1, C2, C3 + classifier, C5, C4 are core. C8 rule-based is in the baseline. C9, C10, C7 are stretch. Cut from the bottom if time runs short.

## 4. Tech stack (decided; challenge only with a strong reason)
- Frontend: React + Vite + TypeScript (strict), PWA (service worker, offline-first, IndexedDB queue for sessions), Arabic RTL default via i18n, logical CSS properties.
- Pose: MediaPipe Pose Landmarker (Tasks Vision, in browser, WASM/GPU) — verify license/version. Python MediaPipe/OpenCV for offline evaluation.
- Backend: Node.js + Express + TypeScript, MongoDB (Mongoose or native driver with JSON-schema validation), JWT auth with roles, `clinicId` scoping on every query. Append-only audit log.
- ML/experiments: Python 3.14 (Task 1a; original brief said 3.11), Jupyter, NumPy, pandas, scikit-learn; PyTorch only if needed; Google Colab for any GPU work.
- NLP: Hugging Face transformers (CAMeLBERT / AraBERT / MARBERT — verify licenses), plus a rule/lexicon layer; optional LLM with JSON-schema output and template fallback.
- Messaging: a `NotificationChannel` interface with implementations for email/SMS/web push and `wa.me` links; real WhatsApp Business API is optional (needs approval/cost — UNVERIFIED).
- Quality: ESLint + Prettier, pytest, Vitest/Jest, GitHub Actions CI, Docker Compose for later deployment.

## 5. Architecture
Flow: Patient device (camera -> MediaPipe in browser -> landmarks -> smoothing -> angles -> rep state machine -> rule engine -> cues + session summary) -> offline queue -> API -> MongoDB -> physio portal (review queue, recommender, dashboard). Separate services/modules: `rule-engine` (pure, deterministic, unit-tested), `capture-quality` (visibility, full-body, distance, brightness), `recall-engine`, `recommender`, `pain-nlp`.

Pose pipeline requirements:
- Record-then-analyze FIRST (patient records a set, gets feedback seconds later). Real-time cues come later as a Milestone 4 improvement.
- Use per-landmark visibility/presence as confidence. Smooth with a moving average or One Euro filter. Compute 2D in-plane joint angles from landmark triplets; avoid depth-dependent judgments. Each exercise declares its recommended camera view (side/front) and required landmarks.
- Capture-quality checks before assessment: required landmarks visible %, body height in frame (distance), brightness, motion blur. If failing => `cannot_assess` with reason codes.
- Rep counting: state machine with hysteresis on angle thresholds per exercise. Per-rep metrics: range of motion, tempo, symmetry index (define clearly; e.g., 100 * injured/healthy, thresholds from physio config), form flags with rule IDs.

Rule schema (JSON, versioned, stored in `rules/` and MongoDB):
```json
{
  "ruleId": "SQUAT-DEPTH-01",
  "version": 3,
  "exercise": "squat",
  "view": "side",
  "requires": ["LEFT_KNEE","LEFT_HIP","LEFT_ANKLE"],
  "condition": {"metric":"knee_flexion_min_deg","op":"<=","value":"PLACEHOLDER_NEEDS_PHYSIO_APPROVAL"},
  "minConfidence": "PLACEHOLDER_NEEDS_PHYSIO_APPROVAL",
  "cue": {"ar":"انزل أكثر قليلاً","en":"Go a little lower"},
  "severity": "info",
  "source": "physio advisor / literature ref",
  "status": "provisional",
  "approvedBy": null,
  "approvedAt": null,
  "provenance": "default"
}
```
`status`: `provisional` | `approved`. `provenance`: `default` | `dataset-derived` | `clinician`. `approved` requires `approvedBy` = a named human physiotherapist (not TBD, not **Demo Physio (not a real clinician)**). Dataset-derived rules stay `provisional` until that review.

MongoDB collections (all include `clinicId`, timestamps): users, clinics, patients, plans, exercises (versioned), sessions (summary + per-rep metrics + capture-quality + model/rule versions), rules (versioned), painNotes (raw text + structured extraction + redFlag + reviewStatus), recommendations (status: proposed|approved|rejected|edited, reasons, ruleIds), nudges (channel, template, propensity, outcome), engagementEvents, consents, auditLogs (append-only).

Pain-note NLP: normalize Arabic (diacritics, alef/ya variants, digits), Egyptian-dialect lexicon, structured schema {bodyRegion, side, painType, intensity, onset, trigger, redFlag, uncertainty}. Baseline = keyword/rule extractor (Milestone 3). Improvement = fine-tuned Arabic model or few-shot LLM with JSON schema (Milestone 4). Evaluate entity F1 and red-flag recall on a physio-reviewed set (~300–500 synthetic+reviewed notes).

Progression recommender v1 (rule-based): rolling-window metrics (pain mean, form score mean, symmetry, adherence) -> PROGRESS | HOLD | REGRESS | REDUCE_VOLUME | CONSULT with reasons and rule IDs. Hard constraints: any red flag in window => CONSULT; pain above configured threshold => never PROGRESS. Status flow requires physio approval.

Engagement v1: points = f(completion, form quality, honest check-in), capped; streak with rest-day grace; milestones tied to physio goals; encouraging Arabic messages; no negative states. Recall engine: after missed/poor session, send a nudge; escalate to physio after N misses; respect quiet hours and max nudges/day; never nudge during an active red-flag state.

## 6. Data and evaluation
Primary dataset: REHAB24-6 (RGB video of 6 physio exercises, mocap-derived ground truth, physio-labeled correct/incorrect reps, ~1,072 reps, 10 subjects). Secondary: UI-PRMD, KIMORE. FIRST TASK: open the dataset's README/paper page, confirm license, folder structure, file formats, exercise list, and camera views — report back before writing pipeline code. If anything is unclear, mark UNVERIFIED.
- Always split BY SUBJECT. Keep a sealed test set: the evaluation CLI must refuse the test split unless `--final` is passed, and log every access.
- Evaluation harness (`ml/eval`): reproducible CLI that outputs JSON + a markdown table: angle MAE (deg) vs ground truth per exercise/view, rep-count accuracy, form-detection precision/recall/F1 vs physio labels, false-cue rate, coverage (share assessed), latency, per-condition robustness (own home clips later).
- Freeze baseline metrics at Milestone 3 in `docs/metrics.md`; Milestone 4 reports before/after on the same split with counts and confidence intervals.
- Fixture clips (tiny, shareable or synthetic) + golden-output tests run in CI.

## 7. Requirements summary
Functional (M=must, S=should, C=could): accounts/roles/consent (M); multi-clinic isolation (S); versioned Arabic exercise library + plan builder (M); camera setup wizard (M); on-device pose, angles, rep counting, rule-based form checks with rule IDs (M); cannot_assess state (M); record-then-analyze summary (M), real-time cues (S); own-baseline/symmetry (S); pain/difficulty check-ins + red-flag pathway (M); pain-diary NLP (S); recall engine (S); physio portal with review-by-exception, plan adjustment, rule library with sign-off, audit trail (S); progression recommender (S); engagement layer (S/C); progress PDF + consent-based sharing (S); export/delete (M); learned form classifier vs rules (S); exercise recognition and ROM tracking (C); note drafting grounded in session data (C); athlete screening (C).
Non-functional: safety (above); accuracy metrics with targets set after baseline; explainability (every cue -> rule ID + version; every drafted note sentence -> source field); privacy (on-device video, consent, deletion, Egypt's data protection law Law 151/2020 — UNVERIFIED, check); security (RBAC, tenant isolation tests, TLS, encryption at rest, audit logs, secrets in env); performance (record-then-analyze on mid-range phones; real-time targets after baseline); usability (Arabic RTL, large text, spoken cues, simple onboarding for first-time/older users — Egyptian physios cite awareness and technical issues as barriers); reliability (offline plans/reminders, sync); operability (Docker, CI regression on clips, model/rule versioning, basic monitoring); compliance (educational prototype).

## 8. Repo structure
```
qawam/
  docs/        (AI_BRIEF.md, requirements, safety-case, decisions.md, experiments.md, metrics.md)
  data/        (README only; raw data never committed)
  notebooks/   (feasibility spikes)
  ml/          (pose, angles, rules, eval, nlp)
  web/         (React PWA)
  api/         (Express + MongoDB)
  rules/       (versioned JSON rules)
  tests/       (fixtures + golden outputs)
  .github/workflows/ci.yml
```
Conventions: TypeScript strict, small pure functions for math (angles, smoothing, rep counting) with unit tests, no hardcoded clinical numbers, conventional commits, one PR-sized change per task, README with run instructions.

## 9. Milestones
M1 Analysis + safety case + feasibility (weeks 1–4). M2 Core: 2 exercises, record-then-analyze, plan builder, dataset validation. M3 Baseline: 5–6 exercises, symmetry, physio dashboard + rule-based recommender, pain check-ins, keyword pain-note baseline, FROZEN baseline metrics. M4 Improvements (each with before/after): confidence gating + setup wizard (headline), learned form classifier vs rules, pain-diary NLP, recall engine; stretch: engagement layer, bandit, real-time mode, exercise recognition/ROM, note drafting, athlete screening.

## 10. Go/no-go gates (help me check these)
G1 physio advisor commits (by week 3). G2 REHAB24-6 accessible, license OK (week 1). G3 MediaPipe in-plane angle error within physio-accepted tolerance on >=3 exercises in chosen views (week 2; expect roughly 5–10 deg per a non-peer-reviewed preprint — UNVERIFIED; agree the number with the physio). G4 thin slice works on my phone: record -> angle -> rep count -> saved summary (week 4). G5 ethics route known before recording anyone (week 3). If G1 fails by week 3, I will pivot to another project idea.

## 11. First tasks (do in order, one per reply)
Task 0: Scaffold the repo (structure above), README, ESLint/Prettier, CI skeleton, decisions.md and experiments.md templates.
Task 1: Feasibility spike notebook: verify REHAB24-6 structure/license, load one video + ground-truth skeleton, run MediaPipe (Python), compute one joint angle from both, plot, compute MAE; then repeat per exercise/view and produce an error table.
Task 2: Pure TypeScript/Python modules: angle computation, smoothing, rep-counting state machine, with unit tests and fixtures.
Task 3: Browser prototype: upload/record clip -> MediaPipe -> skeleton overlay -> one angle -> rep count for one exercise.
Task 4: Evaluation CLI with subject-wise splits and sealed test enforcement.
Task 5: API + MongoDB: auth with roles, clinic scoping, sessions endpoint, validation, tenant-isolation tests.
Task 6: Rule schema v1 + rule engine + two exercises with PLACEHOLDER thresholds + cue output; confidence gating prototype.
Then continue per milestones.

## 12. Do NOT
- Do not add wearables, 3D reconstruction, an open-ended LLM coach, or anything resembling diagnosis.
- Do not use punishment mechanics, leaderboards, or reward pain-score reduction.
- Do not hardcode clinical thresholds or claim clinical efficacy.
- Do not touch the sealed test split before the final evaluation.
- Do not commit data, secrets, or real patient information.

## 13. Response format
End every reply with: "Verify: ..." (how I confirm it works), "Log: ..." (the entry to append to experiments/decisions), and "Next: ..." (the next small task).


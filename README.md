# Qawam (قوام)

Arabic-first, physiotherapist-supervised **home-rehabilitation coach** (PWA). Educational prototype — not a diagnostic or treatment-outcome product.

A physio prescribes an exercise plan. The patient records a set in front of a camera. On-device pose estimation counts reps and checks form using **physio-approved rules**. The app gives Arabic text/voice cues. If pose confidence is low, Qawam **refuses to judge** instead of guessing.

## What this is / is not

| Is | Is not |
| --- | --- |
| Exercise support and decision support | Diagnosis, injury prediction, autonomous treatment |
| Rule-gated cues with `cannot_assess` | Guessing form when the camera is bad |
| Physio must approve every plan change | Auto-progression of the patient |

Safety principles (non-negotiable): `docs/safety-case.md`. Full brief: `docs/AI_BRIEF.md`.

## Repo layout

```
docs/         product brief, decisions, experiments, metrics, safety case
data/         README only — raw videos/skeletons are never committed
notebooks/    feasibility spikes
ml/           pose, angles, rules, eval, nlp (Python)
web/          React + Vite + TypeScript PWA (Task 3+)
api/          Express + MongoDB (Task 5+)
rules/        versioned JSON exercise rules
tests/        fixtures, golden outputs, Python/JS tests
.github/      CI
```

## Prerequisites

- Node.js **20+** (this machine currently has 24.18.1; whether that is the current LTS is **UNVERIFIED** — check [nodejs.org](https://nodejs.org))
- Python **3.14** for ML/eval (matches this machine’s `.venv` and CI). The original brief said 3.11; that was changed in Task 1a.
- Git
- MongoDB local or Atlas — not required until Task 5

## Commands

If `npm install` fails with `UNABLE_TO_VERIFY_LEAF_SIGNATURE` (common with TLS-inspecting proxies), retry in PowerShell with Node's system CA store — do **not** set `strict-ssl=false`:

```powershell
$env:NODE_OPTIONS = '--use-system-ca'
npm install
```

```bash
# from repo root
npm install
npm run typecheck
npm run lint
npm run format:check
npm test
```

Python (PowerShell, from repo root):

```powershell
.\.venv\Scripts\python.exe -m pip install -r ml/requirements.txt -r ml/requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

Dataset files live in `data/raw/rehab24-6/` and are gitignored. License and layout: `docs/dataset-report.md`.

## Status

Task 1a: dataset report + sealed subject-wise loader. No MediaPipe evaluation yet.

## License

Undecided. Treat as a private educational project until a license is chosen. Do not assume third-party dataset licenses from this file — see `data/README.md`.

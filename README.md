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
- Python **3.11** for ML/eval (CI uses 3.11). This machine currently reports **Python 3.14 only** — install 3.11 before Task 1
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

Python (after installing 3.11 and creating a venv — recommended):

```bash
py -3.11 -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
python -m pip install -r ml/requirements-dev.txt
python -m pytest
```

If 3.11 is not installed, GitHub Actions still runs pytest on 3.11. Local pytest on 3.14 is **UNVERIFIED**.

## Status

Task 0 (scaffold) only. No pose pipeline, no API, no PWA yet.

## License

Undecided. Treat as a private educational project until a license is chosen. Do not assume third-party dataset licenses from this file — see `data/README.md`.

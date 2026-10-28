# Qawam (قوام)

Arabic-first, physiotherapist-supervised **home-rehabilitation coach** (PWA). Educational prototype — not a diagnostic or treatment-outcome product.

The long-term product goal is physiotherapist-supervised home rehabilitation. The current educational prototype can overlay MediaPipe pose landmarks on a selected local video and includes an experimental arm-raise counter. Its landmark mapping and thresholds are unvalidated test assumptions; it does not assess form or provide treatment advice.

## What this is / is not

| Is | Is not |
| --- | --- |
| Local pose overlay and explicitly experimental counter | Diagnosis, injury prediction, autonomous treatment |
| Test-only landmark/threshold details shown in the UI | Validated repetition counts or form assessment |
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

- Node.js **22.12+** (Vitest 5 requires it) (this machine currently has 24.18.1; whether that is the current LTS is **UNVERIFIED** — check [nodejs.org](https://nodejs.org))
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
npm run dev --workspace web
```

The last command starts the web prototype in Vite; open the local URL printed
in the terminal. To run this worktree's version without accidentally opening
an older app already using the default port, use:

```bash
npm run dev:demo
```

Open the exact URL Vite prints in the terminal (it may choose a higher port
if 5174 is already in use). In Visual Studio Code, first open this worktree's
folder, not another checkout:
`C:\Users\eyada\copilot-worktrees\Grad_1\eyadamgad25-silver-telegram`.
On the page, select a short local video and choose **بدء تحليل الوضعية** to see
MediaPipe landmarks over playback. The clip is processed in the browser and
not uploaded; starting analysis requires downloading MediaPipe's WASM/model
from public CDNs. Videos longer than two minutes are rejected. The experimental
counter attempts one complete arm raise and return using the displayed
MediaPipe landmarks and provisional thresholds; the displayed target of 8 is
only a test target, not a prescription or a fabricated count. The mapping and
thresholds have not been clinically or dataset validated. It does not assess
form. While it runs, compare the tracked side, estimated angle, and minimum
landmark visibility between front-facing and side-facing recordings; choose
automatic, the person's left, or the person's right arm. Changing the choice
resets the experimental count. The
separate session examples remain simulations. When the clip ends, the page
shows an unsaved, in-page summary of the count detected and clip duration;
optionally enter your own manually observed repetition count beforehand to see
the absolute count difference. This manual comparison is a test aid, not a
validated benchmark. Replay the video to run the counter again.

Python (PowerShell, from repo root):

```powershell
.\.venv\Scripts\python.exe -m pip install -r ml/requirements.txt -r ml/requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

Dataset files live in `data/raw/rehab24-6/` and are gitignored. License and layout: `docs/dataset-report.md`.

## Status

Current state: dataset/split safeguards and exploratory pose evaluation are in place; the browser can overlay MediaPipe landmarks and run a visibly labeled experimental arm-raise counter with synthetic unit tests. There is not yet a validated exercise mapping, threshold set, form assessment, clinician-approved rule set, or clinical validation.

## License

Undecided. Treat as a private educational project until a license is chosen. Do not assume third-party dataset licenses from this file — see `data/README.md`.

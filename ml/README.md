# ml/

Python **3.14** (CI + local `.venv`). Runtime pins: `requirements.txt`. pytest/jupyter: `requirements-dev.txt`.

- `qawam_ml/rehab24.py` — REHAB24-6 CSV loader, named filters, sealed test split
- `qawam_ml/filters.py` — `none` / `gt_quality` / `label_quality`, Camera18 view swap
- `qawam_ml/angles.py` — generic 2D angle geometry; no joint mapping or clinical thresholds
- `qawam_ml/smoothing.py` — causal trailing moving average; caller chooses the window
- `qawam_ml/repetitions.py` — configurable low/high hysteresis counter; no threshold defaults
- `qawam_ml/capture_quality.py` — required-landmark visibility gate; caller supplies landmarks and cutoff
- `qawam_ml/angle_pipeline.py` — composes the configurable gate, angle, smoothing, and rep counter
- `splits.json` — frozen subject-wise 6/2/2 on `person_id`
- `spike/overlay_check.py` — train-only GT overlay (Task 1b-A; no MediaPipe)
- `spike/mediapipe_check.py` — train-only single-frame MediaPipe feasibility check
- `spike/angle_check.py` — sampled angle comparisons: Ex1 elbow/Camera17 front and Ex5–Ex6 knee/Camera18 profile; accepts train or validation only
- `spike/view_robustness_check.py` — balanced MediaPipe detection and 2D joint comparison across front/half-profile/profile views for Ex1/Ex5/Ex6; accepts train or validation only
- `pose/` — MediaPipe offline (Task 1b+)
- `eval/` — evaluation CLI (Task 4; sealing already starts in the loader)

```powershell
.\.venv\Scripts\python.exe -m pip install -r ml/requirements.txt -r ml/requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

## Task 1b reproduction (PowerShell, from repository root)

**MUST:** Keep the test split sealed. The loader selects only `train` rows.
Download the official MediaPipe Lite task model once if it is missing; it stays
local under ignored `data/derived/` and must not be committed. Verify its hash:

```powershell
if (-not (Test-Path data\derived\models\pose_landmarker_lite.task)) {
  New-Item -ItemType Directory -Force data\derived\models | Out-Null
  curl.exe -L --fail --silent --show-error `
    https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task `
    -o data\derived\models\pose_landmarker_lite.task
  if ($LASTEXITCODE -ne 0) { throw "MediaPipe model download failed" }
}
$expected = "59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a"
$actual = (Get-FileHash data\derived\models\pose_landmarker_lite.task -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $expected) { throw "MediaPipe model SHA-256 mismatch" }
$env:PYTHONPATH = "ml"

# MUST, if reproducing the completed checks: GT overlay, then pose check, then multi-repetition angle checks.
.\.venv\Scripts\python.exe ml\spike\overlay_check.py
.\.venv\Scripts\python.exe ml\spike\mediapipe_check.py
.\.venv\Scripts\python.exe ml\spike\angle_check.py
.\.venv\Scripts\python.exe ml\spike\angle_check.py --exercise 5
.\.venv\Scripts\python.exe ml\spike\angle_check.py --exercise 1
.\.venv\Scripts\python.exe ml\spike\view_robustness_check.py

# SHOULD: run once after the training method is fixed; do not tune on this small validation sample.
.\.venv\Scripts\python.exe ml\spike\angle_check.py --split validation
.\.venv\Scripts\python.exe ml\spike\angle_check.py --split validation --exercise 5
.\.venv\Scripts\python.exe ml\spike\angle_check.py --split validation --exercise 1
.\.venv\Scripts\python.exe ml\spike\view_robustness_check.py --split validation

# SHOULD, especially after code changes:
.\.venv\Scripts\python.exe -m pytest tests\python
```

**MAY:** Inspect PNGs under `data\derived\overlay\` and
`data\derived\mediapipe\`, and angle CSVs under `data\derived\angles\`.
Angle outputs are named `{train|validation}_ex{5|6}_cam18_knee_angles.csv`.
View comparison CSVs are saved under `data\derived\view-robustness\`; the
script caps sampling at five repetitions per subject/exercise/camera-view and
five frames per repetition. The dataset is for academic or non-profit
non-commercial research; contact its authors for commercial use. These ignored
files are local outputs, not inputs to commit. Dataset-to-model mapping,
Camera18 alignment, generalization beyond the small sample, and the model's
specific license remain **UNVERIFIED**; do not interpret this spike clinically.
The angle and view-comparison scripts accept only `train` or `validation`;
test is intentionally unavailable.

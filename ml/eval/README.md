# ml/eval

Evaluation CLI lands in Task 4. Sealed test enforcement already lives in `qawam_ml.rehab24.load_repetitions(..., final=True)` (Task 1a). The CLI must pass `final` only with `--final` and must not add a back door.

`audit_splits.py` (Task 1a-3, pandas, not CI) reads `Segmentation.csv` + `ml/splits.json` only and writes `docs/split-audit.md`. It does not open video/npy and does not call `load_repetitions('test')`.

`summarize_view_robustness.py` reads only derived frame CSVs (default:
`data/processed/model-evaluation/train_view_robustness.csv` and
`validation_view_robustness.csv`) and writes `docs/eval-confidence-coverage.md`.
It validates the split label in each input and rejects test rows. Run:

```powershell
py -3.14 ml\eval\summarize_view_robustness.py
py -3.14 -m pytest tests\python\test_view_robustness.py
```

The report also compares exported direct and coordinate-swapped error by
camera/view as a limited coordinate-order diagnostic. It is not a substitute
for a video/keypoint overlay, and it cannot validate image orientation,
coordinate origin, frame synchronization, or joint mapping.

`overlay_camera18_train.py` is a bounded train-only correspondence check,
hard-scoped to the explicitly authorized PM_039 and PM_101 Camera18 videos
and 30 FPS joint arrays. It runs MediaPipe Pose Landmarker Lite on the
approved same-index samples, renders GT vs model landmarks, and prints mean
normalized distance for three explicitly listed candidate mappings by
recording/view and combined. These two recordings do not establish a
canonical mapping. The official model
asset is stored at ignored
`data/derived/overlay/pose_landmarker_lite.task` and is available at
`https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task`.
it does not load other recordings or validation/test assets. PM_101 has a
one-frame total count discrepancy (video 1307; joints 1308); the script warns
about this and only accesses the approved indices 34–36:

```powershell
py -3.14 -m pip install mediapipe==1.1.1
Invoke-WebRequest -Uri "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task" -OutFile "data\derived\overlay\pose_landmarker_lite.task"
py -3.14 ml\eval\overlay_camera18_train.py
```

Candidate distance is exploratory, not a validated landmark mapping or
clinical/model-accuracy metric. See `docs/dataset-report.md`.

## angle_eval.py — full-frame joint-angle baseline (2026-10-28)

Runs MediaPipe Pose Landmarker (VIDEO mode) on every frame of every
`gt_quality` repetition for the chosen exercises, computes each exercise
pack's angles from MediaPipe and from the REHAB24-6 2D skeleton, and calibrates
the confidence gate on train subjects, then applies it to validation subjects.
Test split only with `--final` (logged).

```powershell
py -3.14 ml\eval\angle_eval.py --exercises 6 `
  --dataset-root C:\Users\eyada\Grad_1\data\raw\rehab24-6 `
  --model C:\Users\eyada\Grad_1\data\derived\models\pose_landmarker_lite.task
```

Outputs go to ignored `data/derived/angle-eval/`. `--tolerance-deg` (default 10)
only defines what the evaluation counts as a wrong measurement; it is not a
clinical threshold. `--max-videos 1` gives a quick smoke run.

## reference_eval.py — personal vs universal reference (2026-10-28)

Ground-truth-only comparison of how well DTW to the subject's own correct rep
flags physio-labelled incorrect reps, against a universal template and a
universal depth threshold. No video needed.

```powershell
py -3.14 ml\eval\reference_eval.py --exercises 4 5 6 --dataset-root C:\Users\eyada\Grad_1\data\raw\rehab24-6
```

Writes `data/derived/reference-eval/summary.md`, `summary.json`, `scores.csv`.

## rehab26_eval.py — REHAB26-ViewAngles, by viewing angle and error type (2026-10-29)

```powershell
py -3.14 ml\eval\rehab26_eval.py --root C:\path\to\rehab26
```

`--root` holds `Segmentation.csv` and the unzipped `jointSequences-mediapipe.zip` under `mp/`. Leave-one-person-out; writes `data/derived/rehab26-eval/`.

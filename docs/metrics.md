# Metrics

Baseline is **not frozen**. Freeze only at Milestone 3, on the sealed protocol in `ml/eval` (Task 4+).

Do not invent targets. Fill cells only from measured runs. Use `PLACEHOLDER_NEEDS_PHYSIO_APPROVAL` for any clinical tolerance.

| Milestone | Split | Exercise | View | Angle MAE (deg) | Rep-count acc. | Form F1 | False-cue rate | Coverage (assessed) | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M3 freeze | — | — | — | — | — | — | — | — | not yet run |

## Exploratory results (not the frozen baseline)

Train / validation subjects only; numbers from `docs/experiments.md` entries dated 2026-10-28 and 2026-10-29.

| Measure | Squat | Lunge | Leg abduction | Shoulder abduction |
| --- | --- | --- | --- | --- |
| MediaPipe Lite angle MAE in declared view, train / val (deg) | 8.6 / 4.7 | 5.8 / 6.0 | 3.7 / 9.0 | — |
| Incorrect-rep AUC, personal reference, REHAB24-6 mocap | 0.79 | 0.85 | 0.68 | — |
| Incorrect-rep AUC, personal reference, REHAB26 MediaPipe (LOPO) | 0.93 | — | — | 0.76 |
| Visibility-only gate at alpha 0.10 | abstains on all reps | abstains | abstains | — |
| Side-view MediaPipe error after one-rep calibration (median, deg) | 3.1 | 4.7 | — | — |
| View rule + one-rep calibration: false cues (wrong / spoken), held-out people | 3 / 88 | 3 / 52 | 1 / 26 | — |
| Same with the Full model instead of Lite | 3 / 88 | 14 / 51 | 2 / 24 | — |

Sealed test split: do not access until `--final`. Log every access in `docs/experiments.md`.

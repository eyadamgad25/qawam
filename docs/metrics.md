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

UCOPhyRehab++ (external, physio-scored, motion capture; `docs/experiments.md` 2026-11-03): rep counting MAE 0.56 reps (exact 76%) on the 269 recordings whose measured angle moves, abstained on 124; agreement with the physio's 1-5 score is weak for every method (Spearman 0.14-0.22).

Pain red flags (synthetic Egyptian-Arabic notes, not physio-reviewed; `docs/experiments.md` 2026-11-03): test red flags caught 14 / 40 by the word list, 39 / 40 by word list OR the 58 KB on-device model; false alarms 3 / 19 and 7 / 19. With the temperature rule and negation (all 121 notes): 78 / 81 caught, false alarms 9 / 40.

Fit3D (external, 8 new people, 4 new cameras, Vicon truth; `docs/experiments.md` 2026-11-03), shipped view rule not refitted: knee packs silent on all 608 diagonal-view units (speaking would be wrong on 70%), 0 false cues; shoulder abduction speaks on 74% with false-cue rate 0.34 (95% upper 0.41), above target; learned gate certifies nothing (stays silent).

Sealed test split: do not access until `--final`. Log every access in `docs/experiments.md`.

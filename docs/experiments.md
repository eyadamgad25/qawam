# Experiments log

Append-only. Newest entry at the top. Record what was run, on what data, and the outcome. No clinical claims.

---

## 2026-10-23 — Task 1b-H — Train/validation camera-view robustness comparison

- **Question:** Across front, half-profile, and profile views in Ex1/Ex5/Ex6, how often does MediaPipe Lite detect a pose, and how do selected 2D joints compare with projected GT?
- **Setup:** Added `view_robustness_check.py`. The existing sealed loader selects `gt_quality` independently for each camera. For each subject/exercise/camera/view group, selected the first five repetitions sorted by recording ID and repetition number; sampled five evenly spaced frames per repetition. Reported detection rate, mean visibility, and direct/swapped side-mapping mean keypoint error normalized by frame diagonal. Used Camera18 coordinates as-is. The method was fixed after train, then run once on validation.
- **Command:** `$env:PYTHONPATH='ml'; .\.venv\Scripts\python.exe ml\spike\view_robustness_check.py`; then `.\.venv\Scripts\python.exe ml\spike\view_robustness_check.py --split validation`; checks: `.\.venv\Scripts\python.exe -m pytest tests\python`, `.\.venv\Scripts\python.exe -m py_compile ml\spike\view_robustness_check.py`, and attempted `--split test` (rejected by CLI).
- **Data:** Train: 203 repetitions, 1,015 sampled frames, subjects 3/5/6/8. Validation: 60 repetitions, 300 sampled frames, subject 4. Each split covered 12 exercise-camera-view groups (Ex1/5/6; Camera17 front/half-profile and Camera18 half-profile/profile). No test access.
- **Result:** Pose detected in 1,015/1,015 train frames and 300/300 validation frames across the selected groups. Group mean direct normalized keypoint error ranged from 0.58% to 4.10% of frame diagonal on train and 0.56% to 2.82% on validation; swapped-side errors ranged 2.23%–14.64% and 1.45%–11.40%, respectively. Python tests: 14 passed; script compiled; CLI rejected the sealed test split. Per-frame output is in ignored `data/derived/view-robustness/{train|validation}_view_robustness.csv`.
- **Caveats / UNVERIFIED:** Detection results apply only to capped `gt_quality` repetitions, five frames per rep, and this MediaPipe model; all-sampled-frame detection does not mean continuous video tracking. Validation has one subject. Joint correspondences, anatomical side mapping, Camera18 coordinate alignment, wider camera angles, phone performance, and clinical relevance remain **UNVERIFIED**. No thresholds were selected. MediaPipe emitted its non-fatal rectangular-frame projection warning.

## 2026-10-23 — Browser prototype — two-minute clip limit

- **Question:** Can the prototype accept clips up to two minutes without increasing the fixed inference sample count?
- **Setup:** Raised the duration limit from 60 to 120 seconds in playback-independent analysis validation and its Arabic UI; `sampleTimes` remains capped at 24 frames.
- **Command:** `npm run test:web`, `npm run typecheck`, `npm run build --workspace web`.
- **Data:** No video or dataset split used.
- **Result:** A two-minute clip is within the configured limit; the angle-summary path still samples at most 24 frames across the clip. The supplied REHAB24-6 sample at 126.77 seconds remains over the limit.
- **Caveats / UNVERIFIED:** The fixed 24 samples become farther apart on longer clips. This limit improves usability but does not establish that every movement phase is captured.

## 2026-10-23 — Browser prototype — live playback pose overlay

- **Question:** Does the skeleton update during playback on a short, side-facing clip, rather than staying on one sampled frame?
- **Setup:** Added a separate MediaPipe VIDEO-mode landmarker that runs locally during playback, throttled to at most one inference every 150 ms. Pausing stops the loop; seeking clears the old overlay. The existing analysis button remains a separate 24-frame IMAGE-mode pass.
- **Command:** Selected the user-supplied local clip in the browser, pressed play, and inspected the overlay at multiple playback times.
- **Data:** One 43.07-second, 678×568 clip; no dataset split used.
- **Result:** Playback inference ran without an error. A side-facing pose was drawn at about 4 and 7 seconds, was not detected at a later sampled moment, and was detected again later in the clip. The overlay therefore updates with playback but is intermittent on this clip; this does not establish accuracy or reliable tracking across camera angles.
- **Caveats / UNVERIFIED:** Only one clip and viewpoint were tried; no frontal-versus-diagonal-versus-side benchmark, frame-to-frame landmark error, or device-performance study was performed. Camera/viewpoint, lighting, distance, occlusion, and motion effects remain **UNVERIFIED**. No clinical conclusions.

## 2026-10-23 — Browser prototype — short-clip end-to-end smoke

- **Question:** Does a real short local clip complete inference, and does the pose overlay stay aligned with the displayed video?
- **Setup:** Local Vite/browser preview using one user-supplied clip (43.07 seconds, 678×568); MediaPipe Lite and WASM served locally. No dataset split used.
- **Command:** Selected the clip in the browser and pressed **حلّل المقطع**; checked the rendered video/canvas geometry and playback behavior in the browser.
- **Data:** 24 sampled frames; 13 had detected poses. The clip remained local.
- **Result:** Inference completed and showed the pose and angle summary. Visual inspection found the overlay canvas was 34 CSS pixels shorter than the video. Set the canvas to the full video-stage height and clear its pose when playback or seeking begins, avoiding a stale skeleton over a different frame. Browser geometry now reports equal video/canvas bounds.
- **Caveats / UNVERIFIED:** Pose was not present in every sampled frame, so this is an integration smoke test, not a quality or clinical evaluation. The angle values remain exploratory.

## 2026-10-23 — Browser prototype — local inference smoke test

- **Question:** Can the browser prototype load its local model, sample a video, draw the detected pose, and show the exploratory angle summary without uploading the clip?
- **Setup:** Local Vite development server and browser preview; MediaPipe Lite model and WASM served locally. Used the existing Ex1 `PM_039` Camera17 video, person 5 (train, as recorded in the earlier train-only checks).
- **Command:** Started the app with `npm run dev --workspace web`; selected the local video in the page. Its actual duration is 126.77 seconds, so the app correctly rejected it under the 60-second limit. For an inference-only smoke test, temporarily set the selected video element's reported duration to 55 seconds in browser developer tools, then removed that override; no source code or raw data was changed.
- **Data:** First 55 seconds of the named train recording; 24 sampled frames. No validation or test data.
- **Result:** Model detected a pose on 24/24 sampled frames, drew the overlay, and displayed exploratory mean elbow angles of 175° and 171°. The video remained local.
- **Caveats / UNVERIFIED:** This confirms the inference/rendering path only; the temporary duration override is not a user workflow. The README now warns that the supplied 126.77-second sample exceeds the app limit. Angle values and pose detections are not clinical results.

## 2026-10-23 — Task 1b-G — Ex1 elbow angle, Camera17 front

- **Question:** Does the frozen 2D triplet comparison behave differently on an arm exercise and a front-view camera, where left/right elbow motion is more distinct?
- **Setup:** Extended `angle_check.py` with an explicit Ex1 configuration: Camera17 front; GT triplets use the documented, still-UNVERIFIED `Left/RightArm` → shoulder, `ForeArm` → elbow, `Hand` → wrist hypothesis; MediaPipe uses its shoulder-elbow-wrist landmarks. Same five-frame sampling and side-mapping comparisons as Ex5/Ex6.
- **Command:** `$env:PYTHONPATH='ml'; .\.venv\Scripts\python.exe ml\spike\angle_check.py --exercise 1`; after method freeze, `.\.venv\Scripts\python.exe ml\spike\angle_check.py --split validation --exercise 1`.
- **Data:** Train: 18 repetitions, 2 recordings, subjects 5 and 8, 90 frames / 180 bilateral comparisons. Validation: 10 repetitions, one recording, subject 4, 50 frames / 100 comparisons. Ex1 `gt_quality(17)`, Camera17 front. Test split not accessed.
- **Result:** Pose detected on every sampled frame. Train direct/swapped elbow-angle pooled MAE: 4.711° / 6.346°; validation: 3.498° / 10.467°. Train direct MAE by subject: person 5 4.097°, person 8 5.479°. Train frame-error p90/max: 10.510°/22.300° direct and 11.076°/24.356° swapped. CSVs saved to ignored `data/derived/angles/train_ex1_cam17_elbow_angles.csv` and `validation_ex1_cam17_elbow_angles.csv`; Python tests: 14 passed.
- **Caveats / UNVERIFIED:** Only two train subjects and one validation subject; the result suggests the direct correspondence is more consistent on these samples but does not prove anatomical laterality, broader accuracy, or clinical value. The GT joint mapping and dataset pose convention remain **UNVERIFIED**. No clinical threshold was applied.
- **Reproduction labels:** **MUST** use the exact train command only for training exploration and keep test sealed. **SHOULD** run the validation command once with the same method. **MAY** inspect the ignored CSVs; do not commit derived output.

## 2026-10-23 — Task 1b-F — Second exercise with frozen angle method

- **Question:** Does the same MediaPipe/GT knee-angle procedure work on another leg exercise in the same Camera18 profile view?
- **Setup:** Reused the unchanged five-frame sampling, GT and MediaPipe hip-knee-ankle triplets, both side mappings, and summary metrics. `angle_check.py --exercise 5` selects Ex5 rows; no thresholds or parameters were fit.
- **Command:** `$env:PYTHONPATH='ml'; .\.venv\Scripts\python.exe ml\spike\angle_check.py --exercise 5`; then, once the train method was fixed, `.\.venv\Scripts\python.exe ml\spike\angle_check.py --split validation --exercise 5`.
- **Data:** Train: 46 repetitions, 4 recordings, subjects 3/5/6/8, 230 frames, 460 bilateral comparisons. Validation: 10 repetitions, one recording, subject 4, 50 frames, 100 comparisons. Both are Ex5 `gt_quality(18)`, Camera18 profile. Test split not accessed.
- **Result:** Pose detected on all sampled frames. Train direct/swapped pooled MAE: 9.297° / 13.327°; validation direct/swapped pooled MAE: 3.632° / 9.029°. Train direct MAE by subject: person 3 9.820°, 5 11.185°, 6 13.848°, 8 2.979°. Train frame-error p90/max: 19.992°/44.933° direct and 26.433°/43.984° swapped. CSVs saved to ignored `data/derived/angles/train_ex5_cam18_knee_angles.csv` and `validation_ex5_cam18_knee_angles.csv`; Python tests: 14 passed.
- **Caveats / UNVERIFIED:** Validation contains only one subject and cannot establish which mapping generalizes; do not select a side mapping from this result. The train subject spread and high frame-error maxima show a single pooled average hides substantial variation. This is still an exploratory, healthy-lab dataset comparison, not a clinical measurement or effectiveness claim.
- **Reproduction labels:** **MUST** use the exact train/validation commands above only after method freeze and keep test sealed. **SHOULD** review per-frame CSV values, not just the aggregate. **MAY** inspect the ignored CSV outputs; do not commit them.

## 2026-10-23 — Task 1b-E — Frozen-method validation check

- **Question:** With the training-only sampling and angle calculation unchanged, what does the held-out validation split show for Ex6 Camera18 profile?
- **Setup:** Added `--split train|validation` to `angle_check.py`; `test` is deliberately not an accepted option. Evaluated validation once after the train run, without changing frame sampling, landmarks, or angle calculations.
- **Command:** `$env:PYTHONPATH='ml'; .\.venv\Scripts\python.exe ml\spike\angle_check.py --split validation`; `.\.venv\Scripts\python.exe -m pytest tests\python`.
- **Data:** 10 eligible validation repetitions from 1 subject (person 4), one recording, 50 sampled frames, 100 bilateral comparisons; Ex6 `gt_quality(18)`, Camera18 profile. Test split not accessed.
- **Result:** Pose detected on 50/50 frames. Direct side labels: pooled/macro repetition knee-angle MAE 4.106°, median repetition MAE 3.846°. Swapped labels: 4.411° pooled/macro MAE, median 4.282°. Output saved to ignored `data/derived/angles/validation_ex6_cam18_knee_angles.csv`; Python tests: 14 passed.
- **Caveats / UNVERIFIED:** A single validation subject is too small to establish generalization or justify a side mapping; do not select a clinical threshold from these results. Results are descriptive and were not used to modify the method. Camera18 alignment, model-weight license, rectangular-frame warning, and clinical relevance remain **UNVERIFIED**.
- **Reproduction labels:** **MUST** first freeze the method from train and keep test sealed. **SHOULD** run validation only once for this unchanged method. **MAY** inspect the ignored validation CSV; do not tune based on this tiny validation sample.

## 2026-10-23 — Task 1b-D — Multi-repetition Ex6 profile angle check

- **Question:** Does the single-repetition knee-angle result repeat across train subjects for Ex6 in the Camera18 profile view?
- **Setup:** `angle_check.py` loads only `train` + `gt_quality(18)`, keeps Ex6 rows with Camera17 orientation `front` (Camera18 view `profile`), then samples five evenly spaced frames per repetition. It reports direct and swapped side correspondence, pooled frame MAE, macro/median repetition MAE, per-repetition MAE, and pose detections. No threshold is applied.
- **Command:** `$env:PYTHONPATH='ml'; .\.venv\Scripts\python.exe ml\spike\angle_check.py`; `.\.venv\Scripts\python.exe -m pytest tests\python`.
- **Data:** 39 repetitions, 4 recordings, 4 training subjects (3, 5, 6, 8); 195 sampled frames and 390 bilateral angle comparisons. No validation/test data.
- **Result:** Pose detected on 195/195 frames. Direct mapping: pooled and macro repetition MAE 8.243°, median repetition MAE 8.285°. Swapped mapping: pooled and macro repetition MAE 8.239°, median repetition MAE 8.232°. Direct pooled MAE by subject: person 3 7.234°, 5 6.089°, 6 8.969°, 8 10.577°. Frame-error p90/max were 14.467°/28.124° direct and 15.732°/30.329° swapped. CSV saved to ignored `data/derived/angles/train_ex6_cam18_knee_angles.csv`; Python tests: 14 passed.
- **Caveats / UNVERIFIED:** Train-only exploratory sample, not a held-out benchmark; four subjects and one exercise/view do not establish generalization. The near-identical direct/swapped aggregates confirm this profile-view angle cannot resolve side identity. Camera18 coordinate mapping, MediaPipe's rectangular-frame warning, model-weight license, and clinical relevance remain **UNVERIFIED**.
- **Reproduction labels:** **MUST** keep test sealed and run from the repo root. **SHOULD** verify the model SHA-256 and run the Python tests as in `ml/README.md`. **MAY** inspect the ignored CSV; do not commit it or other derived files.

## 2026-10-23 — Task 1b-C — Sampled Ex6 knee-angle comparison

- **Question:** On one train-only Ex6 Camera18 repetition, how close are MediaPipe and GT 2D knee angles at five frames through the rep?
- **Setup:** Same official local-only Pose Landmarker Lite model as Task 1b-B. `angle_check.py` reads the first train `gt_quality(18)` Ex6 front repetition and samples 0%, 25%, 50%, 75%, and 100% of its stored frame interval. It calculates image-plane hip-knee-ankle angles for both sides and reports direct and side-swapped correspondences.
- **Command:** `$env:PYTHONPATH='ml'; .\.venv\Scripts\python.exe ml\spike\angle_check.py`; `.\.venv\Scripts\python.exe -m pytest tests\python`.
- **Data:** Ex6 `PM_029`, person 3, rep 1, Camera18, frames 70, 102, 135, 168, 200; `gt_quality(18)`; train only. No validation/test reads.
- **Result:** Pose detected at all five frames; per-frame CPU inference 20.0–22.3 ms. Knee-angle MAE = **5.976°** over 10 bilateral frame comparisons for both direct and swapped side mappings. CSV saved to ignored `data/derived/angles/Ex6_PM_029_rep1_cam18_knee_angles.csv`. Python tests: 14 passed.
- **Caveats / UNVERIFIED:** One repetition is a smoke test, not an accuracy benchmark. Direct and swapped aggregate errors match because this profile view has similar left/right knee angles; it cannot settle side identity. Camera18 coordinate relationship, MediaPipe's non-fatal rectangular-frame projection warning, model-weight license, and any clinical interpretation remain **UNVERIFIED**.
- **Reproduction labels:** See the complete, ordered commands under “Task 1b reproduction” in `ml/README.md`. **MUST** keep the test split sealed. **SHOULD** run pytest after changing scripts. **MAY** inspect ignored PNG/CSV outputs; do not commit raw data or derived outputs.

## 2026-10-23 — Task 1b-B — MediaPipe single-frame feasibility

- **Hypothesis:** MediaPipe Pose Landmarker can run on the selected train-only frames and produce inspectable 2D landmarks; compare six bilateral GT joint correspondences without selecting a side mapping.
- **Setup:** Windows, `.venv` Python 3.14.0, MediaPipe 1.1.1, `PoseLandmarker` IMAGE mode on CPU. Downloaded the official Lite task model to ignored `data/derived/models/pose_landmarker_lite.task` (5,777,746 bytes; SHA-256 `59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a`). Model weights are not committed; their specific license is **UNVERIFIED**.
- **Command:** `$env:PYTHONPATH='ml'; .\.venv\Scripts\python.exe ml\spike\mediapipe_check.py`; `.\.venv\Scripts\python.exe -m pytest tests\python`.
- **Data:** Three single frames from the existing train-only `gt_quality` samples: Ex1 `PM_039`, person 5, frame 142, Camera17 and Camera18 (same repetition); Ex6 `PM_029`, person 3, frame 135, Camera18. Camera18 coordinates used as-is; no validation/test access.
- **Result:** One pose detected on each frame; comparison PNGs saved in ignored `data/derived/mediapipe/`. Inference times were 31.7 ms (Cam17), 22.4 ms (Ex1 Cam18), 21.8 ms (Ex6 Cam18). Mean 6-point bilateral pixel errors for direct vs swapped side labels: Ex1 Cam17 18.1 vs 209.4 px; Ex1 Cam18 71.3 vs 58.1 px; Ex6 Cam18 36.5 vs 46.3 px. Mean visibility: Cam17 left/right 0.936/0.982; Ex1 Cam18 0.954/0.472; Ex6 Cam18 0.983/0.583. Python tests: 14 passed.
- **Caveats / UNVERIFIED:** These are three frames, not a benchmark; no clinical or model-quality conclusion. The lower-error side mapping differs across cameras/exercises, so left/right and Camera18 correspondence remain **UNVERIFIED**. MediaPipe emitted a non-fatal `NORM_RECT` / `IMAGE_DIMENSIONS` projection warning on rectangular frames; impact on these coordinates is **UNVERIFIED**. CPU timings do not predict browser or phone performance.

## 2026-10-23 — Task 1b-A — Train-only GT overlay check

- **Hypothesis:** Save visual evidence for the joint-map and Camera18 orientation hypotheses without MediaPipe or an alignment decision.
- **Setup:** Windows, `.venv` Python 3.14.0; `overlay_check.py` uses the existing sealed loader and `gt_quality`; no validation or test rows.
- **Command:** `$env:PYTHONPATH='ml'; .\.venv\Scripts\python.exe ml\spike\overlay_check.py`; `.\.venv\Scripts\python.exe -m pytest tests\python`.
- **Data:** Ex1 `PM_039`, person 5, rep 1, frames 95–190, midpoint 142; same rep passes `gt_quality` for both cameras. Ex6 `PM_029`, person 3, rep 1, frames 70–200, midpoint 135; Camera18 `gt_quality`. Camera18 view for Ex6 is profile.
- **Result:** Script saved 9 PNGs (one Camera17 + four Camera18 modes for each of the two samples) to gitignored `data/derived/overlay/`; prints each path, frame size, in-frame fraction, and coordinate min/max. In-frame fractions: Ex1 Camera17 1.000; Ex1 Camera18 asis 1.000, each transformed mode 0.615; Ex6 Camera18 asis 1.000, each transformed mode 0.500. Python tests: 14 passed.
- **Caveats / UNVERIFIED:** Joint-to-landmark mapping and Camera18 coordinate mapping remain unverified; images are for owner inspection only. No clinical interpretation or MediaPipe run.

## 2026-10-23 — Task 1a-4 — Evidence levels and rule schema (docs only)

- **Hypothesis:** Naming three evidence levels and schema fields `status` / `approvedBy` / `approvedAt` / `provenance` stops dataset cutoffs and demo accounts from looking clinically approved.
- **Setup:** Docs only; no code, no `data/raw/`, no `ml/splits.json`.
- **Command:** none (schema/docs).
- **Data:** none.
- **Result:** Levels defined in `docs/decisions.md` and `docs/safety-case.md`. Schema updated in `docs/AI_BRIEF.md` and `rules/README.md`. Advisor recorded as TBD (unassigned); demo seed is not an approver; provisional-fire banner required.
- **Caveats / UNVERIFIED:** Banner and approval-gate enforcement are not implemented until later tasks. G1 still open.

## 2026-10-23 — Task 1a-3 — Filters, split audit, test-access log path

- **Hypothesis:** Named stdlib filters match the stated flag logic; CSV-only audit can describe the frozen 6/2/2 split without touching video/npy or `ml/splits.json`.
- **Setup:** Windows, `.venv` Python 3.14.0; pytest stdlib tests; pandas only in `audit_splits.py`.
- **Command:** `.\.venv\Scripts\python.exe -m pytest tests/python`; `.\.venv\Scripts\python.exe ml/eval/audit_splits.py`.
- **Data:** `Segmentation.csv` (semicolon, 1072 rows) + frozen `ml/splits.json`. Test split not loaded via `load_repetitions`.
- **Result:** `pytest tests/python` 14 passed. Audit: train 592 / val 238 / test 242 (CSV metadata; test not loaded). `gt_quality` cam17 train 267 val 98; cam18 train 402 val 115. Warning: validation Ex6 correctness=0 has 9 reps. `ml/splits.json` unchanged.
- **Caveats / UNVERIFIED:** Audit test-split cells are CSV metadata counts, not an evaluation run. License dual-wording recorded; we follow the stricter research-only text plus CC BY-NC 4.0.

## 2026-10-21 — Task 1a — REHAB24-6 inspect + loader tests

- **Hypothesis:** Local REHAB24-6 matches the owner’s CSV/file facts; a synthetic-fixture loader can split on `person_id` and seal the test set.
- **Setup:** Windows, `.venv` Python 3.14.0; packages from `pip show` (mediapipe 1.1.1, numpy 2.5.4, opencv-python 5.0.0.93, pandas 3.0.6, matplotlib 3.11.2). pytest was **not** in the venv; pin remains 9.1.1.
- **Command:** pandas/OpenCV probes on `data/raw/rehab24-6` (gitignored); `python -m pytest tests/python`.
- **Data:** REHAB24-6 local extract. CSV 1072 rows. Ex1/PM_000 Camera17 1304×30fps 1920×1080; c17 npy (1304,26,2). Camera18 transposed video 1080×1920, c18 npy (1304,26,2). 120fps npy (5215,26,2). Clean subset 521 rows. Split train `[8,5,6,2,3,10]` val `[4,1]` test `[7,9]`.
- **Result:** `pytest tests/python` 8 passed (7 loader + 1 scaffold). Real CSV (not committed): 1072 rows; train 592 (persons 2,3,5,6,8,10); validation 238 (1,4); train clean 267; `load_repetitions('test')` raises `SealedTestSplitError` with no log file. Test split not opened.
- **Caveats / UNVERIFIED:** joint origin; c18 npy vs transposed pixels; MediaPipe landmark map; Segmentation.txt `side`/`camera17` typos. No MediaPipe inference. Zips not re-hashed here (owner reported MD5 match).
- **Next:** Task 1b overlay + MediaPipe 1.1.1 (read *installed* docs; no legacy `mp.solutions.pose` unless it exists).

## 2026-10-21 — Task 0 — Scaffold smoke

- **Hypothesis:** Root lint, typecheck, JS unit tests, and pytest (scaffold only) pass on a clean install.
- **Setup:** Empty workspace → repo skeleton. Node v24.18.1, npm 11.16.0. Python 3.11 **not installed locally** (py reports 3.14.0). CI targets Python 3.11.
- **Command:** `npm install && npm run typecheck && npm run lint && npm run format:check && npm test` and `py -3.14 -m pytest` (local fallback; 3.11 preferred).
- **Data:** none.
- **Result:** After `$env:NODE_OPTIONS='--use-system-ca'` (local TLS intercept; GitHub Actions should not need this): `npm install` OK. After import-path + Prettier fixes: `typecheck`, `lint`, `format:check` pass; `npm test` 4 passed (web 2, api 2); `py -3.14 -m pytest` 1 passed. pytest **9.1.1** (Scripts folder not on PATH — always use `py -3.14 -m pytest`). Python 3.11 still missing locally.
- **Next:** Task 1 — REHAB24-6 license/structure check; no pipeline code until that report exists.

## Template

```
## YYYY-MM-DD — Task / experiment title
- Hypothesis:
- Setup (OS, versions, commit):
- Command:
- Data (id, split, N — never commit files):
- Metrics:
- Result:
- Caveats / UNVERIFIED:
```

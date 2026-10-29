# Experiments log

Append-only. Newest entry at the top. Record what was run, on what data, and the outcome. No clinical claims.

---

## 2026-10-29 — Live coach v2: hands-free, all four exercises, posture cues

- **Question:** The first laptop test of live mode gave no rep feedback and only one spoken word ("start"); the only messages were about distance. Why, and can the live coach work for every pack and coach more?
- **Diagnosis:** Re-running the old live coach on synthetic squats with home angles shifted 3-10 deg still counted 3 of 3 reps, so rep thresholds were not the cause. The likely cause is the old setup check: it needed shoulder, hip, knee and ankle visibility >= 0.5 on one side in 60% of frames and only ever said "step back", so with a laptop camera on a table the start button never unlocked in step 2. Not confirmed on the user's machine; the new diagnostics panel will show it.
- **Change:** `web/src/exercise/` (renamed from `squat/`). Exercise menu with all four packs (squat, lunge, leg abduction, shoulder abduction) and Arabic wording per pack; one-sided packs measure the limb that moves most (or the one chosen). Setup check names the missing parts ("I can't see your feet: step back or lower the camera") at visibility >= 0.35, and speaks. Hands-free: 1.5 s of "ready" starts a spoken 3-2-1; the reference stops itself after 2 reps and the exercise after the planned rep count, then a written and spoken summary. Per rep: spoken count + cue, live bar against the reference range, warning when the person leaves the view. Counting and range of motion are measured from each session's own resting angle (a camera offset between clinic and home cancels); a rep starts at 30% of the reference range (was 50%: small reps were never counted). New posture cue from each pack's second angle (trunk for squat and lunge, trunk lean for leg abduction, elbow for arm abduction): the slope of that angle per degree of the main movement, rep vs reference, so a deeper squat is not called a posture fault. GPU pose model with CPU fallback, 640x480 camera, frame-rate diagnostics.
- **Data:** Chromium fake camera (clips loop) playing REHAB24-6 recordings of training/validation subjects, reference from file, home live, speech captured: squat PM_043 (side; 3 correct then 3 incorrect), lunge PM_042 (side; 1 correct, 5 incorrect), leg abduction PM_018 (front; 5 incorrect), arm abduction PM_012 (front; 5 incorrect).
- **Result:** All four reached "ready" in the right view, counted reps hands-free and spoke a cue per rep. Squat: the correct rep at reference depth -> "excellent"; deeper reps -> "do not go deeper" (+12 to +37 deg), trunk cue on the deepest. Leg abduction: 7 of 7 counted reps -> "lift your leg higher" (-21 to -39 deg). Lunge: 7 of 7 flagged (depth on 3, trunk on all); against its own correct reps 1 of 1 full rep -> "close" (the other was cut by the camera loop). Arm abduction: 2 of 6 incorrect reps flagged, 4 "close": these errors are probably the arm drifting forward, which REHAB26 showed needs a 60-90 deg view; the front view cannot see them. First-version posture check (raw trunk curve) flagged every squat including the correct one; the per-degree slope fixed that.
- **Caveats:** One person per exercise, fake camera with looping clips (the first counted rep can be partial), tolerances and rep counts are test values, posture cues are not yet validated against labels; voice depends on an Arabic voice in the browser.
- **Next:** User test on the laptop with the diagnostics panel; evaluate the posture cue on REHAB24-6 labels per error type; offer a second camera angle for arm abduction.

## 2026-10-29 — Live camera mode: setup check and per-rep feedback while exercising

- **Question:** Can the coach check the camera position before the patient starts and judge each squat as it happens, with the same rules as the recorded-video flow?
- **Change:** `web/src/squat/liveCoach.ts` (setup check: person present, full body visible on the near side, view matches the pack; `LiveSquatCoach`: rep thresholds from the reference rep, each rep judged when it ends, a rep is not judged if the person was missing on most of its frames or it was not filmed side-on) and `LiveCamera.tsx` (camera, skeleton overlay, setup banner, start button enabled only when ready, optional Arabic voice cue per rep). Both steps of the squat screen can now use the camera or a file; recording the reference with the camera produces the same reference as a file.
- **Data:** Chromium fake camera playing the REHAB24-6 PM_043 clips from the previous entry (downscaled to 360x640, 15 fps), headless, WASM and model served locally.
- **Result:** Reference recorded with the camera: 2 reps, 70 and 73 deg, same as the file. Live home exercise: setup reached "ready", each rep's feedback appeared when the rep ended; depth differences +21, +16, +38, +51, +51, -1 deg vs +21, +17, +40, +51, +52, -1 from the file analysis of the same reps (the camera loop started mid-clip). Front view: setup banner "change the phone angle", start button stayed disabled.
- **Caveats:** Fake camera, one person; the camera must be opened from `localhost` or `https` (browser rule), so a phone on the same Wi-Fi needs an https setup; voice depends on the browser having an Arabic voice.
- **Next:** Try on the laptop webcam and a phone; add lunge and leg abduction to the app with the same code.

## 2026-10-29 — Squat with a clinic reference, end to end in the browser

- **Question:** Does the research pipeline (squat pack, view gate, personal reference) work as an app feature on real video?
- **Change:** `web/src/squat/`: reads `rules/packs/lower-limb.squat.json` and `rules/gate/view-rule.json`, runs MediaPipe Lite on each frame of a local video in the browser (15 frames per second of video), measures knee flexion of the leg nearer the camera, refuses clips that are not side-on, finds reps from the clip's own range, compares each home rep with the chosen reference rep (DTW identical to `ml/qawam_ml/reference.py`, checked to 10 decimals) and shows an Arabic cue per rep. The tolerance is physio-set (default 10 deg labelled as a test value); an optional goniometer reading on the reference rep turns depth into real degrees.
- **Data:** REHAB24-6 PM_043 (subject 5, training split), trimmed locally, not committed: reference = reps 1-2 from camera 18 (side); home = reps 3-8 (3-5 correct, 6-8 incorrect) from camera 18 (side) and camera 17 (front). Headless Chromium, WASM and model served from local copies.
- **Result:** Side view accepted (frontalness 0.09 and 0.06); all 6 home reps found at the right times. Depth difference vs reference rep 1, app vs motion capture (left knee): rep 3 -1 / 0, rep 4 +21 / +19, rep 5 +17 / +12, rep 6 +40 / +33, rep 7 +51 / +42, rep 8 +52 / +42 deg. The incorrect reps were the deepest; reps 4-5, labelled correct, really were 12-19 deg deeper than the reference, so at a 10 deg tolerance they are flagged and at 20 deg they are not. Front view of the same reps refused (frontalness 0.64) with "I can't see you well: put the phone at your side". Analysis took 55 s for a 9 s clip and 225 s for a 39 s clip on 2 CPU cores.
- **Caveats:** One person; the reference comes from the same session; the tolerance is not clinical; analysis is slower than real time on this machine.
- **Next:** Live camera mode with the setup wizard (check the view before recording); faster processing (play the video instead of seeking); try it on our own phone recordings.

## 2026-10-29 — Lite vs Full pose model, same frames and gate

- **Question:** Does MediaPipe Pose Landmarker Full measure better than Lite, and does the view rule + one-rep calibration still hold with it?
- **Setup:** Same as the gate entry below: `angle_eval.py --save-landmarks` on Ex4-6, both cameras, train + validation subjects, then `gate_eval.py` with both labels. Same 2-core cloud workspace.
- **Result, angle error in the pack's view (frame MAE, train / validation, deg):** squat side 8.6 / 4.7 (Lite) vs **6.4 / 3.2** (Full); lunge side **5.8 / 6.0** (Lite) vs 9.6 / 3.1 (Full); leg abduction front **3.7 / 9.0** vs 3.8 / 8.8. Median inference 16.2 vs 19.3 ms per frame.
- **Result, view rule + one-rep calibration (false cues among spoken reps):** Lite 7 / 166 = **4.2%** (upper bound 7.8%); Full 19 / 163 = 11.7% (16.6%). Squat is identical (3 / 88 for both). The difference is side-view lunge: Lite 3 / 52, Full 14 / 51, spread over three people (3, 5, 8), so Full's lunge error there is not a steady offset the calibration can remove. Not yet checked: whether Full swaps the front and back leg when they overlap in profile.
- **Decision:** Keep Lite as the default model: faster, and the gate's guarantee holds with it. Full is not worth the cost for these packs.
- **Next:** Plot side-view lunge curves for persons 3, 5, 8 under Full to confirm or rule out leg swapping before any model change.

## 2026-10-29 — Richer confidence gate: view match plus one-rep calibration

- **Question:** Can the coach speak on some reps with a false-cue rate at or below 10%, where visibility alone abstained on everything?
- **Setup:** `ml/eval/angle_eval.py --save-landmarks` (Lite, Ex4-6, both cameras, every frame, train + validation subjects 3, 4, 5, 6, 8; test 7, 9 untouched), then `ml/eval/gate_eval.py`. New per-rep features from the phone's own landmarks (`ml/qawam_ml/quality.py`): visibility, detection rate, frontalness (shoulder width / torso length), out-of-plane ratio, angle jitter, bone-length variation, left/right leg-length ratio, measured range. Everything leave-one-person-out. "Wrong" = rep mean angle error > 10 deg (evaluation tolerance only). Two labels: **absolute** (raw error) and **calibrated** (error after subtracting the offset measured on the first rep of the same recording, camera and side; that rep is then dropped), which simulates the clinic reference recording.
- **Finding 1, the error is mostly a steady offset:** for squat and lunge, MediaPipe reads knee flexion 4-10 deg lower than motion capture on every rep of a person and view. After the one-rep calibration, side-view squat goes from 24% to 3% wrong reps (median error 7.1 to 3.1 deg) and side-view lunge from 8% to 6%. Half-profile squat does not improve (27%): there the error changes with the movement. Leg abduction from the side or half-profile stays unmeasurable.
- **Finding 2, learned scores rank better but do not certify:** out-of-fold AUROC for telling right from wrong measurements, absolute label: visibility 0.67, new geometry features 0.79, combined 0.80 (gain +0.13, 95% CI 0.07 to 0.19, resampling people). Almost all of that gain is in leg abduction (view); within squat and lunge every score is near chance (0.50-0.60). With 5 people, Learn-then-Test thresholds on the learned scores were unstable (Bonferroni over 50 thresholds certifies nothing; fixed-sequence testing, added to `selective.py`, stops early when the most confident reps include errors).
- **Finding 3, a fixed rule works:** "speak only when the estimated view matches the pack's view" (side packs: frontalness <= cut; front packs: frontalness >= cut; cut-offs set leave-one-person-out from the dataset's **view labels only**, never from error labels), together with the one-rep calibration:

| Gate | Coverage (all reps, all views) | False-cue rate | Exact 95% upper bound |
| --- | --- | --- | --- |
| Visibility only, Learn-then-Test alpha 0.10 (previous entry) | 0% | — | — |
| View rule, no calibration | 27.6% | 14.7% (27 / 184) | 19.7% |
| **View rule + one-rep calibration** | **26.5%** | **4.2% (7 / 166)** | **7.8%** |

  By pack (calibrated): squat 3 / 88 wrong (upper 8.6%), lunge 3 / 52 (14.2%), leg abduction 1 / 26 (17.0%). By held-out person: 0-10.8% false cues. Coverage is low only because the dataset films every exercise from every view on purpose; the rule accepts essentially all reps filmed in the pack's view, so in the product the setup wizard decides coverage. Frontalness separates profile from other views perfectly (<= 0.15 vs >= 0.16). Exported cut-offs: side packs frontalness <= 0.178, front packs >= 0.601 (`view_rule.json`).
- **Caveats:** 5 healthy people performing deliberate errors; reps from one person are not independent, so the bounds are indicative; the calibration rep comes from the same session (the clinic-to-home gap is untested); the 10 deg tolerance is an evaluation choice, not a clinical one.
- **Decision taken:** see `docs/decisions.md` (2026-10-29, gate design).
- **Next:** Repeat on REHAB26-ViewAngles (3 cameras, 11 orientations) to place the view cut-offs more finely and check the oblique 20-35 deg view the reference study favoured; record a second-session reference in our own volunteer study.

## 2026-10-29 — Full-frame MediaPipe angle baseline and visibility gate, REHAB24-6 lower limb

- **Question:** How far are MediaPipe Pose Landmarker Lite angles from the REHAB24-6 2D ground truth on every frame, by camera view, and can landmark visibility alone certify a false-cue rate?
- **Setup:** `ml/eval/angle_eval.py --exercises 6 5 4`, Lite model (float16 v1), VIDEO mode, every frame of every `gt_quality` repetition, train and validation subjects only (test 7, 9 untouched). Pack primary angles: squat and lunge knee flexion, leg abduction hip abduction. Gate unit = repetition x camera x side; "wrong" = rep mean error > 10 deg (evaluation tolerance, not clinical) or pose missing on half the frames. Run in the cloud workspace on the Zenodo copy, 2 CPU cores, median 20.3 ms per frame.
- **Result, angle error (frame MAE in degrees, train / validation):**

| Exercise | Declared view in pack | Declared view | Other views |
| --- | --- | --- | --- |
| Squat (Ex6) | side | 8.6 / 4.7 (cam18 profile) | front 6.0 / 2.4; half-profile 9.1-9.5 / 5.4-6.3 |
| Lunge (Ex5) | side | 5.8 / 6.0 (cam18 profile) | front 5.6 / 3.0; half-profile 4.7-9.8 / 4.5-5.9 |
| Leg abduction (Ex4) | front | 3.7 / 9.0 (cam17 front) | profile 43.2 / 48.0; half-profile 5.8-14.0 / 2.1-21.8 |

  Pose was detected on 100% of frames. Per-subject rep MAE ranged 4.6-10.5 deg for squat and lunge and 15-21 deg for leg abduction pooled over views (the profile view dominates that number).
- **Result, gate:** mean landmark visibility predicts a wrong measurement only weakly (AUC 0.66). At alpha = 0.10 (delta 0.10) no threshold can be certified, so the gate abstains on every rep (train wrong rate 29%, validation 14%). Restricting to the declared view lowers the wrong rate (squat 24%, lunge 7%, abduction 0%) but still certifies nothing at 0.10; at alpha = 0.20 it certifies 6-7% coverage.
- **Interpretation:** (1) Camera view matters more than the model: leg abduction filmed from the side is unusable (43-48 deg), filmed from the front it is 4-9 deg. The setup wizard must enforce the pack's view. (2) Visibility alone is not a safe confidence signal, matching Khanal and Zhou (2026). The gate behaves safely (it refuses rather than guesses) but is not yet useful.
- **Next:** Build a richer confidence score (view match from shoulder/hip width ratio, landmark jitter, bone-length consistency, left/right agreement, DTW residual), fit it on train subjects, calibrate with `selective.py`, and report the risk-coverage curve against visibility alone. Compare the Full model on the same frames.

## 2026-10-29 — Personal vs universal reference on REHAB26-ViewAngles (MediaPipe output)

- **Question:** Does the REHAB24-6 mocap result hold on a second dataset, on real pose-estimator output, and at which camera angles?
- **Setup:** `ml/eval/rehab26_eval.py` on REHAB26-ViewAngles (Zenodo 23018128, CC BY-NC 4.0): 5 people, 3 synchronised cameras, person orientations 0-90 deg, so viewing angles from frontal to profile; MediaPipe 2D landmarks shipped with the dataset, scaled to an assumed 1920x1080. Squat (`lower-limb.squat`) and arm abduction (new `upper-limb.shoulder-abduction` pack). Leave-one-person-out: universal templates and thresholds come from the other four people. Personal reference = first correct rep of the same person, orientation and camera.
- **Result (ROC AUC, all views):** squat 1,497 rep views: personal DTW **0.925**, universal template 0.588, universal depth threshold 0.526; gain +0.34 (95% CI 0.27 to 0.41) and +0.40 (0.28 to 0.52). Shoulder abduction 1,503 rep views: **0.756** vs 0.538 vs 0.477; gain +0.22 (0.15 to 0.30) and +0.28 (0.20 to 0.38). Every one of the 5 people and every viewing-angle bucket favours the personal reference.
- **Camera angle by error (squat, personal DTW AUC):** knees inside 1.00 frontal vs 0.72 profile; torso to side 0.95 frontal vs 0.69 profile; knees forward 0.84 frontal vs 0.97 oblique; lifted heels 0.89 frontal vs 0.97 oblique; shallow squat 0.94 frontal vs 0.99-1.00 oblique/half-profile. Best single bucket overall: oblique 20-35 deg (0.963). Shoulder: arm-forward errors need 60-90 deg (0.94-0.96 vs 0.69 frontal).
- **Caveats:** 5 healthy people with deliberate errors; same-session reference; frame size assumed, not read from the videos; reps appear once per camera.
- **Next:** Setup wizard default for squat = oblique 20-35 deg, frontal when the physio is watching for knee valgus; add the calibrated gate on these scores; repeat on IntelliRehabDS (30 people, Kinect) and UCOPhyRehab++ (physio scores) for the cross-dataset claim.

## 2026-10-28 — Personal reference vs universal reference on REHAB24-6 ground truth

- **Question:** Does comparing a rep with the subject's own correct rep flag physio-labelled incorrect reps better than a universal template or a universal depth threshold?
- **Setup:** `ml/eval/reference_eval.py`, mocap 2D ground truth only (no video, no pose model), lower-limb packs Ex4 leg abduction, Ex5 lunge, Ex6 squat, both cameras. Reps with `mocap_erroneous == 0` (mocap does not depend on lights or bystanders). Personal reference = the subject's first correct rep in the same recording and orientation, excluded from scoring. Universal template = mean correct rep of training subjects (leave-one-subject-out for training subjects). Score = mean DTW absolute deviation over the pack's angles. Metric = ROC AUC (0.5 = chance). Test subjects 7 and 9 not accessed.
- **Result (all 7 non-test subjects, all views pooled):**

| Pack | Reps (incorrect) | Personal DTW | Universal template DTW | Universal depth threshold |
| --- | --- | --- | --- | --- |
| Squat (Ex6) | 268 (92) | 0.789 | 0.584 | 0.567 |
| Lunge (Ex5) | 200 (108) | 0.847 | 0.645 | 0.688 |
| Leg abduction (Ex4) | 306 (158) | 0.675 | 0.537 | 0.510 |

  AUC gain of personal DTW, 95% CI from resampling subjects: vs depth threshold +0.22 (0.04 to 0.38) squat, +0.16 (0.02 to 0.34) lunge, +0.17 (0.09 to 0.24) leg abduction; vs universal template +0.21 (-0.01 to 0.43) squat, +0.20 (-0.01 to 0.44) lunge, +0.14 (0.09 to 0.19) leg abduction. Validation-only squat (2 subjects, 18 incorrect): personal 0.81 vs template 0.83 vs threshold 0.52.
- **Caveats:** Mocap ground truth, so this is the method's upper bound before pose-estimation noise. Each rep appears once per camera, so reps are not independent; CIs resample subjects. The reference comes from the same session, which is easier than a clinic-to-home gap. Errors were performed deliberately by healthy adults. In the declared view alone the gain is smaller (squat side view 0.77 vs 0.65 vs 0.61) and for lunge the depth threshold wins in side view (0.82 vs 0.70); half-profile views separate errors best, which echoes REHAB26-ViewAngles.
- **Next:** Repeat with MediaPipe angles once `angle_eval.py` has run locally; add a multi-view or half-profile option to the setup wizard; record the reference in a separate session in our own volunteer study.

## 2026-10-28 — Pack, reference, gate and full-frame angle harness (synthetic tests)

- **Question:** Can the lower-limb packs, DTW reference comparison and calibrated gate be measured end to end on REHAB24-6?
- **Change:** Added `rules/packs/` (schema + squat, lunge, leg-abduction packs, all provisional with placeholders), `ml/qawam_ml/packs.py`, `reference.py` (DTW), `selective.py` (risk-coverage + Learn-then-Test calibration), and `ml/eval/angle_eval.py`, which runs MediaPipe in VIDEO mode on **every frame** of every `gt_quality` rep (earlier spikes sampled five frames per rep) and writes `frames.csv`, `reps.csv`, `summary.md` and `summary.json` under ignored `data/derived/angle-eval/`.
- **Data:** Synthetic only: a generated squat skeleton, generated videos and a fake landmarker. 50 Python tests pass, including a check that the calibrated gate keeps the false-cue rate <= alpha on fresh synthetic data in at least 90% of 200 trials, and that the harness refuses the sealed test split.
- **Command (to run on the laptop):** `py -3.14 ml\eval\angle_eval.py --exercises 6 --dataset-root C:\Users\eyada\Grad_1\data\raw\rehab24-6 --model C:\Users\eyada\Grad_1\data\derived\models\pose_landmarker_lite.task`
- **Caveat:** No REHAB24-6 number is reported in this entry; results land in the next entry after the local run. Ground truth is the dataset's 2D projection, so results are 2D angle agreement, not clinical accuracy.
- **Next:** Run Ex6 with the Lite model, then Ex4–Ex6, then the Full model for comparison; freeze the baseline in `docs/metrics.md`.

## 2026-10-25 — Manual count comparison for local video tests

- **Question:** Can a user quantify the experimental counter's difference from their own observed count on a short clip?
- **Change:** Added an optional non-negative whole-number reference count. At clip end, the unsaved local summary shows detector count, user-entered count, absolute difference, and clip duration. Invalid fractional/negative counts are rejected; leaving the field blank omits the comparison. No data is saved or transmitted.
- **How to test:** Before playing a clip, enter the number of complete arm-raise-and-return cycles you observe. Choose auto or one arm, start analysis, and let the clip end. Compare the two counts, then repeat with a front-facing and side-facing clip. Replay clears the summary.
- **Data:** Synthetic input validation tests only; no user or dataset video was accessed.
- **Caveat / UNVERIFIED:** The user-entered count is an informal reference, not expert annotation. This comparison does not prove accuracy or suitability and must not guide treatment.
- **Next:** Use the error difference to spot which view is less reliable; if repeated results disagree, keep the side-view limitation explicit and seek labeled, authorized clips before tuning thresholds.

## 2026-10-25 — Selectable arm for the experimental counter

- **Question:** Can the user select the arm that is most visible when the automatic side choice is unreliable?
- **Change:** Added automatic, person-left, and person-right selections. A manually selected side is not replaced by the opposite side when it becomes unclear; the counter abstains instead. Changing the selection resets the count and current cycle so counts from different sides are not mixed.
- **How to test:** Select a video, choose the clearer arm before starting playback, then compare against automatic. Changing sides should reset the visible count to zero.
- **Data:** Synthetic unit tests only; no user or dataset video was accessed.
- **Caveat / UNVERIFIED:** Selection cannot recover an arm hidden by the torso or correct a poor 2D angle. The anatomical interpretation of MediaPipe's left/right labels may also depend on view/mirroring.
- **Next:** Use the side selection and live diagnostics on your next front/side comparison, and report whether a selected side improves or worsens the observed count.

## 2026-10-24 — On-device end-of-clip summary

- **Question:** Can a user review what the experimental counter detected after a full clip without introducing server storage or presenting it as a clinical session record?
- **Change:** At natural video end, show the actually detected complete-repetition count and clip duration. The summary remains only in page memory and is labeled experimental, unsaved, and not a medical record. A replay button restarts the clip and clears the summary when playback resumes.
- **How to test:** Load a short clip, start analysis, let it finish, review the count/duration, then choose **إعادة الفيديو** and confirm the summary clears while the counter restarts.
- **Data:** No user or dataset video was processed during implementation. A generated browser clip exercised the `ended` handler and displayed an in-page 0-count/duration summary; duration formatting and invalid-input handling are covered by unit tests.
- **Caveat / UNVERIFIED:** This is only a local UI summary. It does not verify the repetition count, save a session, or establish exercise validity.
- **Next:** Compare summary count with manually observed repetitions on user-selected non-sensitive clips; keep the result explicitly experimental.

## 2026-10-24 — Live counter diagnostics for camera-view comparison

- **Question:** Can a user identify why the experimental arm counter behaves differently between frontal and side-facing recordings?
- **Change:** Added live display of selected MediaPipe side, estimated 2D arm angle, minimum visibility among the shoulder/wrist/hip points, and counter phase. The counter now keeps tracking the selected side while its three landmarks remain usable, rather than switching sides whenever the other side's visibility briefly rises.
- **How to test:** Select the same short clip or comparable clips of one arm raise, run once facing the camera and once side-on, and compare angle, visibility, phase, skeleton alignment, and final count. Begin with arm down, raise overhead, then return down.
- **Data:** No video was accessed or processed during this change. A synthetic unit test verifies the side lock, diagnostic values, and cycle logic.
- **Caveat / UNVERIFIED:** The readouts expose the algorithm's inputs; they do not establish that the estimated angle, visibility, side label, or rep count is correct. A side view can compress the relevant movement in 2D and produce a plausible-looking but misleading value.
- **Next:** Use the comparison to localize the failure (landmark drift/visibility, side selection, or angle thresholds) before deciding whether to adjust the heuristic or limit supported views.

## 2026-10-24 — Portrait-video pose-overlay alignment

- **Question:** Does the skeleton overlay align with the visible video when a portrait recording is displayed in a wide page?
- **Evidence:** User screenshots showed pose lines extending into the side margins while the recorded person remained centered in a portrait frame. The previous overlay canvas covered the full-width player, stretching normalized landmark x-coordinates across the letterboxed area.
- **Change:** The video and canvas now share a fit-content frame centered inside the player, preserving the recording's intrinsic aspect ratio. Added visible disclosure that side views/occlusion can lower landmark and count reliability.
- **Data:** No user video was accessed or copied. Browser geometry will be checked using a generated portrait clip.
- **Caveat / UNVERIFIED:** Fixing render alignment does not improve MediaPipe's pose estimate or establish counter accuracy for side-facing movement.
- **Next:** Re-test the same clip and confirm the skeleton stays on the person. If points are aligned but jump or move to the wrong limbs, investigate pose visibility/orientation and compare frame-by-frame counts before adjusting thresholds.

## 2026-10-24 — Local video pose-landmark overlay

- **Question:** Can a real browser feature accept user-selected video and display pose landmarks without transmitting the clip?
- **Setup:** Added MediaPipe Tasks Vision 1.1.1 to the web app. The user selects a local video no longer than two minutes; after explicit start, the browser loads the Lite model and WASM runtime from the documented public endpoints, runs video-mode inference locally on playback frames, and draws the 33-point pose skeleton over the preview. Model/network failures appear as errors; the video object URL is revoked when replaced/unmounted.
- **Command:** `npm run dev:demo`; select a short video; click **بدء تحليل الوضعية**; play it.
- **Data:** No repository/dataset videos were processed during implementation. A generated 1-second stick-figure clip was used only to smoke-test browser model initialization and inference.
- **Result:** Production build and type/test checks pass. In-browser MediaPipe initialization and inference completed; the synthetic drawing correctly followed the no-pose result path. Tracking on an actual person/exercise clip still needs user verification because no authorized exercise video was available for this feature.
- **Caveats / UNVERIFIED at this initial overlay step:** Browser camera is not used. Video stays in browser memory, but public MediaPipe WASM/model files are downloaded from jsDelivr/Google when analysis starts. At this point it was a visualization only; the later experimental counter is separately documented below. Model inference accuracy is unmeasured here.
- **Next:** User can test with a non-sensitive short clip; inspect whether landmarks track the body. Then establish dataset joint semantics and frame alignment before connecting pose joints to exercise analysis.

## 2026-10-24 — Experimental browser arm-raise counter

- **Question:** Can the real browser pose stream drive a visible, testable repetition-count flow before the exercise mapping and thresholds are validated?
- **Setup:** Connected MediaPipe Pose Landmarker Lite's standard left/right shoulder, wrist, and hip indices to a 2D arm-elevation estimate. The clearer side is used when all three landmarks have visibility ≥0.5. The counter recognizes lowered (≤45°) → raised (≥120°) → lowered as one completed cycle. Rewind resets the current cycle; unclear landmarks break a partial cycle. A displayed target of 8 is only a test target and is never substituted for the measured count.
- **Command:** `npm run dev:demo`; select a non-sensitive video, click **بدء تحليل الوضعية**, and play it. For a manual counter check, use a clip with a clearly visible person completing arm raises from lowered to overhead and back.
- **Data:** No new dataset or raw files used. Synthetic coordinates test angle geometry, full-cycle counting, visibility abstention, and avoiding counts when a recording begins raised.
- **Result:** The UI exposes the current count and the mapping, angle bounds, visibility cutoff, and 8-repetition test target. It prominently states that they are unreviewed/unvalidated, the count may be wrong, and it is not a treatment target or form assessment.
- **Caveats / UNVERIFIED:** The simple 2D angle depends on camera orientation and occlusion. MediaPipe's generic joint indices are not a verified REHAB24-6 joint correspondence. The cutoff and angle bounds are engineering assumptions; no rep-count accuracy, clinical validity, or exercise suitability is claimed.
- **Next:** Compare the counter with manually labeled complete cycles in authorized non-test recordings across views; adjust or reject the heuristic based on measured errors. Keep validation and sealed test governance intact.

## 2026-10-24 — Interactive Arabic text-normalization test

- **Question:** Can a user verify the Arabic text-normalization and lexicon/model OR behavior without entering health information or using medical terms?
- **Setup:** Added a UI-only text box with a harmless test phrase (`كلمة اختبار`), a synthetic lexicon term, and an optional simulated positive model checkbox. Results are computed in page memory and are not persisted or transmitted.
- **Command:** `npm run dev:demo`; enter `كلمة اختبَار` then choose **اختبر العبارة المصطنعة**. Optionally enter an unrelated phrase, enable the simulated model flag, and rerun.
- **Data:** Test phrase and synthetic term only. No actual health notes or red-flag vocabulary.
- **Result:** Matching phrase shows `ESCALATE_FOR_REVIEW` / `LEXICON_FLAG`; model toggle adds `MODEL_FLAG`. Non-match explicitly warns that it is not evidence of safety.
- **Caveats / UNVERIFIED:** This does not validate Arabic clinical vocabulary, red-flag recall, or patient safety. Do not enter personal or health data.
- **Next:** Use only reviewed terms and a qualifiedly reviewed escalation flow before building a real pain check-in.

## 2026-10-24 — Interactive synthetic pipeline demonstration

- **Question:** Can a user verify the browser angle pipeline behavior without uploading a video or using a model?
- **Setup:** Added a button that runs a deterministic fabricated 2D sequence through the actual TypeScript angle/repetition pipeline. It includes a low-visibility frame; the UI shows per-frame status, angle, count, and reason code.
- **Command:** `npm test`; `npm run typecheck`; `npm run lint`; `npm run format:check`; `npm -w web run build`.
- **Data:** Generated synthetic coordinates and visibility only; all temporary state remains in the browser component memory.
- **Result:** UI test asserts that the low-visibility frame returns `CANNOT_ASSESS`, reports its reason code, and the final count remains two complete synthetic cycles.
- **Browser smoke check:** Opened the page, clicked **شغّل المثال المصطنع**, and confirmed the rendered output shows two cycles, frame 5 as `CANNOT_ASSESS` with `LOW_REQUIRED_LANDMARK_VISIBILITY`, and no count increase at the gap. The first live check found the Vite 7 / Vite 8 plugin mismatch; aligning web Vite to the workspace's Vite 8 toolchain restored the dev server and page rendering.
- **Run-path check:** `localhost:5173` was occupied by a different checkout, and `localhost:5174` by this worktree's already-running preview. The attached VS Code recording shows the command entered as `run npm run dev:demo`, which PowerShell rejects because `run` is not a command; it also shows the generic dev command. Updated `dev:demo` to let Vite automatically select the next free port and clarified that users should open the URL printed in the terminal.
- **Caveats / UNVERIFIED:** This verifies software behavior only. Synthetic thresholds are test parameters, not exercise or clinical values; no camera or user data is read, uploaded, or stored.
- **Next:** Replace the demonstration only after authoritative mapping/alignment evidence and model integration are available.

## 2026-10-24 — Configurable pain-text escalation primitive

- **Question:** Can the core lexicon-OR-model safety invariant be tested without inventing or deploying a medical vocabulary?
- **Setup:** Added Arabic normalization for diacritics, tatweel, alef/ya variants, and Arabic/Persian digits. The pure evaluator accepts only caller-configured terms, escalates any exact whole-phrase lexicon hit, and lets an optional model flag add escalation but never suppress a lexicon result. Empty text and missing lexicon configuration abstain.
- **Command:** `npm test`; `npm run typecheck`; `npm run lint`; `npm run format:check`.
- **Data:** Synthetic phrases and a test-only flag term; no clinical lexicon, patient text, or dataset used.
- **Result:** Tests cover normalization, lexicon and model OR semantics, Arabic clitic matching, whole-token boundaries, abstention, and malformed lexicon entries.
- **Caveats / UNVERIFIED:** No reviewed Egyptian-dialect lexicon, clinician-reviewed red-flag term set, user input, model, escalation notification, or care pathway is implemented. A non-match is not evidence of safety.
- **Next:** Have a qualified reviewer define/verify the language and escalation protocol before configuring production-like terms or exposing this to users.

## 2026-10-24 — Browser angle-to-repetition pipeline

- **Question:** Can the UI runtime compose capture gating, in-plane angle calculation, causal smoothing, and repetition-state logic without relying on an unverified model mapping?
- **Setup:** Added a pure TypeScript pipeline requiring caller-supplied landmark names, visibility cutoff, smoothing window, and low/high repetition bounds. It returns per-frame angles/status and a cumulative count, abstains when required observations or angle geometry are unusable, and clears smoothing/partial cycles on gaps.
- **Command:** `npm test`; `npm run typecheck`; `npm run lint`; `npm run format:check`; `npm -w web run build`.
- **Data:** Synthetic 2D points and visibility scores only; no dataset or raw data used.
- **Result:** Tests cover angle geometry, low-high-low cycle counting, causal smoothing, missing visibility, undefined angles, reset, and invalid configuration.
- **Caveats / UNVERIFIED:** This is generic technical behavior, not a validated exercise detector; no MediaPipe connection, anatomical mapping, thresholds, coaching rules, or UI integration were added.
- **Next:** Obtain authoritative joint semantics and frame alignment before configuring a real exercise or camera pipeline.

## 2026-10-24 — Browser capture gate connected to rule evaluation

- **Question:** Can the browser rule evaluator consume the same explicit fail-closed visibility decision used by the Python analysis primitives?
- **Setup:** Added a TypeScript required-landmark visibility gate with caller-supplied names and cutoff, missing/low-visibility reason codes, and input validation. Rule evaluation now receives the gate result directly and refuses cues when capture is not ready.
- **Command:** `npm test`; `npm run typecheck`; `npm run lint`; `npm run format:check`; `npm -w web run build`.
- **Data:** Synthetic landmark visibility and rule metrics only; no dataset or raw data used.
- **Result:** Tests cover passing/missing/low-visibility inputs, invalid configuration, and the gate-to-rule abstention path.
- **Caveats / UNVERIFIED:** The threshold and required landmarks must be supplied by a future caller; no MediaPipe output, exercise mapping, UI state, or clinical rule is connected.
- **Next:** Obtain authoritative landmark correspondence and frame alignment before integrating browser pose output.

## 2026-10-24 — Configurable deterministic rule evaluator

- **Question:** Can exercise rule evaluation be implemented without inventing exercise thresholds or claiming clinician approval?
- **Setup:** Added a pure TypeScript evaluator that requires caller-provided rules and metrics, stops on `CANNOT_ASSESS` or missing metrics, reports matching rule IDs/versions/provenance, and flags provisional matches for the prototype warning. It rejects duplicate active rule IDs and approved rules without clinician provenance, a non-placeholder approver, and a timestamp.
- **Command:** `npm test`; `npm run typecheck`; `npm run lint`; `npm run format:check`.
- **Data:** Synthetic test metrics and rules only; no dataset or raw data used.
- **Result:** Tests cover matching/provenance, capture refusal, missing metric refusal, no configured rule, fake approval rejection, and duplicate active versions.
- **Caveats / UNVERIFIED:** No exercise-specific rule exists, no clinical threshold was selected, and the evaluator is not wired to pose inference or the UI. A non-placeholder approver string is not proof of a real clinician's identity or approval.
- **Next:** Obtain authoritative landmark correspondence and resolve frame alignment before configuring exercise rules or exposing evaluator output.

## 2026-10-24 — Interactive simulated session outcomes

- **Question:** Can the UI demonstrate both a completed-session summary and safe abstention while the real pose pipeline remains unverified?
- **Setup:** Added a two-scenario selector. The default is simulated `CANNOT_ASSESS`; it shows a missing-landmark reason code and no rep count. A separate explicit button reveals the synthetic completed-session summary. Both states say no video was analyzed and remain visibly simulated.
- **Command:** `npm test`; `npm run typecheck`; `npm run lint`; `npm run format:check`; `npm -w web run build`.
- **Data:** Static synthetic UI cases only; no video or dataset data.
- **Result:** Component tests exercise switching in both directions and assert no repetition count appears in the abstention state.
- **Caveats / UNVERIFIED:** This is a UI mock, not model inference or a validated confidence gate. The example reason code is illustrative and is not triggered by camera output.
- **Next:** Replace scenarios with actual session results only after resolving landmark mapping/alignment and integrating pose inference with the technical `cannot_assess` pipeline.

## 2026-10-24 — Simulated session-summary UI and REHAB24-6 model comparison

- **Question:** Can the patient-facing rep/session summary be prototyped safely while the real pose pipeline is blocked, and can Qawam accuracy be compared with the REHAB24-6 study?
- **Setup:** Added a static mock summary with simulated rep count/duration, synthetic movement description, and explicit no-video/no-form-assessment copy. Reviewed Zenodo 13305826 and the associated 2024 paper metadata/abstract access.
- **Command:** `npm test`; `npm run typecheck`; `npm run lint`; `npm run format:check`; `npm -w web run build`.
- **Data:** Static synthetic UI values only; Zenodo record and publication metadata. No dataset files downloaded or processed.
- **Result:** UI test asserts that summary values are marked simulated and that no video was analyzed. Zenodo describes ground-truth data, not one model or aggregate accuracy score. The associated paper's accessible excerpt says MediaPipe Pose had the lowest 3D position error in general, but exact tested variant/numeric comparisons were not verifiable from the full text. Qawam reports normalized 2D pixel error with Lite on a limited sample; no direct winner/comparable accuracy claim is supported.
- **Caveats / UNVERIFIED:** Current browser Lite wiring is not independently verified in this checkout. Qawam's 26-joint-to-MediaPipe mapping remains unresolved; metrics differ in dimension/definition. The session card is not inference output.
- **Next:** Resolve landmark semantics, integrate real capture/inference for one scoped exercise, and evaluate rep-count accuracy on permitted training data before replacing the mock.

## 2026-10-24 — Synthetic angle-to-repetition pipeline

- **Question:** Can the generic capture gate, angle, smoothing, and repetition logic be composed and tested together without relying on an unverified anatomical mapping?
- **Setup:** Added `AngleRepPipeline`, requiring callers to supply required landmark names, a 3-point angle tuple, visibility cutoff, smoothing window, and low/high repetition bounds. A missing/low-visibility landmark or undefined angle returns `CANNOT_ASSESS`; such gaps clear smoothing history and break partial rep cycles.
- **Command:** `py -3.14 -m pytest tests/python/test_angle_pipeline.py`.
- **Data:** Synthetic coordinates/angles and visibility values only; no raw, validation, or test data used.
- **Result:** Synthetic integration tests cover computed angles and completed cycles, smoothing, low-visibility and missing-coordinate refusal, undefined geometry, cycle interruption, reset, and invalid mapping configuration.
- **Caveats / UNVERIFIED:** This proves component wiring only. It does not validate MediaPipe inference, landmark correspondence, threshold values, rep accuracy, clinical safety, or user experience. No app behavior or exercise-specific config was changed.
- **Next:** Obtain authoritative joint semantics or expert confirmation, then wire this pipeline to an explicitly scoped pose source and evaluate on authorized training data before any separate validation.

## 2026-10-24 — Configurable capture-visibility gate

- **Question:** Can Qawam explicitly refuse analysis when configured required landmarks are missing or below a supplied visibility cutoff, without guessing which joints or cutoff are appropriate?
- **Setup:** Added `assess_capture_quality`, a pure helper that requires a non-empty unique landmark list and an explicit [0, 1] visibility cutoff. It returns `CANNOT_ASSESS` with stable reason codes for missing/low-visibility required landmarks, or `READY_FOR_ANALYSIS` when all pass. Invalid inputs raise `ValueError`.
- **Command:** `py -3.14 -m pytest tests/python/test_capture_quality.py`.
- **Data:** Synthetic visibility dictionaries only; no raw data, validation rows, split manifest, or test data read.
- **Result:** Tests cover passing values, equality at the caller cutoff, missing and `None` values, low visibility, multiple reason codes, and invalid configuration/input. No default cutoff or anatomical landmark mapping was added.
- **Caveats / UNVERIFIED:** This helper does not inspect images or model output, is not wired into the app, and does not establish a clinically meaningful threshold or safe capture. `READY_FOR_ANALYSIS` is a technical capture gate only, not approval to provide exercise advice.
- **Next:** Obtain authoritative joint semantics or expert confirmation, then select and validate required landmarks/cutoff with documented provenance before integrating capture gating into the browser.

## 2026-10-24 — Arabic-first first-screen prototype disclaimer

- **Question:** Can the project clearly communicate its educational/non-clinical status before any future demo results are shown?
- **Setup:** Replaced the web placeholder with a minimal React/Vite entry page. Added a prominent accessible alert in Arabic and English stating that the prototype is not clinically approved and any demo decisions/results are simulated, not clinician-provided or approved. Updated safety documentation and the decision log.
- **Command:** `npm run test:web`; `npm run typecheck`; `npm -w web run build`.
- **Data:** Static copy only; no clinical rules, medical decisions, external data, or patient data.
- **Result:** First render carries `lang="ar"` and `dir="rtl"`; notice is visible in both languages and marked with `role="alert"`. No fabricated clinician judgments or approval were created.
- **Caveats / UNVERIFIED:** This static disclaimer is not a substitute for a per-rule provisional banner, `cannot_assess`, clinician governance, or real clinical review. A demo UI using synthetic cases must label each result individually as simulated.
- **Next:** After obtaining source-authored joint semantics or expert confirmation, build one bounded exercise flow; until then, do not display guessed form advice as a doctor's decision.

## 2026-10-24 — Configurable repetition-counter primitive

- **Question:** Can repetition-cycle logic be implemented without selecting an unverified joint mapping or clinical threshold?
- **Setup:** Added a stateful low/high hysteresis counter whose two thresholds must be supplied by the caller. It requires observing the low phase, then the high phase, then a return to low before incrementing; missing (`None`) observations leave state unchanged.
- **Command:** `py -3.14 -m pytest tests/python/test_repetitions.py`.
- **Data:** Synthetic angle values only; no raw data, validation rows, split manifest, or test data read.
- **Result:** Counter and tests cover complete cycles, hysteresis/repeated samples, missing observations, reset behavior, threshold validation, and invalid observations. No exercise-specific threshold defaults or joint IDs were added.
- **Caveats / UNVERIFIED:** The state machine is a generic signal primitive, not a validated rep detector. Threshold selection, smoothing window, angle triplet, capture-quality gating, and false/missed-repetition performance require exercise-specific review and evaluation.
- **Next:** Obtain authoritative joint semantics or expert confirmation; then evaluate the integrated angle/smoothing/counter sequence on authorized training data before separate validation.

## 2026-10-24 — Causal moving-average primitive

- **Question:** Can the next signal-processing primitive be implemented without choosing an unverified joint mapping, exercise, or clinical cutoff?
- **Setup:** Added a pure trailing moving average with caller-specified window size. It preserves input length, uses available prior samples during warm-up, and never reads future samples.
- **Command:** `py -3.14 -m pytest tests/python/test_smoothing.py`.
- **Data:** Synthetic numeric sequences only; no raw data, validation rows, split manifest, or test data read.
- **Result:** The primitive is implemented with explicit validation for positive integer windows and finite numeric samples. Synthetic tests cover causal behavior, warm-up, empty input, invalid values, and large finite values.
- **Caveats / UNVERIFIED:** This utility does not establish an appropriate smoothing window for any exercise, sampling rate, or clinical use. It is not wired into the app or an angle pipeline.
- **Next:** Obtain source-authored joint semantics or expert confirmation; then choose and evaluate the angle input and window on authorized training data.

## 2026-10-24 — Generic 2D angle primitive and source-record check

- **Question:** What is the safest useful next implementation step while the REHAB24-6-to-MediaPipe joint mapping remains unresolved?
- **Setup:** Checked the primary REHAB24-6 Zenodo record and existing project docs. The record describes OptiTrack-derived 26-joint ground truth, nominally synchronized 30 FPS cameras, and 2D coordinates projected with a simplified pinhole model, but does not specify correspondence to MediaPipe's 33 landmarks. Added a pure angle-at-vertex helper that accepts points rather than joint IDs, with synthetic tests for geometry, invariance, undefined degenerate angles, and invalid inputs.
- **Command:** `py -3.14 -m pytest tests/python/test_angles.py`.
- **Data:** Documentation/source metadata and synthetic points only. No raw data, validation rows, split manifest, or test data read.
- **Result:** `qawam_ml.angles.angle_degrees` returns the smaller 2D in-plane angle in degrees, and returns `None` when either arm has zero length. Invalid coordinate shapes, nonnumeric values, and non-finite coordinates raise `ValueError`. No anatomical mapping, clinical cutoff, or app behavior added.
- **Caveats / UNVERIFIED:** Unit tests establish geometry behavior only; they do not establish a joint triplet, camera suitability, angle accuracy, or clinical relevance. PM_039/PM_101 mapping comparisons remain a small exploratory train-only sample. PM_101 video/joint row-count mismatch (1307 vs 1308) leaves full-clip synchronization unresolved.
- **Next:** Obtain a source-authored joint mapping or expert confirmation; then use verified point triplets for train-only angle error and separately validate before any coaching use.

## 2026-10-24 — PM_101 Camera18 cross-recording correspondence probe

- **Question:** Does the same candidate 26-joint correspondence remain plausible on a second authorized Camera18 train recording?
- **Setup:** Extended the hard-scoped MediaPipe Lite overlay script to process the three approved PM_101 frames and summarize candidate distances per clip/view and combined. Inspected only the PM_101 Camera18 video and matching 30 FPS joint array, frames 34–36.
- **Command:** `py -3.14 ml/eval/overlay_camera18_train.py`.
- **Data:** Only `data/raw/rehab24-6/Ex1/PM_101-Camera18-30fps-transposed.mp4` and `data/raw/rehab24-6/Ex1/PM_101-c18-30fps.npy`, authorized frames 34–36, plus the previously authorized PM_039 pair/frames for the cross-recording aggregate and official Lite model. PM_101 is subject 6, Ex1, Camera18 half-profile per train-only export. No other raw files, validation data, split manifest, or test data read.
- **Result:** PM_101 mean normalized distance across 36 point/frame comparisons: documented hypothesis 1.58%; adjacent arm-joint shift 4.21%; side-swapped hypothesis 10.49%. Combined PM_039+PM_101 sample across 108 comparisons: 1.80%, 3.85%, and 7.14%, respectively. Generated PM_101 overlays at frames 34–36 under ignored `data/derived/overlay/`.
- **Caveats / UNVERIFIED:** PM_101 video has 1307 frames and its `.npy` has 1308 rows; sampled frames are same-index and visually plausible, but full-clip synchronization remains UNVERIFIED. Three neighboring frames from one PM_101 clip do not establish anatomical mapping or clinical performance. The existing candidate remains UNVERIFIED pending authoritative joint definitions and broader checks. No app mapping or coaching behavior changed.
- **Next:** Verify the REHAB24-6 skeleton semantics from an authoritative source; do not begin angle/coaching code with an assumed mapping.

## 2026-10-24 — PM_101 cross-clip check blocked on authorized files

- **Question:** Can the MediaPipe Lite candidate correspondence be checked on a second authorized Camera18 train recording?
- **Setup:** Checked only the two specifically authorized PM_101 paths in this worktree. Both are absent. Did not search the attached folder or other raw-data locations.
- **Command:** `Test-Path` on the two authorized paths only.
- **Data:** Expected pair: `data/raw/rehab24-6/Ex1/PM_101-Camera18-30fps-transposed.mp4` and `data/raw/rehab24-6/Ex1/PM_101-c18-30fps.npy`; planned zero-based frames 34–36, subject 6, train split as identified in the supplied train-only derived export.
- **Result:** Cross-recording inference was not run because both exact files are missing. Roadmap now marks confidence/coverage and the one-recording PM_039 overlay as completed, and orders PM_101 cross-clip comparison before joint-semantics verification and angle baselines.
- **Caveats / UNVERIFIED:** No evidence from PM_101 has been observed; PM_039 candidate mapping scores are limited to one person/recording. No other raw files or test split were accessed.
- **Next:** Copy only the two already-authorized PM_101 files into the exact paths above, then run `py -3.14 ml/eval/overlay_camera18_train.py` after updating the script's sample target for that one authorized pair.

## 2026-10-24 — PM_039 Camera18 MediaPipe correspondence probe

- **Question:** Does MediaPipe Pose Landmarker Lite output on the authorized train clip support the existing candidate 26-joint mapping, an adjacent-arm-joint shift, or a left/right swap?
- **Setup:** Installed the pinned MediaPipe 1.1.1 package and downloaded the official `pose_landmarker_lite.task` into ignored `data/derived/overlay/`. Extended the hard-scoped overlay script to run IMAGE-mode inference on frames 94–96 (profile) and 2539–2541 (half-profile) of the PM_039 recording. Compared the same 12 candidate GT↔MediaPipe point pairs per frame using Euclidean distance normalized by image diagonal. No automatic mapping selection or app behavior change.
- **Command:** `py -3.14 -m pip install mediapipe==1.1.1`; download the official task model to `data/derived/overlay/pose_landmarker_lite.task`; `py -3.14 ml/eval/overlay_camera18_train.py`.
- **Data:** Only the previously authorized `data/raw/rehab24-6/Ex1/PM_039-Camera18-30fps-transposed.mp4` and matching `PM_039-c18-30fps.npy`, zero-based frames 94–96 and 2539–2541, plus the official Lite task model. The sampled indices are train frames from subject 5 (PM_039) as confirmed in the supplied train export. No other raw files, split manifest, validation files, or test data read.
- **Result:** Mean candidate normalized distance over 72 point/frame comparisons: documented hypothesis 1.90%; adjacent arm-joint shift 3.67%; left/right-swapped hypothesis 5.46%. By view, the documented mapping scores 2.40% on profile and 1.41% on half-profile. Comparison overlays regenerated in ignored `data/derived/overlay/`.
- **Caveats / UNVERIFIED:** All frames remain from one clip/person, and movement is limited; profile bilateral landmarks overlap and are partly occluded. No mapping fix was justified; 26-joint-to-MediaPipe mapping remains UNVERIFIED. Runtime emitted a MediaPipe projection warning; coordinates are treated as exploratory image-space output only.
- **Next:** Run the cross-clip check on the already authorized PM_101 Camera18 half-profile train sample at frames 34–36 after its matching files are supplied: `data/raw/rehab24-6/Ex1/PM_101-Camera18-30fps-transposed.mp4` and `data/raw/rehab24-6/Ex1/PM_101-c18-30fps.npy`. These files are absent from this worktree so no PM_101 inference has been run.

## 2026-10-23 — Camera18 PM_039 same-index overlay

- **Question:** Do the authorized Camera18 PM_039 train video and 30 FPS joint sequence visually support same-index alignment and portrait coordinate orientation?
- **Setup:** Added `ml/eval/overlay_camera18_train.py`, hard-scoped to the named PM_039 Camera18 video/joint pair and zero-based frames 94–96. It checks video/joint frame-count equality, expected 1080×1920 dimensions, array shape, and finite coordinates. The overlay renders the 26 named ground-truth joints with hierarchy links; links are visualization aids, not a MediaPipe mapping.
- **Command:** `py -3.14 -m pip install opencv-python==5.0.0.93`; `py -3.14 ml/eval/overlay_camera18_train.py`.
- **Data:** Only `data/raw/rehab24-6/Ex1/PM_039-Camera18-30fps-transposed.mp4` and `data/raw/rehab24-6/Ex1/PM_039-c18-30fps.npy`, both user-authorized train assets. Video: 3803 frames, 30 FPS, 1080×1920. Joint array: `(3803, 26, 2)`. No other raw files, split manifest, or test data accessed.
- **Result:** Frames 94, 95, and 96 visually place the same-index ground-truth coordinates over the person's head/trunk/limbs/feet in the displayed portrait frame. For this recording, the evidence supports same-index alignment and x/y orientation without swapping. PNG outputs are under ignored `data/derived/overlay/`.
- **Caveats / UNVERIFIED:** Three adjacent frames from one recording do not establish dataset-wide origin, synchronization for other recordings, or a 26-joint-to-MediaPipe landmark mapping. The subject is mostly stationary across these neighboring frames, so this is a bounded visual plausibility check, not a motion-based synchronization validation.
- **Next:** Verify the dataset joint definitions against any MediaPipe mapping used by the application before angle baselines; do not infer that mapping from this overlay.

## 2026-10-23 — Camera18 coordinate-order diagnostic

- **Question:** Do the supplied derived frame exports support the Camera18 coordinate-order component of the alignment check?
- **Setup:** Extended the CSV-only report to compare direct and coordinate-swapped normalized errors by split, camera, and view. No images or arrays were loaded.
- **Command:** `py -3.14 ml/eval/summarize_view_robustness.py`; `py -3.14 -m pytest tests/python`.
- **Data:** The same supplied derived train and validation CSVs only (1,015 train and 300 validation frames). No raw video, `.npy`, split manifest, or test data read.
- **Result:** Direct mean error is below swapped mean error in every camera/view stratum. Camera18 train direct vs swapped mean: half-profile 1.42% vs 10.47%, profile 2.74% vs 5.76%. Validation: half-profile 0.97% vs 9.23%, profile 1.54% vs 5.16%. Report regenerated at `docs/eval-confidence-coverage.md`.
- **Caveats / UNVERIFIED:** The exported comparison only tests component swapping. It does not visually verify orientation, origin, frame synchronization, or joint mapping. The required train overlay assets were not supplied in this derived-only set.
- **Next:** Run a visual overlay for specifically authorized train Camera18 video and 30 FPS ground-truth joint files; validate one frame plus neighboring frames before computing angles.

## 2026-10-23 — Reproducible confidence and view-robustness summary

- **Question:** Can the supplied train/validation visibility and normalized keypoint-error results be reproduced and stratified by exercise and view?
- **Setup:** Added a stdlib-only CSV analysis CLI and synthetic tests. It accepts only rows explicitly labeled as the expected `train` or `validation` split, groups by exercise × camera × view, and reports pose-detection coverage, mean visibility, direct normalized error mean/p90, plus descriptive visibility-threshold coverage and conditional error. Thresholds are descriptive and not app gates.
- **Command:** `py -3.14 ml/eval/summarize_view_robustness.py`; `py -3.14 -m pytest tests/python/test_view_robustness.py`.
- **Data:** Supplied `data/processed/model-evaluation/train_view_robustness.csv` (1,015 sampled frames, subjects 3/5/6/8) and `validation_view_robustness.csv` (300 frames, subject 4). No raw data, split manifest, or test data read.
- **Result:** Generated `docs/eval-confidence-coverage.md`. Train/validation coverage at visibility >=0.70 was 94.8%/91.7%, with conditional mean error 1.54%/0.87% and nearest-rank p90 2.15%/1.16%. At >=0.80, coverage was 86.4%/80.7%, conditional mean error 1.53%/0.88% and p90 2.15%/1.19%. All sampled Ex1 Camera18 profile frames fell below 0.70. No clinically meaningful cutoff inferred.
- **Caveats / UNVERIFIED:** The rows are sampled frames and not independent subjects/repetitions; validation uses one subject. The grouped results are descriptive, with no confidence intervals or clinical claims. Keypoint error is not exercise correctness.
- **Next:** Verify image orientation, frame alignment, and 26-joint-to-MediaPipe mapping, especially for Camera18, before computing exercise angle baselines.

## 2026-10-23 — Model comparison and evaluation roadmap

- **Question:** What is the highest-value next evaluation step, and can the reported Lite-model evidence be compared with REHAB26-ViewAngles?
- **Setup:** Documentation and workspace-artifact inventory only. Reviewed current evaluation docs and the cited arXiv v2 / Zenodo record. Did not access `data/raw/`, `ml/splits.json` contents for evaluation, or the test split.
- **Command:** none; no evaluation run.
- **Data:** No frame-level confidence/error export or other generated evaluation CSV was present in this checkout. Prior reported exploratory sample: 1,015 train frames (subjects 3/5/6/8) and 300 validation frames (subject 4); no test access reported.
- **Result:** Added `docs/model-evaluation-roadmap.md` with the supplied preliminary normalized keypoint-error and visibility/coverage results, caveats, the Lite-vs-Full and localization-vs-separability distinction, and an ordered remaining-work roadmap. The immediate reproducibility rerun is blocked until its non-raw frame-level export is available; no threshold or clinical gate was selected.
- **Caveats / UNVERIFIED:** Prior numerical summaries could not be independently reproduced or stratified by exercise/view from this checkout. REHAB26-ViewAngles' abstract reports relative separability gains (16.9% for optimal single-view vs frontal; up to 13.1% for two-view), not Qawam keypoint accuracy. No clinical significance is inferred.
- **Next:** Reproduce item 1 of `docs/model-evaluation-roadmap.md` from an existing non-raw export, keeping train, validation, and test access distinct.
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

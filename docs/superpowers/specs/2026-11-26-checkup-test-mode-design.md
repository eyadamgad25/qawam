# Check-up test mode: camera-timed sit-to-stand and Timed Up and Go

Date 2026-11-26. Chosen by the project owner as the first extension from the research report
(`reports/Rehab coach advanced extensions.md`, rank 1): it turns the camera from a coach into a measuring tool and answers the
supervisor's question about what a software engineer adds (building the measurement and proving it is trustworthy).

## Why
Physiotherapists use three short standard tests to judge leg strength, function and fall risk, and repeat them over weeks:
five-times sit-to-stand (time for 5 stand-ups), 30-second sit-to-stand (stand-ups in 30 s) and Timed Up and Go (stand, walk 3 m,
turn, walk back, sit; time). A slow result is a clear signal for the physio to check (published at-risk cut-offs, e.g. KINECAL:
five-times > 16.7 s, Timed Up and Go > 14 s). Today they are timed in the clinic with a stopwatch. The patient will do them at home
in front of the phone, and the result reaches the physio's report, but only after the app is shown to time them as well as a person.

## Goals
1. The app runs the three tests at home: setup check, spoken instructions and count in Arabic, a result in seconds or reps.
2. Proof of accuracy, measured once against a reference set before any result is seen, reported with agreement statistics.
3. Results in the physio's progress report, over time, and exportable in HL7 FHIR R4 (the standard clinics use to exchange records).

## Non-goals
No diagnosis or fall prediction shown to the patient; no automatic plan change; no balance tests yet; no video upload.

## Anti-goals (a failure even if it works)
- A result shown to the physio as trustworthy for a test or setup that the evaluation did not cover.
- Any video, image or face saved or sent anywhere.
- Tuning the timing rules on the evaluation videos.

## Approaches
1. **Record body points, analyse when the test ends (chosen).** During the test the app keeps body points in memory and speaks the
   count live with the existing rep engine; at the end one function finds the start and stop moments using frames before and after
   each moment, then discards the points. The same TypeScript function scores the app and the evaluation datasets, so what is
   validated is what ships.
2. Live timing frame by frame: instant, but it detects moments late because it cannot look ahead.
3. Server or cloud video analysis: breaks offline use and uploads video. Rejected.

## How it works
- **Packs:** `sit-to-stand` (side view; hip height relative to leg length and knee angle) and `timed-up-and-go` (side view, person
  walks across the frame; stand-up, leave, return and sit-down events). Versioned JSON in `rules/packs/` like the existing ones.
- **Phases:** setup check (existing `setupStatus`: chair and whole body visible, side-on; for Timed Up and Go a 3 m line, the phone
  far enough to see the path) → spoken instructions → "3, 2, 1, go" → test → result.
- **Timing rule:** start = "go"; end = five-times: seated after the 5th stand-up; 30-second: count of full stand-ups by 30 s;
  Timed Up and Go: seated again. If the person leaves the frame, a joint is hidden too long, or the view is wrong, the app gives
  **no result** ("could not measure, please repeat") instead of a guess.
- **Result:** seconds (one decimal) or count, with the test conditions (chair height not measured; the setup used), saved per
  session like today's sessions, shown in the progress report with a chart over time and the published cut-off line for reference
  only, labelled "for the physiotherapist".
- **FHIR export:** one `Observation` per test result (value, unit, date, device "HomeRehab AI camera", method "phone camera, side
  view"), bundled per patient; codes from LOINC where a code exists, otherwise a local code system (builder verifies codes).
  Checked with the official HL7 FHIR validator.

## Proof of accuracy (rules fixed before any app result is seen)
- **Data now (no ethics approval needed: public, de-identified):**
  1. **Stanford sit-to-stand videos** (`stanfordnmbl/sit2stand-analysis`, npj Digital Medicine 2023): home phone videos of the
     five-times test, faces hidden. **No licence stated: used for research evaluation only, not redistributed, cited.**
     60 videos drawn at random with a fixed seed, before the app runs on any of them.
  2. **KINECAL** (PhysioNet, CC0): Kinect skeletons of 90 people aged 18-92 incl. fallers; five-times sit-to-stand and Timed Up and
     Go, projected to a side-on 2D view (as done for KIMORE). Tests the timing logic on older and at-risk people, not the camera.
     Only the needed folders are downloaded (the full set is 86 GB). Its Healthy-Adult group (33) may be used to set thresholds;
     the other three groups (older non-fallers, self-reported fallers, clinically at risk: 57 people) are the test.
- **Reference:** two team members each mark the start frame and the end frame in `tools/label-checkup.html`, which replays the
  body points as a stick figure (no video, no face), without ever showing the app's result; their agreement is reported and the
  reference is their mean. Start = first frame the hips leave the chair; end = first frame the hips are back at chair level after
  the 5th stand-up (Timed Up and Go: after walking back). Checked 2026-11-26: neither dataset has stopwatch or clinician times
  (Stanford's `time` column is their own algorithm's), so both are marked this way. Stanford: the published OpenPose body points
  (`trajectories.zip`) and `dataMovement.csv` (video id, frame rate); `videometa.pkl` is not opened (an untrusted pickle).
- **Clips that start standing (added 2026-11-27, after the first rater's marks, before any app result):** some Stanford
  recordings begin with the person already up. The app never meets this (the patient sits before "go"), and the first rater
  marked some of them from the first sit-down, so they are scored in their own block, reported but not part of the pass
  decision. Rule, from the body points only: mean hip height above the ankle in the first 0.5 s is above half of that clip's
  5-95 percentile range (`starts_standing` in `ml/eval/checkup_eval.py`). Raters count from the first rise after sitting;
  a clip that ends standing after the 5th rise is "Cannot label". The rule picks 12 of the 60: 4OQQyQYB, 5UbIHQc7,
  Casa9F70, XPMfD5E2, ZK2JlJsq, byzUmGWJ, jxxMYJzb, lqIUuRkJ, nyRH10Bw, oluI9aqT, pmYdj2Zc, ujkGAy6u; the judged block is
  the other 48.
- **Count of stand-ups:** exact when the app finds exactly 5 stand-ups between the raters' mean start and mean end.
- **Frozen 2026-11-27, before the app ran on any of them:** `data/derived/checkup/eval_set.json` (seed 20261127): 60 Stanford
  five-times recordings, KINECAL test groups 53 five-times and 51 Timed Up and Go; SHA-256
  `a9933f2855cfc7e031525cc39377383fb9653f7f9274c62561904e3fa164f47a`.
- **Pass rules, five-times sit-to-stand (Stanford):** app vs reference ICC(2,1) >= 0.90 with its 95% interval reported; mean
  absolute error <= 0.5 s; Bland-Altman limits reported; count of stand-ups exact on >= 95%; a result given on >= 80% of videos
  (no result counted, never hidden). **Timed Up and Go (KINECAL):** ICC >= 0.85, MAE <= 1.0 s. Not met → the test stays out of the
  physio report (it may still be shown as practice) and the failure is reported.
- **30-second sit-to-stand:** no public reference; counts checked on the team's own recordings later; until then labelled
  "not validated" in the report.
- **Later (design ready, needs people):** (A) three team members in their 20s, two of them timing with stopwatches; (B) 20+ adults
  incl. older people, timed by a physiotherapist, under the ethics approval being prepared.

## Ethics and privacy (built in)
- No video or image is ever stored or sent; only body points in memory during the test, and the result afterwards.
- The camera view on screen blurs the face (head points mark the area); any frame shown in the labelling page is blurred too.
- Only the patient's assigned physiotherapist sees results (existing access rules: clinic, role, assignment).
- Using a patient's body points for training is a separate opt-in, off by default, and is not built now.
- **Lines stated clearly in the app and the thesis:** body points and test results are sensitive health data under Egypt's Personal
  Data Protection Law 151/2020; results are not a diagnosis; training on patient data needs consent and ethics approval; the
  Stanford videos have no stated licence and are used for evaluation only.

## Constraints
Offline, in the browser, MediaPipe Pose Lite as today; Arabic first with English; works on a mid-range Android phone; existing
access rules and session store; no new paid service.

## Left to the builder
Exact event-detection thresholds (fixed on KINECAL's Healthy-Adult group, Stanford videos outside the 60 and the team's own
test videos; never on the 60 evaluation videos or KINECAL's test groups), the labelling page's layout, how the face blur is drawn, chart styling, and the FHIR codes after checking LOINC.

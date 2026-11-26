# Quality model (A), then sensor fusion (B): short design

Date 2026-11-25. Order chosen by the project owner: A, then B.

## Why
The supervisor asked for technical depth: what a software engineer builds here that a clinician cannot. The personal
reference ranks squat reps well (AUC 0.79) but one cut-off does not transfer between people (F1 0.55). A model trained
on IntelliRehabDS reaches macro-F1 0.79 on unseen patients, from Kinect points.

## A. Quality model on phone-style 2D points
- **Input:** 13 points a phone also sees, x and y only, centred on the hips and scaled by torso length.
- **Features:** every rep against the person's own reference, per channel (joint angles, trunk tilt, knee over ankle,
  shoulder height, head offset): mean difference along the aligned movement, peak difference, range difference; plus
  tempo and smoothness. The reference is the person's first correct rep (K = 1) or first three (K = 3); those reps are
  never scored, and the same reps are left out for every method.
- **Per-patient cut-off:** with K = 3, each difference is also divided by how much the person's own three reps vary.
- **Model:** logistic regression with class weights and L2, answer at 0.5. Nothing is tuned on the test people.
- **Data:** IntelliRehabDS (person 217 left out, as its authors do), REHAB24-6 (people 7 and 9 stay sealed, motion-capture
  2D points), REHAB26-ViewAngles (MediaPipe points, the real phone model).
- **Splits:** leave one person out. Transfer tests train on one dataset and test once on another, not refitted.
- **Primary measure:** macro-F1 of the model against personal DTW with a cut-off learned on other people. Also accuracy,
  F1, AUC within exercise, majority baselines, 95% intervals by resampling people.
- **Not sure:** the threshold comes from other people's out-of-fold scores, exact 95% bound <= 10% wrong.
- **Ship rule:** goes into the app only if it beats personal DTW on REHAB26 phone points **and** its interval excludes a
  tie, for that exercise. Otherwise it stays research and the app does not change.

## B. Sensor fusion on KneE-PAD
- 31 knee patients, 8 muscle + motion sensors. Task 1: correct vs wrong squat, leg extension, walking. Leave one patient out.
- Compare motion only, muscle only, both by joined features, both by averaged probabilities; then with one sensor type
  missing at test time, and with few motion sensors (thigh only, as a phone in a pocket would be).
- The release has no video, so camera + sensor fusion cannot be trained on it. Camera-side evidence stays separate.

## Not doing
No sealed people, no clinical thresholds, no app change unless the ship rule passes, no cue text from a language model.

## Approaches considered
1. Reference-relative features + logistic regression (chosen): small, explainable, portable to the phone.
2. Deep network on raw points: KERAAL showed it overfits with few people (CNN 0.66 on simulated errors, 0.26 on test).
3. Cut-off tuning only: simplest, but uses one number per rep and misses posture errors.

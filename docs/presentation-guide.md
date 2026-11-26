# HomeRehab AI: presentation guide (Milestone 1 deck v10, 58 slides)

How to explain each slide in plain words to doctors, what to say if they push, and what changed after the 2026-11-03 results. Deck: `Desktop\CO\HomeRehabAI_Milestone1_v10.pptx` (the old 34-slide deck is kept beside it).

**v10 note:** the deck now follows the reference deck's twelve sections. Slides: 1 title; 2 agenda; 4-6 introduction; 8 problem; 10-11 motivation; 13 objectives; 15-20 related work; 22-27 one slide per dataset; 29-34 approach, including the use case, sequence and class diagrams; 36-42 results and expected outcomes; 44 requirements; 46-52 plan, work division, risks, ethics; 54 conclusion; 56-57 references. Slide numbers below are from the older order; the content still applies.

**v8 note:** the deck now has an agenda, 12 section dividers, a three-slide introduction and a conclusion, so slide numbers below are from the older 37-slide order; the content still applies.

**v4 note:** explanatory boxes and sentences were removed from slides 8, 13, 21, 23, 24, 25 and 26, and the speaker notes from slide 1. Those points are now spoken only, so learn them from this guide (Lite 4.2% vs Full 11.7%; gate on patients 3.3% vs 24.0%; phone at 45° still 89% of cues right; errors fell 48% to 21%; synthetic notes, so 98% is an upper bound).

**The one sentence to repeat:** *A physiotherapist records the patient doing the exercise correctly; at home, the phone compares every repetition with that recording and speaks in Arabic only when it can measure reliably; otherwise it stays silent.*

**Three words the panel must leave with:** home, Arabic, trustworthy ("silent rather than wrong").

---

## Part 1: slide by slide

Each slide has three parts:
- **Say:** what to say, in plain words.
- **If asked:** short answers to the likely follow-up questions.
- **Done in v2 / To do:** what changed in the v2 deck, or what you still need to change.

### 1. Title
- **Say:** "HomeRehab AI is a home physiotherapy coach. It watches exercises through the phone camera, speaks Egyptian Arabic, and knows when not to speak."
- **To do (only you can):** fill in member 2 and the ID. Say "formerly Qawam" only if asked.

### 2. Introduction 1: recovery happens at home
- **Say:** "In the clinic, the physio corrects every movement. At home, the patient is alone with a paper sheet or a WhatsApp video, and the physio sees nothing until the next visit."
- **If asked about the 7 of 10 trials:** a systematic review of 10 randomised trials (Lang 2022). Digital support raised adherence mostly in the short term. Say "short term" yourself.

### 3. Introduction 2: a phone can now see the body
- **Say:** "A free model from Google finds 33 points on the body, on the phone itself. From those points we calculate joint angles, such as knee bend or arm raise, and count repetitions."
- **Doctor-friendly picture:** "It is like a goniometer that measures every repetition, but only when the camera angle allows it."

### 4. Motivation 1: the need
- **Say:** "2.41 billion people need rehabilitation (Lancet 2020). In Egypt, 85% of 299 physiotherapists surveyed said telerehabilitation would improve care, and they named awareness and internet as the barriers."
- **If asked:** both numbers come from cited studies, [6] and [7], listed on slide 33.

### 5. Motivation 2: why now
- **Say:** "Companies have proven the demand: Sword bought Kaia for $285M. But a camera that always talks will sometimes be wrong, and a wrong correction teaches bad form. That is the gap we fill."

### 6. Problem definition
- **Say it as one sentence per row:**
  - P1: no feedback at home.
  - P2: the wrong camera angle gives wrong angles (leg abduction filmed from the side is 43–48° off).
  - P3: one rule for everyone barely beats a coin toss (AUC 0.57).
  - P4: no measured progress between visits.
  - P5: language and access.
- **Explain AUC once, simply:** "AUC is how often the method ranks a wrong repetition above a correct one. 0.5 is a coin toss, 1.0 is perfect."

### 7. Objectives
- **Say:** "One objective per problem, each with a number we can measure. The most important is O2: wrong cues at or below 10%."

### 8. Proposed features
- **Say:** "Green means built and tested, today."
- **Done in v2:**
  - **Red-flag check:** change the row to "23 cited phrases + on-device model + temperature rule. Demo, not physio-reviewed."
  - **Arm abduction:** add the note "counts reps only (cues off after the external test)".

### 9–11. Literature: BlazePose, KIMORE, Liao et al.
- **Say for each:** "what they did, what they found, and what they leave open", ending with the gap we fill.
  - **BlazePose:** good keypoints on single images, but no joint angles over a repetition and no "don't trust this" signal.
  - **KIMORE:** clinical scores, but needs a depth sensor and scores offline.
  - **Liao:** one model for everyone, healthy people simulating errors, no live feedback.

### 12. Existing solutions
- **Say:** "Camera coaching exists. What nobody reports is when their coach should stay silent, and few use the patient's own reference."
- **If asked about Limb (Abu Dhabi):** they are closest to us: Arabic, camera feedback, physio report. Our difference is a published wrong-cue rate and a reference recorded by the physio for this patient.

### 13. Our contribution
- **Say:** "Three things":
  1. a gate that stays silent when the view is wrong, with a measured wrong-cue rate;
  2. each patient compared with their own physio-approved repetition;
  3. phone placement tested on real patients' skeletons.
- **Done in v2:** add one line under 02: "works when the physio records the reference; a patient's own early recording is not enough (KERAAL)". This is now an honest condition (see Part 2 and slide 25).

### 14. Proposed solution: five steps
- **Say:** "Prescribe, set up, exercise, feedback, review. The video never leaves the phone."

### 15. Datasets
- **Say:** "We test on public data recorded with motion capture, so we know the true angle, and always on people the system never saw."
- **Done in v2:** the slide lists 3 datasets. We now use 6 public datasets, plus synthetic notes for the pain check:

| Dataset | What it gives us |
|---|---|
| REHAB24-6 | angle accuracy by view, the view gate |
| REHAB26 | personal vs universal reference at every angle |
| KIMORE | patients' skeletons, phone placement |
| UCOPhyRehab++ | physio scores, rep counting |
| **Fit3D** | 8 new people, 4 cameras, motion capture: external test of the gate |
| **KERAAL** | 6 real low-back-pain patients, 2 clinicians' labels |

### 16. Methodology
- **Say:** "Camera → 33 points → the angle for this exercise → repetitions → view check → compare with the reference → speak or stay silent."
- **If asked about the 0.178 / 0.601 numbers:** they measure how much the person faces the camera (shoulder width divided by torso length). Learned from labelled data, then tested on new people without refitting.

### 17–20. Architecture and UML
- **Say:** "Everything solid is built and tested. Dashed is next semester: the server and the physio portal."
- **If asked whether the diagrams are real:** "The class names match the code; you can open them." Have `web/src/exercise/liveCoach.ts` ready.

### 21. Results 1: the view gate
- **Say:** "On people it never saw, the coach spoke on about a quarter of repetitions, and only 4.2% of what it said was wrong. On the rest, it stayed silent."
- **Done in v2:** the Fit3D result has its own slide (24): the knee rule held on new people and cameras, with 0 wrong cues. Point to it from here.

### 22. Results 2: the personal reference
- **Say:** "Comparing with the patient's own correct repetition catches deliberate mistakes much better than one rule for everyone: AUC 0.68–0.93 vs 0.48–0.69 across the five exercises."
- **Done in v2:** the KERAAL result (slide 25). It sets the condition on this result.

### 23. Results 3: KIMORE patients
- **Say:** "With the phone side-on, we keep the hospital sensor's accuracy (1.7° error). Facing the phone, the error is 36°. So the app insists on the right placement."

### 27. Expected outcomes
- **Say:** "A working coach, a safety number, measured accuracy against a goniometer, and clinic validation with interviews and a pilot."

### 28. Requirements
- **Say:** "Any phone with a camera. No sensors, no GPU. Built with standard web tools; works offline."

### 29–32. Gantt chart
- **Say:** "Research and prototype are done. Next are clinic interviews, then the goniometer study after ethics approval, then the server and portal, then a 4-week pilot."
- **If asked whether you are on time:** yes. The research and prototype tasks finished early. The ethics approval is the only external dependency.

### 33. Work division
- Fill in member 2.

### 34. Risks
- **Say:** "Our biggest risk is clinical approval, so no value is used without a source, and only a named physio can approve a rule."
- **Done in v2:** add "Arm-raise accuracy (found by our own external test): cues switched off until certified."

### 35. Ethics, safety and privacy
- **Say:** "The app never pretends to be a clinician. Video stays on the phone. When unsure, it stays silent. For danger words in a pain note, it tells the patient to stop and call 123, and it never dials by itself."

### 36. References
- **Done in v2:** add Fit3D, KERAAL (Nguyen et al., IJCNN 2024), UCOPhyRehab++ and the NHS fever page.

### 37. Live demo
- **Have ready on your phone:**
  - The **Pain check** tab with "الدنيا بتلف بيا". The model catches what the word list misses.
  - A squat side-on: count plus cue.
  - Arm abduction: it counts reps but gives no corrections. Explain why: "our own test found it unsafe".

### New slides 24, 25, 26 (added in v2, right after the results)
- **24 (Fit3D): "We tested ourselves on new people and cameras (Fit3D)."**
  - Knee exercises: silent on all 608 diagonal-view repetitions, where speaking would have been wrong 70% of the time. **0 wrong cues.**
  - Arm abduction: 34% of cues would have been wrong, so **we switched them off**.
  - We found a signal that fixes it, the arm shortening in the image (AUROC 0.75). It cuts wrong cues from 30% to 11%, but 7 people are too few to certify it yet.
- **25 (KERAAL): "First result on real patients (KERAAL)."**
  - Two clinicians agree on only 77% of patient verdicts. Even experts differ, so the system should flag clear errors and let the physio judge.
  - Within each exercise, a healthy reference averages AUC 0.55 (0.84 on hiding face only), and the patient's own *early* recording 0.29. Our best explanation for the second: the patients were still learning. We also trained a small model (0.55); it did not beat simple baselines, so it is not in the app.
  - So the reference must be recorded by the physio when the patient does it well. That is our design.
- **26 (pain check): "Egyptian Arabic pain check."**
  - The word list alone caught 14 of 40 test red flags; with the 58 KB on-device model, the check caught 39 of 40.
  - It only adds alerts and never removes one.
  - Temperature rule: 38 °C or above (NHS). Negation handling: "مفيش دوخة" is not an alarm.
  - Notes are synthetic, so the next step is physio review and real notes.

---

## Part 2: questions to expect, with honest answers

### About the data
- **"Where does your data come from?"**
  - Six public research datasets, all recorded with motion capture or clinicians' labels, so we know the truth: REHAB24-6, REHAB26, KIMORE, UCOPhyRehab++, Fit3D and KERAAL.
  - Plus 121 synthetic Arabic pain notes, labelled as synthetic.
  - No real patient was recorded by us yet: that needs MSA ethics approval, which is in the plan.
- **"10 people is very few."**
  - "Yes, for a clinical claim, and we don't make one. That's why every number is per person, with the worst person reported."
  - "And it's why we tested on four more datasets with nothing tuned on them: KIMORE, UCOPhyRehab++, Fit3D, KERAAL."
- **"Are these patients or healthy people?"**
  - Mostly healthy adults. Patients appear in KIMORE (34) and KERAAL (6 with low-back pain).
  - Healthy-adult results are upper bounds, and we say so.
- **"How do you avoid cheating on the test?"**
  - We split by person, never by repetition.
  - Two REHAB24-6 people are sealed: the code refuses to open them without a `--final` flag, and every access is logged.
  - External datasets are used without refitting anything.

### About the models
- **"What model did you train?"**
  - Pose comes from Google's pretrained MediaPipe model; we don't retrain it.
  - What we built is small and explainable: two view thresholds, a one-repetition calibration, a statistical certificate on the wrong-cue rate, and repetition comparison by dynamic time warping. That last one needs no training at all.
  - **The one trained model:** the pain red-flag model, logistic regression on letter patterns, 58 KB, runs on the phone.
- **"Why not deep learning?"**
  - Four reasons:
    1. Ten people cannot train a deep model that generalises.
    2. Published work shows deep models collapse when moving from lab 3D to phone 2D (63% → 1.6% accuracy, Khanal & Zhou 2026).
    3. A physio must be able to see why a cue was given.
    4. It must run offline on a cheap phone.
  - "We do plan to compare against an Arabic BERT for the pain notes, as a ceiling."
- **"What is AUC / false-cue rate / 95% upper bound?"**
  - **AUC:** how often a wrong repetition is ranked above a correct one; 0.5 is chance.
  - **False-cue rate:** of the corrections the app spoke, how many were wrong.
  - **95% upper bound:** "even in a bad case, the true rate is very likely below this number".

### About the contribution
- **"What is new here? MediaPipe and DTW already exist."**
  - "The parts exist. What we add is *when to trust them*: a gate with a measured, bounded wrong-cue rate, which we found in no published rehab-feedback study."
  - "And a reference that belongs to the patient, on one phone, in Egyptian Arabic."
  - Say "we found none", not "none exists".
- **"How is this better than published studies?"**
  - They make the assessment more accurate offline; we make the feedback safe to act on, live.
  - Example: a Kinect 3D-CNN study gets 83.8% accuracy but always answers. We speak on about a quarter of repetitions, with 4.2% wrong, and say nothing on the rest.
- **"How is this different from Limb or Kaia?"**
  - Neither publishes how often its coach is wrong.
  - We publish it per person, and we switched off an exercise when our own test failed it.

### Testing the edge we claim ("prove it")
- **"Does the gate really work outside your dataset?"**
  - Yes for knees: on Fit3D (8 new people, 4 new cameras), 0 wrong cues.
  - No for arm abduction, and we acted on it: cues are off until a new signal is certified.
- **"Does the personal reference work on real patients?"**
  - Honest answer: with a reference the patient recorded early, no (KERAAL, AUC 0.29), because patients were still learning.
  - Our design requires the physio to record the reference when the patient does it well; that still needs a clinic test, and it is in the pilot plan.
- **"Does the app grade quality like a physio?"**
  - No, and no method we tested does (UCOPhyRehab++: Spearman 0.14–0.22). Even two clinicians agree on only 77% of patient verdicts.
  - So the app flags clear errors and range drops, and the physio judges.
- **"What if the app misses a dangerous symptom?"**
  - The pain check is a safety net, not a diagnosis. The screen says "no flag does not mean you are fine".
  - It combines a cited word list, a model that only adds alerts, and a temperature rule.
  - On synthetic notes it caught 78 of 81 red flags. Real notes and physio review come next.

### Informal and "is it enough?" questions
- **"Is this graduation-worthy? How advanced is it?"**
  - It's a working, installable app with a live camera coach for five exercises, Arabic voice, a progress report and an on-device language model.
  - It's tested on six datasets with person-level statistics, over 250 automated tests and CI on every change.
  - It includes negative results we acted on. "That last part is what research looks like."
- **"What is the barrier to entry? Can't a big company copy this?"**
  - A camera is easy to copy. Three things are harder:
    1. the measured trust: certified wrong-cue rates per exercise and view, which needs data and statistics, not code;
    2. the clinic workflow, with the physio's reference and Egyptian WhatsApp delivery;
    3. our own consented Egyptian recordings over time. Public datasets are non-commercial, so a clean data licence is itself a moat.
- **"Will clinics pay for this?"**
  - Not proven yet, and we say so. The next step is 10 physio interviews, a price question and letters of intent, before building more.
- **"Is it safe to give to patients now?"**
  - No: it's a prototype. No physio has approved a value, and every clinical number is labelled with its source.
  - The plan is healthy volunteers first, then a supervised pilot.
- **"Why Arabic voice? Why WhatsApp?"**
  - Egyptian physios named awareness and connectivity as the barriers.
  - Arabic voice keeps hands free, WhatsApp is where patients already are, and offline works on weak internet.
- **"What was the hardest part?"**
  - Learning to measure when *not* to speak.
  - Example: Fit3D showed our arm-raise rule was unsafe, so we switched it off instead of hiding it.
- **"What would you do with more time?"**
  - Certify the arm signal with more data.
  - Run the goniometer study (20 volunteers).
  - Have a physio review the pain-check labels and collect real notes.
  - Build the physio portal, then run the 4-week pilot.

---

## Part 3: before the day
- Fill in names, IDs and the supervisor on slides 1 and 30.
- Open v6 and check each new or changed slide (8, 13, 15, 19, 21–26, 28, 30, 34, 36) looks right on your screen.
- Rehearse the live demo on your phone with airplane mode on (offline).
- **Keep open:**
  - `docs/experiments.md`, every number with its method;
  - `web/src/exercise/liveCoach.ts`, if asked to show code;
  - the GitHub Actions page, showing green CI.


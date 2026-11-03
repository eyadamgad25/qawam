# ML roadmap: models, data and APIs to add (GP2)

Written 2026-11-03. Each idea keeps the project's edge — **silent rather than wrong, on one phone, in Egyptian Arabic** — instead of replacing it with a bigger model. Every model output still passes the certified gate; no model can create or remove a red flag.

## Ranking

| # | Addition | Model | Data | Where to train | API / key | Effort | Value |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Gate 2.0: learned "can I trust this angle?" score | Gradient boosting (LightGBM) on per-rep features, then Learn-then-Test certification | Fit3D (13 people x 4 camera views, mocap truth) + REHAB24-6 | Laptop CPU | Fit3D account (have) | 2-3 weeks | Highest: fixes the known weakness (5 people could not certify learned scores) |
| 2 | Error type: say *what* is wrong, only when sure | Small 1D-CNN / GRU on angle sequences (< 100k parameters), selective output | REHAB26 error types, REHAB24-6, KERAAL (patients, physio-labelled error type and body part) | Colab or Kaggle GPU | None (KERAAL is a free download) | 3-4 weeks | High: turns "different from reference" into "knee caving in", with a certified wrong-label rate |
| 3 | Egyptian-dialect pain notes | Fine-tune EgyBERT / MARBERT for body part, side, pain type, intensity; lexicon OR model for red flags | Synthetic notes (LLM-generated, labelled "synthetic") + a physio-reviewed test set | Colab GPU | Hugging Face (free); Claude API for synthetic data and a baseline | 3-4 weeks | High: contribution C5, red-flag recall as the metric |
| 4 | Voice pain diary | Whisper fine-tuned on Egyptian Arabic (e.g. whisper-medium-egy, reported CER 13.4%) feeding #3 | Own consented recordings for testing | Inference only | Hugging Face; or a hosted speech API | 1-2 weeks after #3 | Medium-high: older patients speak more easily than they type |
| 5 | Physio report drafted from session data | LLM with JSON input and a numbers check (every sentence names its source field) | Session store (synthetic in the demo) | None | Claude API | 1 week | Medium: saves physio time; no advice, only facts |
| 6 | Loose-clothing robustness (galabeya, abaya) | Compare MediaPipe with YOLO11-pose / RTMPose; fine-tune only if MediaPipe fails | Own clips labelled in Roboflow + Roboflow Universe keypoint sets | Colab GPU | Roboflow (annotation + export) | 2-3 weeks | Medium: Egypt-specific edge Limb also points to |
| 7 | 2D-to-3D lifting (MotionBERT) offline study | Pretrained lifter, evaluated only | Fit3D, REHAB24-6 mocap | Colab GPU | None | 2 weeks | Research only: tests whether 3D removes the camera-angle limit; literature warns lower position error does not mean better joint angles |
| 8 | Learned rep counter | PoseRAC-style transformer | RepCount (pose version), Fit3D reps | Colab GPU | None | 2 weeks | Low: the rule already reaches MAE 0.56 reps on UCOPhyRehab++ |

## Why this order

1. **#1 first.** It is the core contribution made stronger, it needs no new labels (Fit3D gives exact angles from 4 views), and it runs on a laptop. Success = a certified false-cue rate at or below 10% with more of the reps spoken than the current rule (26.5%).
   - **Status 2026-11-03 (first Fit3D run, `docs/experiments.md`):** not met. The rule held for knees (silent on every diagonal view), failed for shoulder abduction (false-cue rate 0.34), and the learned gate certified nothing. Next: find a signal that predicts arm-angle error (out-of-plane arm motion, elbow depth from MediaPipe's z, wrist visibility) and add a Fit3D test split by person before certifying.
2. **#2 next**, because cue wording is what patients and physios notice. It only speaks an error type when the selective model is confident; otherwise it falls back to today's "different from your reference".
3. **#3 and #4 together** make the Arabic edge measurable: red-flag recall and entity F1 on a physio-reviewed set.

## How each is tested (same rules as today)

- Split by person; leave-one-person-out; sealed test people; report the worst person.
- Models must run in the browser: export to ONNX and run with onnxruntime-web, or reimplement small models in TypeScript.
- Compare against today's rule, not only against other models.

## Data sources checked

- **Fit3D** (fit3d.imar.ro): 13 people, 4 RGB cameras + Vicon, 37 exercises. Non-commercial, single user (each team member registers).
- **KERAAL**: low-back-pain clinical study (Nguyen et al., IJCNN 2024): 12 patients and 9 healthy people, 3 exercises, RGB video + Kinect + BlazePose/OpenPose skeletons (Vicon only in group 3), errors labelled by a physiotherapist and a rehab doctor with type, body part and time span. CC BY-NC-SA, direct download from http://nguyensmai.free.fr/KeraalDataset.html (groups 1A and 2A downloaded 2026-11-03).
- **Roboflow Universe**: small exercise keypoint sets, e.g. "squat keypoint detection" (correct / incorrect / standing, CC BY 4.0). Quality unknown; useful for clothing and home-condition tests, not as a main dataset. Roboflow's main value is labelling our own clips.
- **Kaggle**: "Workout/Exercises Video" (exercise classification, no form labels). Kaggle notebooks also give free GPU hours, an alternative to Colab.
- **Egyptian Arabic text and speech**: EgyBERT (Egyptian tweets and forums), CairoDep (Egyptian posts, MARBERT F1 about 96%), Whisper fine-tunes on Egyptian speech (self-reported scores; test on our own audio).
- No public Egyptian-Arabic pain or symptom dataset was found: our own physio-reviewed set would be a contribution in itself.

## Keys and accounts

- Kaggle, Roboflow, Hugging Face and the Claude API keys stay on your machine: put them in `.env` (git-ignored) or `~/.kaggle/kaggle.json`; never in chat or in the repo.
- Colab: free tier is enough for #2, #3, #6-8 (small models); upload derived features, not raw videos, to keep data local.

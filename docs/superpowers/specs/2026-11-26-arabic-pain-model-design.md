# Arabic pain model: a large Arabic language model teaches the small one on the phone

Date 2026-11-26. Chosen by the project owner after comparing five options (`docs/experiments.md`, 2026-11-25 and this
conversation): it fixes a failure we measured, and it uses Kaggle's graphics card for real NLP work.

## Why
The pain check now on the phone (64 KB character n-gram model) misses 6 of 26 warning signs in bone and muscle titles and
8 of 94 overall, and flags 29 of 156 ordinary texts (`docs/experiments.md`, 2026-11-25). Large Arabic language models
understand wording that character n-grams cannot, but at 650 MB they cannot run on a phone, and the app must work offline.

## Goals
1. Measure how much a modern Arabic language model improves the check.
2. Bring as much of that gain as possible to the phone without a server.
3. Keep the rules of the current check: the word list is never overridden, the model only adds alerts, and the note
   before use states the measured errors.

## Non-goals
No diagnosis, no free-text answers, no server needed for the check, no patient text used for training.

## How it works: teacher and student
```
Kaggle notebook (free graphics card; dataset attached on Kaggle, code cloned from the public repository)
  1. same training labels as today: even-numbered Shifaa titles (symptom categories vs ordinary) + the synthetic notes
  2. fine-tune two teachers: MARBERTv2 (best in a 2026 Arabic medical shared task; licence not stated)
                             CAMeLBERT-DA (dialect model, Apache 2.0)
  3. each teacher scores every Shifaa title (about 55,000) → teacher_scores.csv (numbers only, small)
laptop
  4. student = the app's own character n-gram model, trained to copy the teacher's scores on all 55,000 titles
     plus the synthetic notes (knowledge distillation): still about 64 KB, still in the browser, offline
  5. one test, once, on data no model has seen (below)
```
The teacher never ships. If the student does not keep the gain, the result is reported and the app keeps today's model.

## Data for the test (fixed before any new score)
- **New blind set:** 300 odd-numbered titles **not** in the earlier 250 (which were used once already), drawn by a fixed
  seed: 180 bone, muscle and sports, 120 from symptom categories. Labelled by the AI assistant with the same written
  codebook, before any model is trained, and frozen in a file. Done 2026-11-26: 105 of 300 "yes";
  `data/derived/shifaa/labels2.json`, SHA-256 `fca3e1bfe77494376ba8afb46ea373a9827b6688d07cec4263360e7e3990c79d`.
- **Clinician labels:** the doctor's 60 labels on the labelling sheet, used to measure how often the assistant's labels agree
  with a clinician. If agreement is low, every number is reported as "against non-clinician labels".
- **Synthetic notes (Egyptian dialect, AI-generated):** reported, but not a pass criterion, because training notes share their wording.

## Pass rule
The **student** replaces the phone model only if, on the new blind set, at a threshold set beforehand on held-out even
titles so that it flags no more ordinary texts than today's model does there:
1. it catches more warning signs than today's model, with a 95% interval for the gain above 0 (resampling titles); and
2. on bone, muscle and sports titles it misses no more than today's model.

Only the student taught by CAMeLBERT-DA can ship (fixed 2026-11-26, before any score: one test, not two, and a licence that
allows it); the MARBERTv2 student is reported only. The threshold is matched on the model alone (word list and temperature rule
are the same for both); the interval comes from 2,000 resamples of the 300 titles, seed 20261126. Distillation uses every title
except the held-out even ones and both blind sets (removed by number and by normalised text), plus `training-notes.jsonl`;
titles and notes count equally in total. Teachers are reported as the ceiling. A teacher may later run on a server (GP2) only if it clears the same rule and its
licence allows it; MARBERTv2 stays research-only until its licence is confirmed.

## Constraints
- Kaggle: free account with phone verification for the graphics card; the notebook runs with **Save & Run All**, private.
  Shifaa is attached on Kaggle, so nothing is uploaded from the laptop.
- The teacher outputs are scores, not text, so no consultation text leaves Kaggle.
- The note before use is updated only from a new test result.

## Approaches considered
1. **Teacher on Kaggle, student on the phone (chosen):** NLP depth plus offline use; the phone model stays 64 KB.
2. **Run a transformer in the browser (ONNX, transformers.js):** hundreds of MB, slow on cheap phones; rejected for now.
3. **Teacher on a server:** best accuracy, but needs a network, a server (GP2) and consent; kept as a later option.

## Left to the builder
Training settings for the teachers (fixed in the notebook before the test), the distillation loss, and the exact split of
held-out even titles used for the threshold.

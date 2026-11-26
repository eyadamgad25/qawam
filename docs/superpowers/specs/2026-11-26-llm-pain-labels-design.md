# LLM labels for the Arabic pain check: better labels, same models

Date 2026-11-26. Chosen by the project owner after the distillation test (`docs/experiments.md`, 2026-11-26) showed that even
650 MB Arabic models catch at most 3 more warning signs of 105 than the 64 KB phone model: every model learns the diagnosis
category, and a category does not say whether the title states a symptom now.

## Why
Change only the training labels, keep every other part as it was, and measure once whether better labels improve the phone
check. Uses an open LLM for a job it is suited to (reading a title against a written codebook) without putting it in the app.

## Goals
1. An open LLM on Kaggle labels titles with the codebook in `docs/superpowers/specs/2026-11-25-pain-check-real-text.md`.
2. Use its labels only if they agree with trusted labels better than the category labels do.
3. Retrain the CAMeLBERT-DA teacher and the 64 KB student on them, then test once against today's phone model.

## Non-goals
No LLM in the app or on a server; no change to the word list, temperature rule, negation or the note before use unless the
student passes; no new symptoms; no free text from the LLM.

## Anti-goals (a failure even if it works)
- Prompt or model chosen by looking at the gate set or the test set.
- A blind title (any of the three sets) in the LLM-labelled training titles.
- Shifaa text written to the notebook output, git or the reports.

## Approaches
Also considered: the AI assistant labels the 8,884 training titles in chat. Rejected: slow, not reproducible, and the same
labeller would write both the training and the test labels.
- **A. LLM labels a sample, BERT teacher learns from it, the student copies the teacher (chosen).** Small LLM run; reuses the
  teacher notebook and distillation unchanged; the only difference from the last test is the label source.
- B. LLM scores all ~48,000 titles and is the teacher: one model fewer, about six times the LLM run, harder to recover.
- C. Student trained on the LLM labels directly: simplest, but about six times less data for a small character model.

## How it works
```
laptop   1. third blind set: 400 odd titles not in the first two (240 bone/muscle/sports, 160 symptom), seed 20261127,
            labelled by the AI assistant with the codebook BEFORE any LLM output exists; frozen with its SHA-256 here.
            Done 2026-11-26: 119 of 400 "yes"; labels3.json SHA-256
            b179fc32a87619a721caa43c48d0c48b6ebf256eb10e8ccc78c72b83a948d8a2
Kaggle   2. LLM: Qwen2.5-7B-Instruct (Apache 2.0), half precision split across the two T4s (about 15 GB, more than one T4 holds). P(yes) = softmax of the "yes"/"no"
            answer tokens. Prompt = the codebook's nine signs and the "in general / denied / over = no" rule, title last
            Run 1 scores blind sets 1 and 2 and the 8,884 training titles of teacher_data.training_set → llm_scores.csv
laptop   3. development: the yes-threshold is chosen on blind set 1 (250) only, to maximise macro-F1 there
         4. gate, once, on blind set 2 (300): the LLM at that threshold vs the assistant's labels
Kaggle   5. run 2: the training titles get the LLM's 0/1 label at that threshold (same titles, new labels; notes keep theirs,
            class weighting unchanged); CAMeLBERT-DA fine-tuned with the same settings; every title and note scored
            → teacher_scores_llm.csv. Run 1's output is attached to run 2 as a Kaggle input
laptop   6. distil the student exactly as before (distill_student.py), threshold matched to today's flag rate
         7. one-time test on blind set 3
```
Only numbers leave Kaggle: one P(yes) per training title and blind title, and the teacher scores.

## Pass rules, written before any LLM output
- **Gate (step 4):** Cohen's kappa with the assistant's labels >= 0.60, and higher than the kappa of the category label
  (symptom category = yes) on the same 300 titles. If it fails, stop and report; no second model or prompt is tried.
- **Ship (step 7):** against today's phone model on blind set 3, at a threshold matched to today's flag rate on held-out
  ordinary titles: macro-F1 gain with a 95% interval above 0 (2,000 resamples of the 400 titles, seed 20261127), and no more
  misses on bone/muscle/sports titles. Measured once. Macro-F1, not recall as in the distillation test, because today's check
  already catches 92 of 105 there, so better labels can show mostly as fewer false alarms (fixed before any LLM output).
- Also reported: the LLM's own scores on blind set 3 (the ceiling), the student from category labels (already built) on blind
  set 3, synthetic test notes, and agreement with the doctor's 60 labels when they arrive.

## Constraints
- Kaggle GPU T4, Internet on for the model download, notebook private, code cloned from the public repository.
- Qwen2.5-7B-Instruct is Apache 2.0; the LLM never ships either way. CAMeLBERT-DA (Apache 2.0) is the only teacher.
- Labels by the AI assistant, not a clinician: every number is "against non-clinician labels" until the doctor's 60 are in.

## Left to the builder
Exact prompt wording (fixed in code and committed before run 1; never changed after seeing a score), batching and memory
settings, and the answer tokens. Builder's calls already made: the prompt is not tuned on any labelled set (only the threshold
is, on blind set 1), because tuning wording needs repeated runs and invites fitting the labels; the teacher gets 0/1 labels
rather than probabilities, so that the label values are the only change from the last test.

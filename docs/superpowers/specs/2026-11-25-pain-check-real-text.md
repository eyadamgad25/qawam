# Testing the pain check on real Arabic text: rules written before any score

Date 2026-11-25. Data: Shifaa Arabic Medical Consultations (Kaggle, Apache 2.0, 84,422 consultations), in git-ignored
`data/raw/shifaa`. No patient names; it holds doctor names and personal stories, so texts are never committed or quoted, only counts.

## What is tested
The pain check exactly as shipped (word list, 38 °C rule, model), run through the app's own TypeScript. Nothing is tuned first.
The unit is the question **title** (about 8 words), the closest thing to a pain note. Full questions (about 80 words) are reported only
as a stress test: the check was not built for them.

## Two labels
1. **Category label (large, rough).** Symptom categories = chest pain, heart pain, shortness of breath, dizziness, fainting, numbness,
   swollen feet, stroke. Ordinary categories = muscle strain, low back, neck, knee pain, shoulder, sports practice. A title in a symptom
   category need not state the symptom, and an ordinary one may.
2. **Blind label (small, careful).** 150 random titles from bone, muscle and sports consultations (the people this app is for) and 100
   from the symptom categories, shuffled, labelled without seeing any prediction or category: does the title state that one of the nine
   symptoms is present now (chest pain; difficulty breathing; calf pain or swelling; fever or shivering; wound discharge; swollen, hot or
   red knee; numbness or tingling; dizziness or fainting; sharp, sudden or severe pain)? A question about a symptom in general, or one that
   is denied or over, is "no". Labelled by the AI assistant, **not by a clinician**.

## Judged as
- **Useful:** on the blind labels, recall >= 0.80 and at most 20% of ordinary titles flagged.
- Otherwise the result is reported as a failure of the current check on real text.

## If a new model is trained
Only on consultations whose number is even; the blind sample is drawn from odd numbers. Trained model and word list stay separate, as now.
It replaces the shipped model only if, at a threshold fixed on the even half, it is better on the blind titles **and** not worse than the
shipped one on the synthetic test notes (39 of 40 caught, 7 of 19 false alarms).

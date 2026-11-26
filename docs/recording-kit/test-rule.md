# Test rule for the two-day recordings (fixed before any recording)

Written 2026-11-25. Method: three reference reps and the per-patient cut-off of `ml/eval/quality_model.py`, with the cut-offs already
frozen in `ml/eval/confirm_cuts.json`. Nothing is fitted on these recordings.

- **Reference:** the first 3 detected reps of each person's **day 1** `ok` video, per exercise. Never scored.
- **Scored, main result:** every detected rep of the **day 2** `ok` and `fault` videos. Both come from day 2, so a different day, phone
  position or clothes cannot tell them apart.
- **Scored, for comparison:** the rest of day 1.
- **Rep detection:** automatic. A video whose detected count is not 7, 8 or 9 is left out and listed. If more than a quarter of the
  videos are left out, the test does not count.

## Pass, all of these, on day 2, at least 8 people
1. Correct reps called wrong: at most **20%**, and the upper end of the 95% interval (resampling people) at most **35%**.
2. Faulty reps caught: at least **70%**.
3. Macro-F1 better than the plain cut-off, with the 95% interval of the gain above 0.

Also reported: each exercise and each person, worst person, the plain method, and the same with the starting posture removed.

## What happens
- **Pass:** the three-rep reference may be built into the app for the exercises that were tested, still labelled as not reviewed by a
  physiotherapist. Healthy volunteers do not show that it works on patients.
- **Fail:** it stays research, and the numbers are reported. No second attempt on the same recordings.

# Confirming the three-rep reference with a per-patient cut-off: written before any new score

Date 2026-11-25. Method and code as in `ml/eval/quality_model.py` (K = 3, `dtw_z`), nothing changed. The two cut-offs (plain
DTW and per-patient) are the best macro-F1 values on IntelliRehabDS + REHAB24-6 + REHAB26 pooled, K = 3, computed once by
`confirm_reference.py --freeze` and stored in `ml/eval/confirm_cuts.json` before the new data is scored.

## New data
1. **PhysioLens** (Kaggle, CC BY 4.0): 5 healthy people, side leg raise, webcam + MediaPipe. One correct session each, two to
   three sessions with a deliberate fault, some on another day. Reference = first 3 reps of the correct session, per leg. Image
   shape is not recorded: 4:3 assumed, 16:9 as a check.
2. **KERAAL group 1A**: 6 low-back-pain patients over time, two clinicians. Reference = first 3 recordings of an exercise both call
   correct. Used before with a one-recording reference, which failed (AUC 0.29), so it is a hard test and not fully fresh.

## Known weakness, and its control (PhysioLens)
Correct and wrong reps come from different recordings, so a method could detect the recording, not the fault.
- Control 1: AUC of the same distance on the posture at the start of the rep only. Near the method's own AUC = suspect.
- Control 2: the same frozen test after subtracting each rep's own starting posture.
- Faults on another day are reported separately from faults on the same day.

## Pass rule (all must hold)
1. PhysioLens macro-F1 of the per-patient cut-off >= 0.70, and better than the plain cut-off with a 95% interval above 0.
2. Correct reps called wrong <= 20% on PhysioLens.
3. Control 2 also reaches macro-F1 >= 0.70.
4. KERAAL: mean AUC within exercise > 0.5 with the lower end of its 95% interval above 0.5.

If 1-3 hold but not 4: usable only as a same-day, healthy-person result; it does not judge patients over weeks.
If 1-3 fail: the method stays research. Either way nothing is tuned afterwards and no second attempt is made on this data.

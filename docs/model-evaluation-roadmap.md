# Model evaluation roadmap

## Current evidence and its limits

The current browser prototype is reported to use MediaPipe Pose Landmarker
Lite for local 2D inference, with uploads capped at two minutes and analysis
sampling capped at 24 frames. These prototype details were supplied from
prior work; browser model wiring is not independently verified in this
checkout.

The supplied derived REHAB24-6 exports contain 1,015 training frames from
subjects 3, 5, 6, and 8, and 300 validation frames from subject 4. The test
split was not accessed. The analysis is reproducible with
`py -3.14 ml/eval/summarize_view_robustness.py`; its report is
`docs/eval-confidence-coverage.md`. Direct 2D keypoint error normalized by
frame diagonal ranged by exercise/camera/view group from 0.58–4.10% on train
and 0.56–2.82% on validation. These are pose localization errors, not
exercise-correctness accuracy, rep-count accuracy, or clinical performance.

Exploratory visibility filtering retained 94.8% of train frames and 91.7% of
validation frames at mean visibility >= 0.70. Mean normalized error changed
from 1.66% to 1.54% on train and from 1.03% to 0.87% on validation; nearest-rank
p90 changed from 2.65% to 2.15% and from 1.60% to 1.16%. At >= 0.80, coverage
fell to 86.4% and 80.7%; conditional mean error was 1.53% and 0.88%, with p90
2.15% and 1.19%. All sampled Ex1 Camera18 profile frames were excluded at
either threshold. These thresholds are descriptive only, are not validated
operating points, and must not be implemented as clinical gates. Results are
reproducible from the supplied frame-level exports, but remain exploratory
and sample-limited.

## Comparison with REHAB26-ViewAngles

| Aspect | Qawam (reported prototype / REHAB24-6 exploration) | REHAB26-ViewAngles study |
| --- | --- | --- |
| Pose model | MediaPipe Pose Landmarker Lite; browser, local 2D inference | MediaPipe Pose v0.10.20 Full for the released 33-joint sequences |
| Data and views | REHAB24-6; the reported frame comparison uses a subset of train and validation subjects | 1,665 labeled repetitions, 5 participants, 3 synchronized cameras, and 29 viewing angles |
| Main reported measure | 2D keypoint localization error normalized by image diagonal; confidence/coverage summaries | Separation of correct and incorrect repetitions using personalized movement features |
| Reported headline | 0.58–4.10% train and 0.56–2.82% validation normalized keypoint error across groups | Best single 2D camera view improved separability by 16.9% over frontal; two-view combination improved it by up to 13.1% |

The study's 16.9% and 13.1% are relative separability improvements, not
MediaPipe keypoint accuracy or Qawam's exercise-classification accuracy. Its
dataset, model variant, viewpoints, and task differ, so these results are
useful motivation to measure view sensitivity, not a head-to-head benchmark.
The arXiv paper is a preprint/study result and does not validate Qawam or a
clinical threshold.

## REHAB24-6 dataset and model comparison

The [REHAB24-6 Zenodo record](https://zenodo.org/records/13305826) describes
the dataset and its ground truth; it does not itself prescribe a pose model
or publish one aggregate model-accuracy score. Its record lists 65 recordings,
two RGB cameras, 2D/3D projected and mocap-derived skeletons, and 1,072
physiotherapist-labeled repetitions. The associated REHAB24-6 paper compares
pose-estimation methods. Its accessible abstract/search excerpt reports that
MediaPipe Pose has the lowest 3D position error “in general,” while results
vary for other settings. The exact tested MediaPipe variant and numeric
comparison were not verified from the full paper here.

Qawam's exploratory pipeline uses MediaPipe Pose Landmarker Lite v1.1.1 for
the authorized frame overlays; the browser's reported Lite configuration is
not independently verified in this checkout. Qawam's available numeric
result is direct 2D keypoint error normalized by image diagonal on supplied
frame exports, not the associated paper's 3D positional error. Therefore we
cannot say which is more accurate from these numbers. A fair comparison
requires the same frames, landmark correspondence, dimensionality,
coordinate normalization, and error definition; the current 26-to-33
landmark mapping remains UNVERIFIED.

Sources:

- REHAB24-6 dataset record, https://zenodo.org/records/13305826
- Černek, A. et al. (2024), *REHAB24-6: Physical Therapy Dataset for
  Analyzing Pose Estimation Methods*, DOI:
  https://doi.org/10.1007/978-3-031-75823-2_2
- Jánošová, M. et al. (2026), *Impact of Patient Orientation in Single- and
  Multi-View Camera Environments for AI-based Rehabilitation Monitoring*,
  arXiv:2609.35726, https://arxiv.org/abs/2609.35726
- REHAB26-ViewAngles record, https://zenodo.org/records/23018128

## Remaining steps, in order

1. **Resolve joint semantics and alignment.** The primary REHAB24-6 record
   says the 26-joint ground truth was derived from OptiTrack markers and its
   2D coordinates were projected using a simplified pinhole model; it does
   not specify a mapping to MediaPipe's 33 landmarks. The two authorized
   PM_039/PM_101 Camera18 clips favor the existing candidate mapping over
   tested alternatives (1.80% vs 3.85% adjacent-arm shift and 7.14%
   left/right swap over 108 point/frame comparisons), but this small sample
   does not make the mapping canonical. PM_101 also has a one-row
   video/joint-count mismatch (1307 vs 1308); sampled frames 34–36 are
   plausible, while full-sequence alignment remains UNVERIFIED. Obtain a
   source-authored skeleton definition or expert-confirmed correspondence
   before wiring joint IDs into exercise logic.
2. **Measure exercise-relevant baselines.** After correspondence and
   coordinate conventions are sufficiently verified, compute in-plane angle
   error on authorized training data first. Keep pose localization error
   distinct from rep-count and form correctness. Validation requires its own
   explicit evaluation step; keep the sealed test inaccessible.
3. **Complete pose primitives.** Generic 2D angle geometry, causal trailing
   moving average, configurable low/high repetition counter, Python/browser
   visibility gates, synthetic-testable angle-to-repetition pipelines, and
   generic deterministic rule evaluator are implemented. These accept
   explicit caller configuration; no sample values are defaults for an
   exercise. A separately labeled browser experiment now connects MediaPipe's
   shoulder/wrist/hip indices to an arm-raise counter using 45°/120° angle
   bounds and a 0.5 visibility cutoff. Those are software test assumptions,
   not dataset-derived or clinician-approved values; the UI says so.
4. **Complete the record-then-analyze thin slice.** A first real slice now
   accepts a local video of up to two minutes, runs MediaPipe Pose Landmarker
   Lite in the browser, and overlays detected landmarks during playback.
   Video remains local; the page fetches the WASM runtime and model from public
   CDNs. It displays landmarks and a test-only arm-raise repetition count with
   an 8-repetition demonstration target (not a prescription). This is not
   validated exercise analysis and provides no cues. An unsaved in-page
   end-of-clip count/duration summary is available locally; the older session
   summaries and angle sequence remain explicitly synthetic examples. An
   optional user-entered manual count can be compared with the detector's
   count locally; this is a test aid, not a validated benchmark. Next,
   verify overlay alignment for portrait/landscape video, compare the new
   angle/visibility/phase diagnostics between frontal and side views; the
   experimental counter now allows automatic or manually selected left/right
   tracking and resets when the choice changes. Then validate landmark
   behavior and thresholds against authorized labeled
   exercise recordings before treating any count as meaningful.
5. **Complete the evaluation harness.** Produce per-exercise/view results
   for angle MAE, rep-count accuracy, form precision/recall/F1, false-cue
   rate, coverage, and latency. Preserve subject-wise splits and sealed-test
   enforcement.
6. **Freeze the baseline at Milestone 3.** Use validation for decisions,
   report uncertainty and sample sizes, and only access the sealed test for
   the explicitly authorized final evaluation.
7. **Add safety-gated coaching and product milestones.** Integrate and
   validate the configurable visibility gate with pose inference, then connect
   real `cannot_assess` results to the UI; the current abstention screen is
   illustrative only. Add provisional physio-reviewable rules only after
   evidence supports them. Continue with
   confidence gating/setup wizard, clinically reviewed pain/red-flag terms
   and pathway, API/roles,
   physio review, and the remaining core requirements in `docs/AI_BRIEF.md`.
   Keep learned classifiers and other stretch features after the baseline.

## Implemented milestones and next evidence blocker

Confidence/coverage item is implemented and run using the supplied derived CSVs only. The
analysis reports split totals and exercise × camera × view groups for
visibility, pose-detection coverage, direct normalized keypoint-error mean
and p90, and descriptive visibility-threshold coverage/error. It rejects
input rows whose split does not match the expected train or validation
source. No raw data or sealed test split was accessed; no additional raw
data is needed.

The primary record confirms nominal 30 FPS capture and pinhole-projected 2D
ground truth but does not resolve the 26-to-33 landmark correspondence. The
PM_039/PM_101 same-index overlays support portrait coordinates for the
sampled frames; PM_101's one-row frame-count difference keeps overall
synchronization unverified. The best next evidence step is source-authored
joint semantics or expert confirmation—not another ungrounded mapping
guess. Before the browser counter described below, added standalone angle, causal smoothing,
configurable repetition-counting and visibility-gate primitives, then
composed them in a synthetic-testable sequence pipeline. It uses only
caller-supplied landmarks and thresholds; that pipeline added no mapping,
exercise configuration, or coaching behavior. The UI lets a user switch between an
explicitly synthetic completed-session example and a default synthetic
`cannot_assess` example; neither is driven by camera input.

The later experimental counter is connected to the live MediaPipe output for
one generic arm-raise cycle. It uses documented MediaPipe indices, a projected
2D angle heuristic, and displayed test cutoffs; this does not establish
REHAB24-6 correspondence or exercise validity. Its status and caveats are
prominent in the first screen. The 8-repetition figure is a demonstration
target only, not a prefilled result or treatment recommendation.

Added a pure TypeScript rule evaluator that requires caller-supplied rules and
metrics, abstains on failed capture or missing metrics, returns rule
IDs/versions/provenance, and flags provisional matches for the required
prototype warning. It rejects duplicate active versions and invalid approval
metadata. No exercise rules are configured and it is not connected to pose or
the UI.

The web runtime now also has a pure landmark-visibility gate that requires
caller-supplied required joints and cutoff and feeds its result into the rule
evaluator. Both are covered with synthetic tests; neither is connected to
MediaPipe or the UI.

The browser now has the same generic synthetic-testable angle-to-repetition
composition as the Python utilities: 2D angle, causal trailing smoothing,
visibility refusal, and a configurable low/high cycle counter. Missing or
undefined observations break partial cycles. No mapping, exercise values, or
camera integration is included.

Added a configurable pain-text flagging primitive that normalizes Arabic
letter variants, diacritics, tatweel, and Arabic/Persian digits. An exact
configured lexicon hit always escalates for review; an optional model flag can
add escalation but cannot suppress it. Empty text or an absent lexicon returns
`CANNOT_ASSESS`; no lexicon terms are bundled and no clinical conclusion is
made from a non-match. UI and notification wiring remain unimplemented.

The best next evidence step remains obtaining source-authored joint semantics
or expert-confirmed correspondence and resolving the PM_101 frame alignment.
The browser's simple MediaPipe-index arm-raise mapping is only an isolated
engineering experiment, clearly labeled unverified in the UI; it does not
resolve dataset correspondence or validate exercise thresholds. Do not use
its output for treatment decisions.

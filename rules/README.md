# rules/

Versioned JSON exercise rules. Schema lands in Task 6; fields below are frozen in Task 1a-4.

Every clinical number must be a string or value tagged `PLACEHOLDER_NEEDS_PHYSIO_APPROVAL` until a **named human** physiotherapist approves it. **Physio advisor: TBD (unassigned).** No invented names. The demo seed **Demo Physio (not a real clinician)** is not an approver.

## Evidence levels

1. **Provisional default** — `status: provisional`, `provenance: default`. Engineering placeholder, demo only.
2. **Data-derived** — `status: provisional`, `provenance: dataset-derived`. Chosen from REHAB24-6 **training** people only, checked on **validation** people; still provisional (healthy lab adults). Do not use the sealed test split to pick thresholds.
2b. **Literature** — `status: provisional`, `provenance: literature` or a `literatureGoals` entry: a published value with a full citation and an https link. Shown to the physio as context or a display goal; never used on its own to judge a rep, and never presented as approval.
3. **Clinician-approved** — `status: approved`, `provenance: clinician`, `approvedBy` a named human, `approvedAt` set.

No rule may be marked `approved` without that named human. The UI must show **Prototype, not clinically approved** whenever a provisional rule fired.

## Schema (example; not a live rule)

```json
{
  "ruleId": "SQUAT-DEPTH-01",
  "version": 3,
  "exercise": "squat",
  "view": "side",
  "requires": ["LEFT_KNEE", "LEFT_HIP", "LEFT_ANKLE"],
  "condition": {
    "metric": "knee_flexion_min_deg",
    "op": "<=",
    "value": "PLACEHOLDER_NEEDS_PHYSIO_APPROVAL"
  },
  "minConfidence": "PLACEHOLDER_NEEDS_PHYSIO_APPROVAL",
  "cue": { "ar": "انزل أكثر قليلاً", "en": "Go a little lower" },
  "severity": "info",
  "source": "physio advisor / literature ref",
  "status": "provisional",
  "approvedBy": null,
  "approvedAt": null,
  "provenance": "default"
}
```

No rule JSON files committed yet (avoids dummy thresholds looking official).

## Exercise packs (`rules/packs/`)

Each exercise is a pack: landmarks, camera view, angles, rep-counter bounds, reference mode and rule IDs. Schema: `packs/pack.schema.json`; validator: `ml/qawam_ml/packs.py` (`validate_pack`, `load_packs`). `SIDE_` and `OTHER_` in landmark names resolve to the patient's evaluated side and the opposite side. Shipped packs: `lower-limb.squat`, `lower-limb.lunge`, `lower-limb.leg-abduction`, all `provisional` with placeholder rep-counter bounds.

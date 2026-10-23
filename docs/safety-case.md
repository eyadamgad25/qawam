# Safety case (draft)

Status: **scaffold**. Not an approved clinical safety case. Educational prototype.

**Physio advisor:** TBD (unassigned). No invented names. Demo seed account: **Demo Physio (not a real clinician)** — not an approver.

## Evidence levels (thresholds and rules)

Any numeric threshold or coaching rule must carry exactly one of:

1. **Provisional default** — engineering placeholder (`provenance: default`). Demo only. `status` must be `provisional`. `approvedBy` / `approvedAt` stay null.
2. **Data-derived** — cutoff chosen from REHAB24-6 **training** subjects only and checked on **validation** subjects (`provenance: dataset-derived`). The sealed **test** split is not used to pick thresholds. Still **provisional**: REHAB24-6 subjects are healthy adults in a lab, not Qawam patients. `status` remains `provisional` until a named human physiotherapist reviews it.
3. **Clinician-approved** — `status: approved`, `provenance: clinician`, `approvedBy` = a **named human** physiotherapist, `approvedAt` set. The unassigned advisor and the demo seed **cannot** approve.

A rule must not be marked `approved` without that named human. Whenever a **provisional** rule fires in the UI, show a banner: **Prototype, not clinically approved**.

## Intended use

Home exercise **support** under a physiotherapist's plan. Decision support for the physio (review-by-exception, progression *suggestions*). Users: patient/athlete, physio, clinic admin, system admin.

## Explicitly out of scope

- Diagnosis
- Treatment-outcome claims
- Injury prediction
- Autonomous plan changes
- Auto-dialing emergency services

## Control measures (to implement)

| Hazard | Control | Status |
| --- | --- | --- |
| Guessing form from a bad camera | `cannot_assess` + reason code; no cue | not implemented |
| ML softening a safety rule | Rules are source of truth; ML cannot edit rules/red flags | not implemented |
| Missed red flag in pain text | Lexicon OR model; model cannot suppress lexicon | not implemented |
| Auto-progressing a patient | Recommendations `proposed` until physio approves | not implemented |
| Video leaving the device | Default: keypoints/metrics only; clips need consent | not implemented |
| Hardcoded clinical numbers | `PLACEHOLDER_NEEDS_PHYSIO_APPROVAL` plus evidence level (`default` / `dataset-derived` / `clinician`); no `approved` without a named human | schema only (Task 1a-4) |
| Provisional cue looking clinical | Banner **Prototype, not clinically approved** when a provisional rule fires | not implemented |
| Punitive engagement | Positive-only; red flag pauses rewards | not implemented |
| Real patient data in git | `.gitignore` + `data/README.md`; synthetic seeds only | scaffolded |

## Emergency copy (draft, not legal advice)

Show a prompt to call **123** (Egypt ambulance number as stated in the brief). Never auto-dial. Confirm with physio advisor and local guidance — **UNVERIFIED**.

## Law 151/2010 vs 151/2020

Egypt personal data protection: the brief cites Law 151/2020. Numbering and obligations are **UNVERIFIED**. Check the official gazette / a qualified advisor before any real-user deployment. Track under gate **G5** (ethics route).

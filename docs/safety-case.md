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

## Control measures and implementation status

| Hazard | Control | Status |
| --- | --- | --- |
| Prototype mistaken for clinician-approved care | First screen says the prototype is not clinically approved; demo decisions/results are explicitly described as simulated, not from a clinician | implemented on the first screen |
| Guessing form from a bad camera | `cannot_assess` + reason code; no cue | experimental rep counter refuses to advance unless mapped shoulder/wrist/hip visibility meets its disclosed test cutoff; this cutoff and mapping are unvalidated; no form cue is generated |
| ML softening a safety rule | Rules are source of truth; ML cannot edit rules/red flags | generic deterministic evaluator implemented; not connected to ML or UI |
| Missed red flag in pain text | Lexicon OR model; model cannot suppress lexicon | generic configurable lexicon/model OR helper implemented with no bundled terms; not connected to user input, model, or notification |
| Auto-progressing a patient | Recommendations `proposed` until physio approves | not implemented |
| Video leaving the device | Default: keypoints/metrics only; clips need consent | new browser pose demo uses a local object URL and does not upload video; the MediaPipe WASM/model assets are fetched from public CDNs; no session metrics are sent or saved |
| Hardcoded clinical numbers | `PLACEHOLDER_NEEDS_PHYSIO_APPROVAL` plus evidence level (`default` / `dataset-derived` / `clinician`); no `approved` without a named human | experimental counter values are explicitly identified in the UI as test-only, unvalidated assumptions and not treatment targets |
| Provisional cue looking clinical | Banner **Prototype, not clinically approved** when a provisional rule fires | evaluator returns a warning flag for provisional matches; no rule is configured or exposed in UI yet; first-screen disclaimer is an additional global notice |
| Punitive engagement | Positive-only; red flag pauses rewards | not implemented |
| Real patient data in git | `.gitignore` + `data/README.md`; synthetic seeds only | scaffolded |

## Emergency copy (draft, not legal advice)

Show a prompt to call **123** (Egypt ambulance number as stated in the brief). Never auto-dial. Confirm with physio advisor and local guidance — **UNVERIFIED**.

## Law 151/2010 vs 151/2020

Egypt personal data protection: the brief cites Law 151/2020. Numbering and obligations are **UNVERIFIED**. Check the official gazette / a qualified advisor before any real-user deployment. Track under gate **G5** (ethics route).

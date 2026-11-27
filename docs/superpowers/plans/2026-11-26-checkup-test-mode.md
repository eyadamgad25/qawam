# Check-up Test Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Camera-timed five-times sit-to-stand, 30-second sit-to-stand and Timed Up and Go in the PWA, with results in the physio report and FHIR export, and an evaluation harness that scores the same timing code on public data.

**Architecture:** One pure TypeScript module (`web/src/checkup/checkupTiming.ts`) turns body-point frames into a result or "no result". The screen collects frames in memory, speaks the count, then calls it. The evaluation script bundles the same module with rolldown and runs it from Python, as `ml/pain/pain_batch.ts` does.

**Tech Stack:** React + TypeScript + Vitest, MediaPipe Tasks; Python 3.14 + NumPy for evaluation.

**Spec:** `docs/superpowers/specs/2026-11-26-checkup-test-mode-design.md`

## Global Constraints
- No video or image stored or sent; face blurred in the camera view; results visible only to the assigned physio.
- A test without its validation passed is labelled "not validated" in the physio report.
- Thresholds are never set on the 60 Stanford evaluation videos or KINECAL's three test groups.
- Pass rules (spec): five-times ICC >= 0.90, MAE <= 0.5 s, count exact >= 95%, result on >= 80%; Timed Up and Go ICC >= 0.85, MAE <= 1.0 s.

## Review Focus
- Person leaves the frame mid-test: "no result" with a reason, never a time (test in Task 1).
- Fewer than five stand-ups before the person stops: "no result" (Task 1).
- 30-second test: a stand-up finishing after 30 s does not count (Task 1).
- Frames with no person at the start (person walks into view after "go"): start is still "go" (Task 1).
- FHIR bundle for a patient with no check-up results: empty bundle, not an error (Task 3).

---

### Task 1: Timing core
**Files:** Create `web/src/checkup/checkupTiming.ts`, `web/src/checkup/checkupTiming.test.ts`
**Interfaces:** `heightSignal(frames: PoseFrame[]) -> (number|null)[]` (hip height above ankle / leg length); `analyseCheckup(kind: 'sts5'|'sts30'|'tug', frames: PoseFrame[], start: 'go'|'first-movement') -> CheckupResult` where `CheckupResult = {ok: true, kind, seconds?, count?, startS, endS, standUps: number[], sitDowns: number[]} | {ok: false, kind, reason: 'person-missing'|'no-movement'|'too-few-stands'|'not-seated'}`.
- [ ] Tests on synthetic frames: five clean cycles time to the final sit within 0.1 s; 4 cycles → too-few-stands; 30 s cut; person missing 40% → person-missing; TUG stand-walk-return-sit.

### Task 2: Check-up screen
**Files:** Create `web/src/checkup/CheckupTest.tsx` (+ test), modify `web/src/App.tsx` (new tab), `web/src/i18n.ts` as needed
**Interfaces:** reuses `loadLandmarker`, `detectCurrentFrame`, `drawPoseOverlay`, `speakAr`, `spokenNumber`; adds `blurFace(ctx, landmarks)`.
- [ ] Test: choosing a test shows its Arabic instructions; the result panel shows "no result" text for a failed analysis.

### Task 3: Results in the report and FHIR
**Files:** Modify `web/src/exercise/sessionStore.ts`, `ProgressReport.tsx`; create `web/src/checkup/fhir.ts` (+ test)
**Interfaces:** `saveCheckup(patientId, result)`, `loadCheckups(patientId)`; `checkupBundle(patientId, results) -> FHIR Bundle JSON`.
- [ ] Tests: saved results round-trip; bundle has one Observation per result with valueQuantity in s or count; empty list → empty Bundle.

### Task 4: Evaluation harness and labelling page
**Files:** Create `ml/eval/checkup_batch.ts`, `ml/eval/checkup_eval.py` (+ test), `tools/label-checkup.html`
**Interfaces:** `checkup_eval.py sample` (fixed-seed 60 Stanford ids, frozen); `checkup_eval.py stanford|kinecal` (ICC(2,1), MAE, Bland-Altman, count accuracy, result rate) → `docs/experiments.md` entry.
- [ ] Tests: ICC on known data; OpenPose BODY_25 → MediaPipe name mapping; KINECAL side-on projection.

### Task 5: Data (needs the owner's OK to download), labelling by two team members, one evaluation run, record, commit.

/**
 * Qawam's server-side data model (GP2). Plain types, no database code, so the
 * same shapes serve MongoDB documents, API payloads and tests.
 *
 * Two ideas carry the design (docs/architecture.md):
 * - An exercise PACK says what the software knows about an exercise (angles,
 *   view, cue wording); a PRESCRIPTION says what one physio asked one patient
 *   to do (side, sets, reps, tolerance, which reference). They are versioned
 *   separately.
 * - Every session records the pack version, coaching-engine version and
 *   reference it was measured against, so an old report stays interpretable
 *   after any of them changes.
 */

export const API_NAME = 'qawam-api';

export type Role = 'patient' | 'physio' | 'clinic_admin' | 'system_admin';

export const ROLES: readonly Role[] = [
  'patient',
  'physio',
  'clinic_admin',
  'system_admin',
];

export type Side = 'left' | 'right';

/** Who is making a request, as established by authentication. */
export interface Actor {
  userId: string;
  role: Role;
  /** clinic the user belongs to; null for system admins */
  clinicId: string | null;
  /** for role 'patient': the patient record this login owns */
  patientId?: string;
}

export interface Consent {
  /** session summaries may be uploaded to the clinic */
  syncSessions: boolean;
  /** the physio may send WhatsApp summaries */
  shareWhatsApp: boolean;
  /** ISO time of the latest change, for the audit trail */
  updatedAt: string;
}

export interface Patient {
  id: string;
  clinicId: string;
  displayName: string;
  /** physios allowed to see and treat this patient */
  assignedPhysioIds: string[];
  consent: Consent;
}

export type ReferenceStatus = 'active' | 'retired';

/** The physio-approved rep a patient's home reps are compared with. */
export interface Reference {
  id: string;
  clinicId: string;
  patientId: string;
  packId: string;
  packVersion: number;
  engineVersion: string;
  side: Side;
  /** resting angle and range of the approved rep, degrees */
  baseDeg: number;
  rangeDeg: number;
  /** primary-angle curve of the approved rep (no video, no landmarks) */
  curve: number[];
  recordedAt: string;
  approvedBy: string;
  status: ReferenceStatus;
  /** set when retired: the reference that replaced it */
  replacedBy?: string;
}

export type PrescriptionStatus = 'active' | 'paused' | 'ended';

export interface Prescription {
  id: string;
  clinicId: string;
  patientId: string;
  physioId: string;
  packId: string;
  packVersion: number;
  side: Side;
  sets: number;
  reps: number;
  toleranceDeg: number;
  referenceId: string;
  status: PrescriptionStatus;
  createdAt: string;
}

/** Why a rep was not judged (mirrors the web coach's reasons). */
export type AbstainReason = 'LOW_DETECTION' | 'JOINTS_HIDDEN' | 'VIEW_MISMATCH' | 'NOT_CERTIFIED';

export interface RepRecord {
  index: number;
  assessed: boolean;
  /** cue code when assessed, abstain reason when not */
  cue: string | null;
  rangeDeg: number | null;
  depthDiffDeg: number | null;
  pathDiffDeg: number | null;
  posture: string | null;
}

/** What the phone uploads after a session. No video, no landmarks. */
export interface SessionUpload {
  /** UUID made on the phone; the idempotency key for retries */
  id: string;
  patientId: string;
  prescriptionId: string;
  referenceId: string;
  packId: string;
  packVersion: number;
  engineVersion: string;
  startedAt: string;
  mode: 'live' | 'file';
  reps: RepRecord[];
}

export type ReviewFlag =
  /** the prescription's pack version changed after this session was planned */
  | 'PACK_VERSION_DIFFERS'
  /** measured against a reference that has since been replaced */
  | 'REFERENCE_RETIRED'
  /** no rep could be judged (camera set-up problem worth a look) */
  | 'NOTHING_ASSESSED';

export interface SessionRecord extends SessionUpload {
  clinicId: string;
  receivedAt: string;
  /** canonical hash of the upload, to tell a retry from a conflicting reuse of an id */
  contentHash: string;
  reviewFlags: ReviewFlag[];
}

export interface AuditEvent {
  at: string;
  actorId: string;
  clinicId: string | null;
  action: string;
  resourceType: 'patient' | 'prescription' | 'reference' | 'session' | 'consent';
  resourceId: string;
  detail?: string;
}

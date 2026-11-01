/**
 * Who may do what. Every rule is scoped to a clinic first, then to the
 * patient's assigned physios, so no query can reach across clinics.
 *
 * - patient: only their own record and sessions.
 * - physio: patients of their clinic who are assigned to them.
 * - clinic_admin: sees their clinic's patients for administration, but does
 *   not prescribe or approve references (that is a clinical act).
 * - system_admin: operates the platform; no access to clinical data.
 */
import type { Actor, Patient } from './model.js';

function sameClinic(actor: Actor, patient: Patient): boolean {
  return actor.clinicId !== null && actor.clinicId === patient.clinicId;
}

function treats(actor: Actor, patient: Patient): boolean {
  return (
    actor.role === 'physio' &&
    sameClinic(actor, patient) &&
    patient.assignedPhysioIds.includes(actor.userId)
  );
}

function isSelf(actor: Actor, patient: Patient): boolean {
  return (
    actor.role === 'patient' &&
    actor.patientId === patient.id &&
    sameClinic(actor, patient)
  );
}

/** Read the patient's plan, references and session history. */
export function canReadPatient(actor: Actor, patient: Patient): boolean {
  return (
    isSelf(actor, patient) ||
    treats(actor, patient) ||
    (actor.role === 'clinic_admin' && sameClinic(actor, patient))
  );
}

/** Prescribe, change a plan, approve or retire a reference. */
export function canTreat(actor: Actor, patient: Patient): boolean {
  return treats(actor, patient);
}

/** Upload a session summary: only the patient's own login. */
export function canSubmitSession(actor: Actor, patient: Patient): boolean {
  return isSelf(actor, patient);
}

/** Change consent: only the patient themselves. */
export function canChangeConsent(actor: Actor, patient: Patient): boolean {
  return isSelf(actor, patient);
}

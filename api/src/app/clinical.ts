/**
 * Clinical use cases: approving a reference, prescribing, consent, and
 * reading a patient's history. Every one checks access through domain/access,
 * reads with the actor's clinic id, and writes an audit event.
 */
import { canChangeConsent, canReadPatient, canTreat } from '../domain/access.js';
import type {
  Actor,
  Consent,
  Patient,
  Prescription,
  Reference,
  SessionRecord,
  Side,
} from '../domain/model.js';
import type { Deps } from '../store/ports.js';
import { Denied } from './errors.js';

async function loadPatient(
  deps: Deps,
  actor: Actor,
  patientId: string,
): Promise<Patient> {
  // Outside the actor's clinic a patient is reported as not found, not forbidden,
  // so the API does not confirm that an id exists in another clinic.
  const patient = actor.clinicId
    ? await deps.store.getPatient(actor.clinicId, patientId)
    : null;
  if (!patient) {
    throw new Denied('NOT_FOUND', 'patient not found');
  }
  return patient;
}

export interface ReferenceInput {
  patientId: string;
  packId: string;
  packVersion: number;
  engineVersion: string;
  side: Side;
  baseDeg: number;
  rangeDeg: number;
  curve: number[];
  recordedAt: string;
}

/**
 * The physio approves a reference rep recorded in the clinic. An active
 * reference for the same exercise and side is retired, never overwritten, so
 * sessions measured against it stay interpretable.
 */
export async function approveReference(
  deps: Deps,
  actor: Actor,
  input: ReferenceInput,
): Promise<Reference> {
  const patient = await loadPatient(deps, actor, input.patientId);
  if (!canTreat(actor, patient)) {
    throw new Denied('FORBIDDEN', 'only an assigned physio can approve a reference');
  }
  if (
    input.curve.length < 2 ||
    !(input.rangeDeg >= 10) ||
    !input.curve.every(Number.isFinite)
  ) {
    throw new Denied('INVALID', 'reference rep has no usable movement');
  }
  const reference: Reference = {
    id: deps.newId(),
    clinicId: patient.clinicId,
    patientId: patient.id,
    packId: input.packId,
    packVersion: input.packVersion,
    engineVersion: input.engineVersion,
    side: input.side,
    baseDeg: input.baseDeg,
    rangeDeg: input.rangeDeg,
    curve: [...input.curve],
    recordedAt: input.recordedAt,
    approvedBy: actor.userId,
    status: 'active',
  };
  const now = deps.clock.now();
  for (const old of await deps.store.activeReferences(
    patient.clinicId,
    patient.id,
    input.packId,
  )) {
    if (old.side !== input.side) {
      continue;
    }
    await deps.store.saveReference({
      ...old,
      status: 'retired',
      replacedBy: reference.id,
    });
    await deps.store.appendAudit({
      at: now,
      actorId: actor.userId,
      clinicId: patient.clinicId,
      action: 'reference.retire',
      resourceType: 'reference',
      resourceId: old.id,
      detail: `replaced by ${reference.id}`,
    });
  }
  await deps.store.saveReference(reference);
  await deps.store.appendAudit({
    at: now,
    actorId: actor.userId,
    clinicId: patient.clinicId,
    action: 'reference.approve',
    resourceType: 'reference',
    resourceId: reference.id,
  });
  return reference;
}

export interface PrescriptionInput {
  patientId: string;
  packId: string;
  packVersion: number;
  side: Side;
  sets: number;
  reps: number;
  toleranceDeg: number;
  referenceId: string;
}

export async function prescribe(
  deps: Deps,
  actor: Actor,
  input: PrescriptionInput,
): Promise<Prescription> {
  const patient = await loadPatient(deps, actor, input.patientId);
  if (!canTreat(actor, patient)) {
    throw new Denied('FORBIDDEN', 'only an assigned physio can prescribe');
  }
  const reference = await deps.store.getReference(patient.clinicId, input.referenceId);
  if (
    !reference ||
    reference.patientId !== patient.id ||
    reference.status !== 'active' ||
    reference.packId !== input.packId ||
    reference.side !== input.side
  ) {
    throw new Denied(
      'INVALID',
      'needs an active reference of this patient, exercise and side',
    );
  }
  const counts = [input.sets, input.reps];
  if (!counts.every((n) => Number.isInteger(n) && n >= 1 && n <= 50)) {
    throw new Denied('INVALID', 'sets and reps must be whole numbers from 1 to 50');
  }
  if (!(input.toleranceDeg > 0 && input.toleranceDeg <= 45)) {
    throw new Denied('INVALID', 'tolerance must be above 0 and at most 45 degrees');
  }
  const prescription: Prescription = {
    id: deps.newId(),
    clinicId: patient.clinicId,
    patientId: patient.id,
    physioId: actor.userId,
    packId: input.packId,
    packVersion: input.packVersion,
    side: input.side,
    sets: input.sets,
    reps: input.reps,
    toleranceDeg: input.toleranceDeg,
    referenceId: reference.id,
    status: 'active',
    createdAt: deps.clock.now(),
  };
  await deps.store.savePrescription(prescription);
  await deps.store.appendAudit({
    at: prescription.createdAt,
    actorId: actor.userId,
    clinicId: patient.clinicId,
    action: 'prescription.create',
    resourceType: 'prescription',
    resourceId: prescription.id,
  });
  return prescription;
}

/** Only the patient changes their own consent; withdrawing stops future uploads. */
export async function setConsent(
  deps: Deps,
  actor: Actor,
  patientId: string,
  consent: Omit<Consent, 'updatedAt'>,
): Promise<Patient> {
  const patient = await loadPatient(deps, actor, patientId);
  if (!canChangeConsent(actor, patient)) {
    throw new Denied('FORBIDDEN', 'only the patient can change their consent');
  }
  const updated: Patient = {
    ...patient,
    consent: { ...consent, updatedAt: deps.clock.now() },
  };
  await deps.store.savePatient(updated);
  await deps.store.appendAudit({
    at: updated.consent.updatedAt,
    actorId: actor.userId,
    clinicId: patient.clinicId,
    action: 'consent.update',
    resourceType: 'consent',
    resourceId: patient.id,
    detail: `syncSessions=${consent.syncSessions},shareWhatsApp=${consent.shareWhatsApp}`,
  });
  return updated;
}

/** A patient's sessions, for the physio portal or the patient's own history. Reads are audited. */
export async function patientSessions(
  deps: Deps,
  actor: Actor,
  patientId: string,
): Promise<SessionRecord[]> {
  const patient = await loadPatient(deps, actor, patientId);
  if (!canReadPatient(actor, patient)) {
    throw new Denied('FORBIDDEN', 'not allowed to read this patient');
  }
  await deps.store.appendAudit({
    at: deps.clock.now(),
    actorId: actor.userId,
    clinicId: patient.clinicId,
    action: 'session.read',
    resourceType: 'patient',
    resourceId: patient.id,
  });
  return deps.store.sessionsFor(patient.clinicId, patient.id);
}

/** Sessions with review flags, oldest first: the physio's review-by-exception queue. */
export async function reviewQueue(
  deps: Deps,
  actor: Actor,
  patientId: string,
): Promise<SessionRecord[]> {
  return (await patientSessions(deps, actor, patientId)).filter(
    (s) => s.reviewFlags.length > 0,
  );
}

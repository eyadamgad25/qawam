/**
 * Storage ports. The use cases depend on these interfaces only; GP2 adds a
 * MongoDB adapter, the tests use the in-memory one. Every lookup that returns
 * clinical data takes the clinic id, so a missing scope is a type error, not
 * a silent leak.
 */
import type {
  AuditEvent,
  Patient,
  Prescription,
  Reference,
  SessionRecord,
} from '../domain/model.js';

export interface Store {
  getPatient(clinicId: string, patientId: string): Promise<Patient | null>;
  savePatient(patient: Patient): Promise<void>;
  getPrescription(
    clinicId: string,
    prescriptionId: string,
  ): Promise<Prescription | null>;
  savePrescription(prescription: Prescription): Promise<void>;
  getReference(clinicId: string, referenceId: string): Promise<Reference | null>;
  saveReference(reference: Reference): Promise<void>;
  activeReferences(
    clinicId: string,
    patientId: string,
    packId: string,
  ): Promise<Reference[]>;
  getSession(clinicId: string, sessionId: string): Promise<SessionRecord | null>;
  /** inserts only; returns false when the id already exists (unique index in MongoDB) */
  insertSession(session: SessionRecord): Promise<boolean>;
  sessionsFor(clinicId: string, patientId: string): Promise<SessionRecord[]>;
  /** append-only: there is deliberately no update or delete */
  appendAudit(event: AuditEvent): Promise<void>;
  auditFor(clinicId: string | null): Promise<AuditEvent[]>;
}

export interface Clock {
  now(): string;
}

export interface Deps {
  store: Store;
  clock: Clock;
  newId(): string;
}

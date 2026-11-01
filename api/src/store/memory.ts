/**
 * In-memory Store for tests and demos. Returns copies so a caller cannot
 * change stored data by mutating what it read, which is how the MongoDB
 * adapter will behave too.
 */
import type {
  AuditEvent,
  Patient,
  Prescription,
  Reference,
  SessionRecord,
} from '../domain/model.js';
import type { Store } from './ports.js';

const copy = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T;

function scoped<T extends { clinicId: string }>(
  item: T | undefined,
  clinicId: string,
): T | null {
  return item && item.clinicId === clinicId ? copy(item) : null;
}

export class MemoryStore implements Store {
  private readonly patients = new Map<string, Patient>();
  private readonly prescriptions = new Map<string, Prescription>();
  private readonly references = new Map<string, Reference>();
  private readonly sessions = new Map<string, SessionRecord>();
  private readonly audit: AuditEvent[] = [];

  async getPatient(clinicId: string, patientId: string) {
    return scoped(this.patients.get(patientId), clinicId);
  }

  async savePatient(patient: Patient) {
    this.patients.set(patient.id, copy(patient));
  }

  async getPrescription(clinicId: string, prescriptionId: string) {
    return scoped(this.prescriptions.get(prescriptionId), clinicId);
  }

  async savePrescription(prescription: Prescription) {
    this.prescriptions.set(prescription.id, copy(prescription));
  }

  async getReference(clinicId: string, referenceId: string) {
    return scoped(this.references.get(referenceId), clinicId);
  }

  async saveReference(reference: Reference) {
    this.references.set(reference.id, copy(reference));
  }

  async activeReferences(clinicId: string, patientId: string, packId: string) {
    return [...this.references.values()]
      .filter(
        (r) =>
          r.clinicId === clinicId &&
          r.patientId === patientId &&
          r.packId === packId &&
          r.status === 'active',
      )
      .map(copy);
  }

  async getSession(clinicId: string, sessionId: string) {
    return scoped(this.sessions.get(sessionId), clinicId);
  }

  async insertSession(session: SessionRecord) {
    if (this.sessions.has(session.id)) {
      return false;
    }
    this.sessions.set(session.id, copy(session));
    return true;
  }

  async sessionsFor(clinicId: string, patientId: string) {
    return [...this.sessions.values()]
      .filter((s) => s.clinicId === clinicId && s.patientId === patientId)
      .sort((a, b) => a.startedAt.localeCompare(b.startedAt))
      .map(copy);
  }

  async appendAudit(event: AuditEvent) {
    this.audit.push(copy(event));
  }

  async auditFor(clinicId: string | null) {
    return this.audit.filter((e) => e.clinicId === clinicId).map(copy);
  }
}

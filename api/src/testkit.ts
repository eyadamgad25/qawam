/** Shared fixtures for the API tests: two clinics, physios, patients. */
import type { Actor, Patient, SessionUpload } from './domain/model.js';
import { MemoryStore } from './store/memory.js';
import type { Deps } from './store/ports.js';

export function testDeps(): Deps & { store: MemoryStore } {
  let tick = 0;
  let next = 0;
  return {
    store: new MemoryStore(),
    clock: { now: () => new Date(Date.UTC(2027, 1, 1, 9, 0, tick++)).toISOString() },
    newId: () => `id${++next}`,
  };
}

export const physioA: Actor = {
  userId: 'physio-a',
  role: 'physio',
  clinicId: 'clinic-a',
};
export const physioA2: Actor = {
  userId: 'physio-a2',
  role: 'physio',
  clinicId: 'clinic-a',
};
export const physioB: Actor = {
  userId: 'physio-b',
  role: 'physio',
  clinicId: 'clinic-b',
};
export const adminA: Actor = {
  userId: 'admin-a',
  role: 'clinic_admin',
  clinicId: 'clinic-a',
};
export const sysadmin: Actor = { userId: 'root', role: 'system_admin', clinicId: null };
export const omar: Actor = {
  userId: 'u-omar',
  role: 'patient',
  clinicId: 'clinic-a',
  patientId: 'p-omar',
};
export const mona: Actor = {
  userId: 'u-mona',
  role: 'patient',
  clinicId: 'clinic-a',
  patientId: 'p-mona',
};

export function patient(
  id: string,
  clinicId = 'clinic-a',
  physios = ['physio-a'],
  sync = true,
): Patient {
  return {
    id,
    clinicId,
    displayName: id,
    assignedPhysioIds: physios,
    consent: {
      syncSessions: sync,
      shareWhatsApp: true,
      updatedAt: '2027-01-01T00:00:00.000Z',
    },
  };
}

export function upload(overrides: Partial<SessionUpload> = {}): SessionUpload {
  return {
    id: '3f2b8c1e-4d5a-4b6c-8d7e-9f0a1b2c3d4e',
    patientId: 'p-omar',
    prescriptionId: 'id2',
    referenceId: 'id1',
    packId: 'lower-limb.squat',
    packVersion: 1,
    engineVersion: 'coach-2026-11-02',
    startedAt: '2027-02-01T08:00:00.000Z',
    mode: 'live',
    reps: [
      {
        index: 0,
        assessed: true,
        cue: 'MATCHES_REFERENCE',
        rangeDeg: 64,
        depthDiffDeg: -2,
        pathDiffDeg: 4,
        posture: null,
      },
      {
        index: 1,
        assessed: false,
        cue: 'JOINTS_HIDDEN',
        rangeDeg: null,
        depthDiffDeg: null,
        pathDiffDeg: null,
        posture: null,
      },
    ],
    ...overrides,
  };
}

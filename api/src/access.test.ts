import { describe, expect, it } from 'vitest';
import {
  canChangeConsent,
  canReadPatient,
  canSubmitSession,
  canTreat,
} from './domain/access.js';
import { ROLES } from './domain/model.js';
import {
  adminA,
  mona,
  omar,
  patient,
  physioA,
  physioA2,
  physioB,
  sysadmin,
} from './testkit.js';

describe('access policy (tenant isolation)', () => {
  const p = patient('p-omar');

  it('lists the four product roles', () => {
    expect(ROLES).toEqual(['patient', 'physio', 'clinic_admin', 'system_admin']);
  });

  it('lets only the assigned physio of the same clinic treat', () => {
    expect(canTreat(physioA, p)).toBe(true);
    expect(canTreat(physioA2, p)).toBe(false); // same clinic, not assigned
    expect(canTreat(physioB, p)).toBe(false); // other clinic
    expect(canTreat(adminA, p)).toBe(false); // admin is not clinical
    expect(canTreat(omar, p)).toBe(false);
  });

  it('never crosses clinics, even with a matching physio id', () => {
    const impostor = { ...physioB, userId: 'physio-a' };
    expect(canReadPatient(impostor, p)).toBe(false);
    expect(canTreat(impostor, p)).toBe(false);
  });

  it('lets patients read and upload only their own record', () => {
    expect(canReadPatient(omar, p)).toBe(true);
    expect(canSubmitSession(omar, p)).toBe(true);
    expect(canReadPatient(mona, p)).toBe(false);
    expect(canSubmitSession(mona, p)).toBe(false);
    expect(canSubmitSession(physioA, p)).toBe(false);
  });

  it('gives the clinic admin read access but the platform admin none', () => {
    expect(canReadPatient(adminA, p)).toBe(true);
    expect(canReadPatient(sysadmin, p)).toBe(false);
    expect(canTreat(sysadmin, p)).toBe(false);
  });

  it('leaves consent to the patient alone', () => {
    expect(canChangeConsent(omar, p)).toBe(true);
    expect(canChangeConsent(physioA, p)).toBe(false);
    expect(canChangeConsent(adminA, p)).toBe(false);
  });
});

/** Scaffold marker. Express app lands in Task 5. */
export const API_NAME = 'qawam-api';

export type Role = 'patient' | 'physio' | 'clinic_admin' | 'system_admin';

export function roles(): readonly Role[] {
  return ['patient', 'physio', 'clinic_admin', 'system_admin'];
}

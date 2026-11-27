/**
 * Check-up results on this device (localStorage, same pattern as exercise sessions). Only the numbers are kept:
 * no video, image or body points. A server with consent and the physio access rules comes in semester 2.
 */
import type { CheckupKind } from './checkupTiming';

export const CHECKUP_ENGINE_VERSION = 'checkup-2026-11-26';

export interface StoredCheckup {
  id: string;
  patient: string;
  kind: CheckupKind;
  dateIso: string;
  /** sts5 and tug */
  seconds?: number;
  /** sts30 */
  count?: number;
  engine: string;
}

const KEY = 'qawam.checkups.v1';
let memory: StoredCheckup[] = [];

function storage(): Storage | null {
  try {
    return globalThis.localStorage ?? null;
  } catch {
    return null;
  }
}

export function loadCheckups(): StoredCheckup[] {
  try {
    const raw = storage()?.getItem(KEY);
    if (raw) {
      const parsed: unknown = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        return parsed as StoredCheckup[];
      }
    }
  } catch {
    // fall back to memory
  }
  return [...memory];
}

function write(items: StoredCheckup[]): void {
  memory = [...items];
  try {
    storage()?.setItem(KEY, JSON.stringify(items));
  } catch {
    // memory copy still works for this page
  }
}

export function saveCheckup(item: StoredCheckup): void {
  write([...loadCheckups().filter((c) => c.id !== item.id), item]);
}

export function checkupsFor(patient: string): StoredCheckup[] {
  return loadCheckups()
    .filter((c) => c.patient === patient)
    .sort((a, b) => a.dateIso.localeCompare(b.dateIso));
}

export function deleteCheckups(patient: string): void {
  write(loadCheckups().filter((c) => c.patient !== patient));
}

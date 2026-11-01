/**
 * Validation of what the phone uploads. Hand-written so the API has no
 * runtime dependency for it; the same checks become MongoDB JSON-schema
 * validators in GP2. Anything not listed is rejected, so a client cannot
 * smuggle extra fields (for example landmarks) into the database.
 */
import type { RepRecord, SessionUpload } from './model.js';

export type Validation<T> = { ok: true; value: T } | { ok: false; errors: string[] };

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const ID = /^[A-Za-z0-9_-]{1,64}$/;
const PACK_ID = /^[a-z0-9-]+\.[a-z0-9-]+$/;
const MAX_REPS = 200;

const SESSION_KEYS = [
  'id',
  'patientId',
  'prescriptionId',
  'referenceId',
  'packId',
  'packVersion',
  'engineVersion',
  'startedAt',
  'mode',
  'reps',
] as const;
const REP_KEYS = [
  'index',
  'assessed',
  'cue',
  'rangeDeg',
  'depthDiffDeg',
  'pathDiffDeg',
  'posture',
] as const;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function extraKeys(
  value: Record<string, unknown>,
  allowed: readonly string[],
): string[] {
  return Object.keys(value).filter((key) => !allowed.includes(key));
}

function finiteOrNull(value: unknown): boolean {
  return value === null || (typeof value === 'number' && Number.isFinite(value));
}

function shortTextOrNull(value: unknown): boolean {
  return value === null || (typeof value === 'string' && value.length <= 64);
}

function isoTime(value: unknown): boolean {
  return (
    typeof value === 'string' && !Number.isNaN(Date.parse(value)) && value.includes('T')
  );
}

function validateRep(rep: unknown, at: string, errors: string[]): rep is RepRecord {
  if (!isRecord(rep)) {
    errors.push(`${at}: not an object`);
    return false;
  }
  const before = errors.length;
  for (const key of extraKeys(rep, REP_KEYS)) {
    errors.push(`${at}.${key}: unknown field`);
  }
  if (!Number.isInteger(rep.index) || (rep.index as number) < 0) {
    errors.push(`${at}.index: must be a non-negative integer`);
  }
  if (typeof rep.assessed !== 'boolean') {
    errors.push(`${at}.assessed: must be true or false`);
  }
  if (!shortTextOrNull(rep.cue)) {
    errors.push(`${at}.cue: must be a short string or null`);
  }
  if (!shortTextOrNull(rep.posture)) {
    errors.push(`${at}.posture: must be a short string or null`);
  }
  for (const key of ['rangeDeg', 'depthDiffDeg', 'pathDiffDeg'] as const) {
    if (!finiteOrNull(rep[key])) {
      errors.push(`${at}.${key}: must be a number or null`);
    }
  }
  return errors.length === before;
}

export function validateSessionUpload(input: unknown): Validation<SessionUpload> {
  const errors: string[] = [];
  if (!isRecord(input)) {
    return { ok: false, errors: ['session: not an object'] };
  }
  for (const key of extraKeys(input, SESSION_KEYS)) {
    errors.push(`session.${key}: unknown field`);
  }
  if (typeof input.id !== 'string' || !UUID.test(input.id)) {
    errors.push('session.id: must be a UUID made on the device');
  }
  for (const key of ['patientId', 'prescriptionId', 'referenceId'] as const) {
    if (typeof input[key] !== 'string' || !ID.test(input[key] as string)) {
      errors.push(`session.${key}: must be an id`);
    }
  }
  if (typeof input.packId !== 'string' || !PACK_ID.test(input.packId)) {
    errors.push('session.packId: must look like "lower-limb.squat"');
  }
  if (!Number.isInteger(input.packVersion) || (input.packVersion as number) < 1) {
    errors.push('session.packVersion: must be a positive integer');
  }
  if (
    typeof input.engineVersion !== 'string' ||
    input.engineVersion.length === 0 ||
    input.engineVersion.length > 64
  ) {
    errors.push('session.engineVersion: must be a short string');
  }
  if (!isoTime(input.startedAt)) {
    errors.push('session.startedAt: must be an ISO date-time');
  }
  if (input.mode !== 'live' && input.mode !== 'file') {
    errors.push('session.mode: must be "live" or "file"');
  }
  if (!Array.isArray(input.reps)) {
    errors.push('session.reps: must be a list');
  } else if (input.reps.length > MAX_REPS) {
    errors.push(`session.reps: at most ${MAX_REPS} reps`);
  } else {
    input.reps.forEach((rep, i) => validateRep(rep, `session.reps[${i}]`, errors));
  }
  return errors.length === 0
    ? { ok: true, value: input as unknown as SessionUpload }
    : { ok: false, errors };
}

/** JSON with sorted keys, so equal content always gives the same text. */
export function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) {
    return `[${value.map(canonicalJson).join(',')}]`;
  }
  if (isRecord(value)) {
    return `{${Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`)
      .join(',')}}`;
  }
  return JSON.stringify(value ?? null);
}

/** FNV-1a 64-bit over the canonical JSON; enough to tell a retry from a different payload. */
export function contentHash(value: unknown): string {
  let hash = 0xcbf29ce484222325n;
  const prime = 0x100000001b3n;
  const text = canonicalJson(value);
  for (let i = 0; i < text.length; i += 1) {
    hash ^= BigInt(text.charCodeAt(i));
    hash = (hash * prime) & 0xffffffffffffffffn;
  }
  return hash.toString(16).padStart(16, '0');
}

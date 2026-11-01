/**
 * Offline-first session upload.
 *
 * The phone saves every session locally first and keeps unsent ones in an
 * outbox. When it is online it sends the outbox as a batch and may resend the
 * same batch after a dropped connection. The id the phone generated is the
 * idempotency key, so a resend never creates a second session:
 *
 * - accepted:  new id, stored.
 * - duplicate: id already stored with identical content; nothing changes and
 *              the phone may drop it from the outbox.
 * - rejected:  invalid, not allowed, no consent, or the id was reused with
 *              different content (a bug or tampering; never overwritten).
 *
 * Each item is judged on its own, so one bad session does not block the rest.
 * Sessions are never edited after acceptance; a physio's review adds flags,
 * it does not change measurements.
 */
import { canSubmitSession } from '../domain/access.js';
import type {
  Actor,
  ReviewFlag,
  SessionRecord,
  SessionUpload,
} from '../domain/model.js';
import { contentHash, validateSessionUpload } from '../domain/validate.js';
import type { Deps } from '../store/ports.js';

export type RejectReason =
  | 'INVALID'
  | 'NOT_FOUND'
  | 'FORBIDDEN'
  | 'NO_CONSENT'
  | 'PRESCRIPTION_MISMATCH'
  | 'REFERENCE_MISMATCH'
  | 'ID_CONFLICT';

export type SyncResult =
  | { id: string; status: 'accepted'; reviewFlags: ReviewFlag[] }
  | { id: string; status: 'duplicate' }
  | { id: string; status: 'rejected'; reason: RejectReason; detail?: string };

export const MAX_BATCH = 50;

function idOf(input: unknown): string {
  return typeof input === 'object' &&
    input !== null &&
    typeof (input as { id?: unknown }).id === 'string'
    ? (input as { id: string }).id
    : '';
}

async function ingestOne(
  deps: Deps,
  actor: Actor,
  input: unknown,
): Promise<SyncResult> {
  const id = idOf(input);
  const checked = validateSessionUpload(input);
  if (!checked.ok) {
    return {
      id,
      status: 'rejected',
      reason: 'INVALID',
      detail: checked.errors.join('; '),
    };
  }
  const upload: SessionUpload = checked.value;
  const clinicId = actor.clinicId;
  if (clinicId === null) {
    return { id, status: 'rejected', reason: 'FORBIDDEN' };
  }
  const patient = await deps.store.getPatient(clinicId, upload.patientId);
  if (!patient) {
    return { id, status: 'rejected', reason: 'NOT_FOUND', detail: 'patient' };
  }
  if (!canSubmitSession(actor, patient)) {
    return { id, status: 'rejected', reason: 'FORBIDDEN' };
  }
  if (!patient.consent.syncSessions) {
    return { id, status: 'rejected', reason: 'NO_CONSENT' };
  }

  const hash = contentHash(upload);
  const existing = await deps.store.getSession(clinicId, upload.id);
  if (existing) {
    return existing.contentHash === hash
      ? { id, status: 'duplicate' }
      : { id, status: 'rejected', reason: 'ID_CONFLICT' };
  }

  const prescription = await deps.store.getPrescription(
    clinicId,
    upload.prescriptionId,
  );
  if (
    !prescription ||
    prescription.patientId !== patient.id ||
    prescription.packId !== upload.packId
  ) {
    return { id, status: 'rejected', reason: 'PRESCRIPTION_MISMATCH' };
  }
  const reference = await deps.store.getReference(clinicId, upload.referenceId);
  if (
    !reference ||
    reference.patientId !== patient.id ||
    reference.packId !== upload.packId
  ) {
    return { id, status: 'rejected', reason: 'REFERENCE_MISMATCH' };
  }

  // Accepted sessions keep their own versions; differences go to the physio's review queue.
  const reviewFlags: ReviewFlag[] = [];
  if (upload.packVersion !== prescription.packVersion) {
    reviewFlags.push('PACK_VERSION_DIFFERS');
  }
  if (reference.status === 'retired') {
    reviewFlags.push('REFERENCE_RETIRED');
  }
  if (upload.reps.length > 0 && upload.reps.every((rep) => !rep.assessed)) {
    reviewFlags.push('NOTHING_ASSESSED');
  }

  const record: SessionRecord = {
    ...upload,
    clinicId,
    receivedAt: deps.clock.now(),
    contentHash: hash,
    reviewFlags,
  };
  if (!(await deps.store.insertSession(record))) {
    // lost a race with a concurrent resend of the same id
    const stored = await deps.store.getSession(clinicId, upload.id);
    return stored?.contentHash === hash
      ? { id, status: 'duplicate' }
      : { id, status: 'rejected', reason: 'ID_CONFLICT' };
  }
  await deps.store.appendAudit({
    at: record.receivedAt,
    actorId: actor.userId,
    clinicId,
    action: 'session.upload',
    resourceType: 'session',
    resourceId: record.id,
    ...(reviewFlags.length ? { detail: reviewFlags.join(',') } : {}),
  });
  return { id, status: 'accepted', reviewFlags };
}

/** Upload a batch from the phone's outbox; one result per item, in order. */
export async function ingestSessions(
  deps: Deps,
  actor: Actor,
  batch: readonly unknown[],
): Promise<SyncResult[]> {
  if (batch.length > MAX_BATCH) {
    return batch.map((item) => ({
      id: idOf(item),
      status: 'rejected' as const,
      reason: 'INVALID' as const,
      detail: `batch larger than ${MAX_BATCH}`,
    }));
  }
  const results: SyncResult[] = [];
  for (const item of batch) {
    results.push(await ingestOne(deps, actor, item));
  }
  return results;
}

import { beforeEach, describe, expect, it } from 'vitest';
import {
  approveReference,
  patientSessions,
  prescribe,
  reviewQueue,
  setConsent,
} from './app/clinical.js';
import { Denied } from './app/errors.js';
import { ingestSessions, MAX_BATCH } from './app/sync.js';
import { contentHash, validateSessionUpload } from './domain/validate.js';
import {
  adminA,
  mona,
  omar,
  patient,
  physioA,
  physioA2,
  physioB,
  sysadmin,
  testDeps,
  upload,
} from './testkit.js';

async function clinicWithPlan() {
  const deps = testDeps();
  await deps.store.savePatient(patient('p-omar'));
  await deps.store.savePatient(patient('p-mona'));
  await deps.store.savePatient(patient('p-zed', 'clinic-b', ['physio-b']));
  const reference = await approveReference(deps, physioA, {
    patientId: 'p-omar',
    packId: 'lower-limb.squat',
    packVersion: 1,
    engineVersion: 'coach-2026-11-02',
    side: 'left',
    baseDeg: 4,
    rangeDeg: 66,
    curve: [4, 30, 70, 30, 4],
    recordedAt: '2027-01-30T10:00:00.000Z',
  });
  const plan = await prescribe(deps, physioA, {
    patientId: 'p-omar',
    packId: 'lower-limb.squat',
    packVersion: 1,
    side: 'left',
    sets: 2,
    reps: 8,
    toleranceDeg: 10,
    referenceId: reference.id,
  });
  return { deps, reference, plan };
}

describe('validation of what the phone uploads', () => {
  it('accepts a well-formed session', () => {
    expect(validateSessionUpload(upload()).ok).toBe(true);
  });

  it('refuses extra fields such as landmarks, and bad values', () => {
    const result = validateSessionUpload({
      ...upload({ id: 'not-a-uuid', mode: 'x' as never }),
      landmarks: [[0, 0]],
    });
    expect(result.ok).toBe(false);
    const errors = result.ok ? [] : result.errors.join('\n');
    expect(errors).toContain('session.landmarks: unknown field');
    expect(errors).toContain('session.id');
    expect(errors).toContain('session.mode');
  });

  it('checks every rep', () => {
    const bad = upload();
    (bad.reps[0] as unknown as Record<string, unknown>).rangeDeg = 'deep';
    const result = validateSessionUpload(bad);
    expect(result.ok ? '' : result.errors.join()).toContain('session.reps[0].rangeDeg');
  });

  it('hashes equal content equally whatever the key order', () => {
    const a = upload();
    const b = Object.fromEntries(Object.entries(a).reverse());
    expect(contentHash(a)).toBe(contentHash(b));
    expect(contentHash(a)).not.toBe(contentHash(upload({ mode: 'file' })));
  });
});

describe('offline-first session sync', () => {
  let ctx: Awaited<ReturnType<typeof clinicWithPlan>>;
  beforeEach(async () => {
    ctx = await clinicWithPlan();
  });
  const mine = () =>
    upload({ prescriptionId: ctx.plan.id, referenceId: ctx.reference.id });

  it('accepts a session once and treats a resend as a duplicate', async () => {
    const first = await ingestSessions(ctx.deps, omar, [mine()]);
    expect(first).toEqual([{ id: mine().id, status: 'accepted', reviewFlags: [] }]);
    const again = await ingestSessions(ctx.deps, omar, [mine()]);
    expect(again).toEqual([{ id: mine().id, status: 'duplicate' }]);
    expect(await ctx.deps.store.sessionsFor('clinic-a', 'p-omar')).toHaveLength(1);
  });

  it('never overwrites when an id is reused with different content', async () => {
    await ingestSessions(ctx.deps, omar, [mine()]);
    const [result] = await ingestSessions(ctx.deps, omar, [
      { ...mine(), mode: 'file' },
    ]);
    expect(result).toMatchObject({ status: 'rejected', reason: 'ID_CONFLICT' });
    const [stored] = await ctx.deps.store.sessionsFor('clinic-a', 'p-omar');
    expect(stored?.mode).toBe('live');
  });

  it('judges each item on its own', async () => {
    const results = await ingestSessions(ctx.deps, omar, [
      { garbage: true },
      mine(),
      { ...mine(), id: '11111111-2222-4333-8444-555555555555', prescriptionId: 'nope' },
    ]);
    expect(results.map((r) => r.status)).toEqual(['rejected', 'accepted', 'rejected']);
    expect(results[2]).toMatchObject({ reason: 'PRESCRIPTION_MISMATCH' });
  });

  it('only takes uploads from the patient themselves', async () => {
    for (const actor of [mona, physioA, adminA]) {
      const [result] = await ingestSessions(ctx.deps, actor, [mine()]);
      expect(result).toMatchObject({ status: 'rejected', reason: 'FORBIDDEN' });
    }
    const [other] = await ingestSessions(ctx.deps, physioB, [mine()]);
    expect(other).toMatchObject({ status: 'rejected', reason: 'NOT_FOUND' });
    const [root] = await ingestSessions(ctx.deps, sysadmin, [mine()]);
    expect(root).toMatchObject({ status: 'rejected', reason: 'FORBIDDEN' });
  });

  it('stops uploads after consent is withdrawn', async () => {
    await setConsent(ctx.deps, omar, 'p-omar', {
      syncSessions: false,
      shareWhatsApp: false,
    });
    const [result] = await ingestSessions(ctx.deps, omar, [mine()]);
    expect(result).toMatchObject({ status: 'rejected', reason: 'NO_CONSENT' });
  });

  it('keeps a session measured with an older pack, flagged for review', async () => {
    const [result] = await ingestSessions(ctx.deps, omar, [
      { ...mine(), packVersion: 2 },
    ]);
    expect(result).toEqual({
      id: mine().id,
      status: 'accepted',
      reviewFlags: ['PACK_VERSION_DIFFERS'],
    });
    expect(await reviewQueue(ctx.deps, physioA, 'p-omar')).toHaveLength(1);
  });

  it('flags sessions measured against a since-replaced reference, and all-abstain sessions', async () => {
    await approveReference(ctx.deps, physioA, {
      patientId: 'p-omar',
      packId: 'lower-limb.squat',
      packVersion: 1,
      engineVersion: 'coach-2026-11-02',
      side: 'left',
      baseDeg: 5,
      rangeDeg: 80,
      curve: [5, 40, 85, 40, 5],
      recordedAt: '2027-02-10T10:00:00.000Z',
    });
    const silent = {
      ...mine(),
      reps: mine().reps.map((r) => ({ ...r, assessed: false })),
    };
    const [result] = await ingestSessions(ctx.deps, omar, [silent]);
    expect(result).toMatchObject({
      status: 'accepted',
      reviewFlags: ['REFERENCE_RETIRED', 'NOTHING_ASSESSED'],
    });
  });

  it('refuses oversized batches', async () => {
    const batch = Array.from({ length: MAX_BATCH + 1 }, () => mine());
    const results = await ingestSessions(ctx.deps, omar, batch);
    expect(results.every((r) => r.status === 'rejected')).toBe(true);
  });

  it('audits every accepted upload and keeps the log append-only', async () => {
    await ingestSessions(ctx.deps, omar, [mine()]);
    await ingestSessions(ctx.deps, omar, [mine()]); // duplicate: no second event
    const log = await ctx.deps.store.auditFor('clinic-a');
    expect(log.filter((e) => e.action === 'session.upload')).toHaveLength(1);
    log.length = 0; // mutating a read copy does not touch the store
    expect((await ctx.deps.store.auditFor('clinic-a')).length).toBeGreaterThan(0);
  });
});

describe('clinical use cases', () => {
  it('retires, never overwrites, the old reference', async () => {
    const { deps, reference } = await clinicWithPlan();
    const next = await approveReference(deps, physioA, {
      patientId: 'p-omar',
      packId: 'lower-limb.squat',
      packVersion: 1,
      engineVersion: 'coach-2026-11-02',
      side: 'left',
      baseDeg: 5,
      rangeDeg: 80,
      curve: [5, 40, 85, 40, 5],
      recordedAt: '2027-02-10T10:00:00.000Z',
    });
    const old = await deps.store.getReference('clinic-a', reference.id);
    expect(old).toMatchObject({ status: 'retired', replacedBy: next.id, rangeDeg: 66 });
    expect(
      await deps.store.activeReferences('clinic-a', 'p-omar', 'lower-limb.squat'),
    ).toHaveLength(1);
  });

  it('lets only the assigned physio prescribe, against an active matching reference', async () => {
    const { deps, reference } = await clinicWithPlan();
    const input = {
      patientId: 'p-omar',
      packId: 'lower-limb.squat',
      packVersion: 1,
      side: 'left' as const,
      sets: 2,
      reps: 8,
      toleranceDeg: 10,
      referenceId: reference.id,
    };
    await expect(prescribe(deps, physioA2, input)).rejects.toMatchObject({
      code: 'FORBIDDEN',
    });
    await expect(prescribe(deps, physioB, input)).rejects.toMatchObject({
      code: 'NOT_FOUND',
    });
    await expect(
      prescribe(deps, physioA, { ...input, side: 'right' }),
    ).rejects.toMatchObject({ code: 'INVALID' });
    await expect(
      prescribe(deps, physioA, { ...input, reps: 0 }),
    ).rejects.toBeInstanceOf(Denied);
  });

  it('hides patients of other clinics as not found and audits reads', async () => {
    const { deps } = await clinicWithPlan();
    await expect(patientSessions(deps, physioA, 'p-zed')).rejects.toMatchObject({
      code: 'NOT_FOUND',
    });
    await expect(patientSessions(deps, mona, 'p-omar')).rejects.toMatchObject({
      code: 'FORBIDDEN',
    });
    await patientSessions(deps, physioA, 'p-omar');
    const reads = (await deps.store.auditFor('clinic-a')).filter(
      (e) => e.action === 'session.read',
    );
    expect(reads).toHaveLength(1);
  });

  it('lets only the patient change consent', async () => {
    const { deps } = await clinicWithPlan();
    await expect(
      setConsent(deps, physioA, 'p-omar', {
        syncSessions: false,
        shareWhatsApp: false,
      }),
    ).rejects.toMatchObject({ code: 'FORBIDDEN' });
    const updated = await setConsent(deps, omar, 'p-omar', {
      syncSessions: true,
      shareWhatsApp: false,
    });
    expect(updated.consent.shareWhatsApp).toBe(false);
  });
});

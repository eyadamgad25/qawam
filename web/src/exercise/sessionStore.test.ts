import { beforeEach, describe, expect, it } from 'vitest';
import {
  deletePatient,
  loadSessions,
  saveSession,
  sessionStats,
  sessionsCsv,
  sessionsFor,
  sessionsInLastDays,
  whatsappSummary,
  whatsappUrl,
  type StoredRep,
  type StoredSession,
} from './sessionStore';

const rep = (
  index: number,
  range: number,
  cue = 'MATCHES_REFERENCE',
  posture: string | null = null,
): StoredRep => ({
  index,
  assessed: true,
  cue,
  rangeDeg: range,
  peakAngleDeg: range + 4,
  depthDiffDeg: range - 80,
  pathDiffDeg: 5,
  posture,
  startSeconds: null,
  endSeconds: null,
});

function session(
  id: string,
  day: number,
  ranges: number[],
  patient = 'Mona',
): StoredSession {
  return {
    id,
    patient,
    packId: 'lower-limb.squat',
    dateIso: new Date(2026, 9, day, 10, 0).toISOString(),
    mode: 'live',
    side: 'left',
    toleranceDeg: 10,
    referenceRangeDeg: 80,
    goniometerDeg: null,
    reps: ranges.map((r, i) =>
      rep(i, r, Math.abs(r - 80) <= 10 ? 'MATCHES_REFERENCE' : 'LESS_THAN_REFERENCE'),
    ),
  };
}

beforeEach(() => {
  for (const s of loadSessions()) deletePatient(s.patient);
});

describe('session store', () => {
  it('saves, sorts and filters sessions by patient', () => {
    saveSession(session('b', 20, [70, 75]));
    saveSession(session('a', 18, [55, 60]));
    saveSession(session('c', 19, [50], 'Omar'));
    expect(sessionsFor('Mona').map((s) => s.id)).toEqual(['a', 'b']);
    expect(sessionsFor('Omar')).toHaveLength(1);
    deletePatient('Omar');
    expect(sessionsFor('Omar')).toHaveLength(0);
  });

  it('summarises a session and counts adherence', () => {
    const s = session('a', 20, [60, 85, 90]);
    s.reps.push({
      ...rep(3, 0),
      assessed: false,
      cue: 'VIEW_MISMATCH',
      rangeDeg: null,
    });
    s.reps[1]!.posture = 'hip_flexion';
    expect(sessionStats(s)).toMatchObject({
      reps: 4,
      assessed: 3,
      matches: 2,
      postureIssues: 1,
      maxRangeDeg: 90,
    });
    expect(sessionStats(s).meanRangeDeg).toBeCloseTo(78.33, 1);
    const now = new Date(2026, 9, 21);
    expect(
      sessionsInLastDays([session('x', 20, [1]), session('y', 10, [1])], 7, now),
    ).toBe(1);
  });

  it('writes an Arabic WhatsApp summary with progress since the first session', () => {
    const sessions = [session('a', 18, [50, 55]), session('b', 20, [75, 80])];
    const text = whatsappSummary('Mona', sessions, new Date(2026, 9, 21));
    expect(text).toContain('Mona');
    expect(text).toContain('الجلسات في آخر 7 أيام: 2');
    expect(text).toContain('التغيّر منذ أول جلسة: +25°');
    expect(text).toContain('ليس تشخيصًا');
    expect(whatsappSummary('Mona', [])).toContain('لا توجد جلسات');
    expect(whatsappUrl('مرحبا', '+20 10 1234')).toBe(
      `https://wa.me/20101234?text=${encodeURIComponent('مرحبا')}`,
    );
  });

  it('exports one CSV row per rep for the accuracy study', () => {
    const csv = sessionsCsv([session('a', 18, [50, 55])])
      .trim()
      .split('\n');
    expect(csv[0]).toContain('peak_angle_deg');
    expect(csv).toHaveLength(3);
    expect(csv[1]).toContain('lower-limb.squat');
    expect(csv[1]!.split(',')).toHaveLength(csv[0]!.split(',').length);
  });
});

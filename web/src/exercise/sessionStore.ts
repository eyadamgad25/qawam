/**
 * Session history for the progress report, kept in this browser only.
 *
 * Prototype storage: localStorage on the device that ran the session. A real
 * deployment moves this to the clinic's server with patient consent. Every
 * read and write is wrapped so the page still works when storage is blocked.
 */
import { packById, packCopy } from './exercisePack';
import type { LiveRepFeedback } from './liveCoach';
import type { RepFeedback } from './session';

export interface StoredRep {
  index: number;
  assessed: boolean;
  cue: string | null;
  /** range of motion from the session's resting angle (deg) */
  rangeDeg: number | null;
  /** measured angle at the top of the rep, 2D camera angle (deg) */
  peakAngleDeg: number | null;
  depthDiffDeg: number | null;
  pathDiffDeg: number | null;
  posture: string | null;
  startSeconds: number | null;
  endSeconds: number | null;
}

export interface StoredSession {
  id: string;
  patient: string;
  packId: string;
  dateIso: string;
  mode: 'live' | 'file';
  side: string;
  toleranceDeg: number;
  referenceRangeDeg: number;
  goniometerDeg: number | null;
  reps: StoredRep[];
}

export interface SessionStats {
  reps: number;
  assessed: number;
  matches: number;
  postureIssues: number;
  meanRangeDeg: number | null;
  maxRangeDeg: number | null;
}

const KEY = 'qawam.sessions.v1';
let memory: StoredSession[] = [];

function storage(): Storage | null {
  try {
    return globalThis.localStorage ?? null;
  } catch {
    return null;
  }
}

export function loadSessions(): StoredSession[] {
  try {
    const raw = storage()?.getItem(KEY);
    if (raw) {
      const parsed: unknown = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        return parsed as StoredSession[];
      }
    }
  } catch {
    // fall back to memory
  }
  return [...memory];
}

function writeSessions(sessions: StoredSession[]): void {
  memory = [...sessions];
  try {
    storage()?.setItem(KEY, JSON.stringify(sessions));
  } catch {
    // memory copy still works for this page
  }
}

export function saveSession(session: StoredSession): void {
  writeSessions([...loadSessions().filter((s) => s.id !== session.id), session]);
}

export function deletePatient(patient: string): void {
  writeSessions(loadSessions().filter((s) => s.patient !== patient));
}

export function sessionsFor(patient: string, packId?: string): StoredSession[] {
  return loadSessions()
    .filter(
      (s) => s.patient === patient && (packId === undefined || s.packId === packId),
    )
    .sort((a, b) => a.dateIso.localeCompare(b.dateIso));
}

export function newSessionId(now = new Date()): string {
  return `${now.getTime().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

export function repsFromLive(
  reps: readonly LiveRepFeedback[],
  referenceRangeDeg: number,
): StoredRep[] {
  return reps.map((rep) =>
    rep.assessed
      ? {
          index: rep.index,
          assessed: true,
          cue: rep.cue,
          rangeDeg: referenceRangeDeg + rep.comparison.depthDiffDeg,
          peakAngleDeg: rep.curve.length ? Math.max(...rep.curve) : null,
          depthDiffDeg: rep.comparison.depthDiffDeg,
          pathDiffDeg: rep.comparison.dtwMeanAbsDeg,
          posture: rep.posture?.angle ?? null,
          startSeconds: null,
          endSeconds: null,
        }
      : {
          index: rep.index,
          assessed: false,
          cue: rep.reason,
          rangeDeg: null,
          peakAngleDeg: null,
          depthDiffDeg: null,
          pathDiffDeg: null,
          posture: null,
          startSeconds: null,
          endSeconds: null,
        },
  );
}

export function repsFromFile(
  reps: readonly RepFeedback[],
  peaks: readonly number[],
  referenceRangeDeg: number,
): StoredRep[] {
  return reps.map((rep) => ({
    index: rep.index,
    assessed: true,
    cue: rep.cue,
    rangeDeg: referenceRangeDeg + rep.comparison.depthDiffDeg,
    peakAngleDeg: peaks[rep.index] ?? null,
    depthDiffDeg: rep.comparison.depthDiffDeg,
    pathDiffDeg: rep.comparison.dtwMeanAbsDeg,
    posture: rep.posture?.angle ?? null,
    startSeconds: rep.startSeconds,
    endSeconds: rep.endSeconds,
  }));
}

export function sessionStats(session: StoredSession): SessionStats {
  const assessed = session.reps.filter((r) => r.assessed);
  const ranges = assessed
    .map((r) => r.rangeDeg)
    .filter((v): v is number => v !== null && Number.isFinite(v));
  return {
    reps: session.reps.length,
    assessed: assessed.length,
    matches: assessed.filter((r) => r.cue === 'MATCHES_REFERENCE').length,
    postureIssues: assessed.filter((r) => r.posture !== null).length,
    meanRangeDeg: ranges.length
      ? ranges.reduce((a, b) => a + b, 0) / ranges.length
      : null,
    maxRangeDeg: ranges.length ? Math.max(...ranges) : null,
  };
}

/** Sessions done in the last ``days`` days (adherence). */
export function sessionsInLastDays(
  sessions: readonly StoredSession[],
  days: number,
  now = new Date(),
): number {
  const since = now.getTime() - days * 24 * 3600 * 1000;
  return sessions.filter((s) => new Date(s.dateIso).getTime() >= since).length;
}

function dayLabel(iso: string): string {
  const d = new Date(iso);
  return `${d.getDate()}/${d.getMonth() + 1}`;
}

/** Short Arabic summary for the physio, ready for WhatsApp. */
export function whatsappSummary(
  patient: string,
  sessions: readonly StoredSession[],
  now = new Date(),
): string {
  if (sessions.length === 0) {
    return `قوام: لا توجد جلسات مسجّلة للمريض ${patient} بعد.`;
  }
  const last = sessions.at(-1)!;
  const pack = packById(last.packId);
  const stats = sessionStats(last);
  const first = sessionStats(sessions[0]!);
  const lines = [
    `قوام — ملخص ${pack.names.ar} للمريض: ${patient}`,
    `الجلسات في آخر 7 أيام: ${sessionsInLastDays(sessions, 7, now)}`,
    `آخر جلسة (${dayLabel(last.dateIso)}): ${stats.reps} تكرارات، ${stats.matches} قريبة من المرجع`,
  ];
  if (stats.meanRangeDeg !== null) {
    lines.push(
      `متوسط مدى ${packCopy(pack).measureAr}: ${Math.round(stats.meanRangeDeg)}° (المرجع ${Math.round(last.referenceRangeDeg)}°)`,
    );
  }
  if (
    sessions.length > 1 &&
    first.meanRangeDeg !== null &&
    stats.meanRangeDeg !== null
  ) {
    const change = Math.round(stats.meanRangeDeg - first.meanRangeDeg);
    lines.push(`التغيّر منذ أول جلسة: ${change > 0 ? '+' : ''}${change}°`);
  }
  if (stats.postureIssues > 0) {
    lines.push(`ملاحظات وضعية الجسم: ${stats.postureIssues} تكرارات`);
  }
  if (stats.assessed < stats.reps) {
    lines.push(`تكرارات لم تُقيَّم بسبب التصوير: ${stats.reps - stats.assessed}`);
  }
  lines.push('قياس بالكاميرا من نموذج بحثي، وليس تشخيصًا.');
  return lines.join('\n');
}

/** wa.me link; with no number WhatsApp asks whom to send to. */
export function whatsappUrl(text: string, phone = ''): string {
  const digits = phone.replace(/\D/g, '');
  const target = digits ? `https://wa.me/${digits}` : 'https://wa.me/';
  return `${target}?text=${encodeURIComponent(text)}`;
}

const CSV_HEADER = [
  'patient',
  'exercise',
  'date',
  'mode',
  'side',
  'rep',
  'assessed',
  'cue',
  'range_deg',
  'peak_angle_deg',
  'reference_range_deg',
  'depth_diff_deg',
  'path_diff_deg',
  'posture',
  'start_s',
  'end_s',
  'tolerance_deg',
  'goniometer_reference_deg',
];

function csvCell(value: unknown): string {
  if (value === null || value === undefined) {
    return '';
  }
  const text =
    typeof value === 'number' ? String(Math.round(value * 10) / 10) : String(value);
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

/** One row per rep, for the goniometer study and the physio's records. */
export function sessionsCsv(sessions: readonly StoredSession[]): string {
  const rows = [CSV_HEADER.join(',')];
  for (const s of sessions) {
    for (const r of s.reps) {
      rows.push(
        [
          s.patient,
          s.packId,
          s.dateIso,
          s.mode,
          s.side,
          r.index + 1,
          r.assessed ? 1 : 0,
          r.cue,
          r.rangeDeg,
          r.peakAngleDeg,
          s.referenceRangeDeg,
          r.depthDiffDeg,
          r.pathDiffDeg,
          r.posture,
          r.startSeconds,
          r.endSeconds,
          s.toleranceDeg,
          s.goniometerDeg,
        ]
          .map(csvCell)
          .join(','),
      );
    }
  }
  return rows.join('\n') + '\n';
}

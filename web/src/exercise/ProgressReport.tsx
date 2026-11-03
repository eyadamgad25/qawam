import { tr } from '../i18n';
import { useState } from 'react';
import { packById, packCopy } from './exercisePack';
import {
  deletePatient,
  sessionStats,
  sessionsCsv,
  sessionsFor,
  sessionsInLastDays,
  whatsappSummary,
  whatsappUrl,
  type StoredSession,
} from './sessionStore';

const PHONE_KEY = 'qawam.physioPhone';

function readPhone(): string {
  try {
    return globalThis.localStorage?.getItem(PHONE_KEY) ?? '';
  } catch {
    return '';
  }
}

function writePhone(value: string): void {
  try {
    globalThis.localStorage?.setItem(PHONE_KEY, value);
  } catch {
    // optional convenience
  }
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return `${d.getDate()}/${d.getMonth() + 1} ${String(d.getHours()).padStart(2, '0')}:${String(
    d.getMinutes(),
  ).padStart(2, '0')}`;
}

/** Range of motion per session against the reference range. */
export function ProgressChart({ sessions }: { sessions: readonly StoredSession[] }) {
  const points = sessions
    .map((s) => ({ s, mean: sessionStats(s).meanRangeDeg }))
    .filter((p): p is { s: StoredSession; mean: number } => p.mean !== null);
  if (points.length === 0) {
    return (
      <p className="field-help">
        {tr(
          'لا توجد تكرارات مقيّمة بعد لرسم التقدم.',
          'No judged reps yet to chart progress.',
        )}
      </p>
    );
  }
  const width = 600;
  const height = 220;
  const pad = { left: 44, right: 16, top: 16, bottom: 34 };
  const ref = sessions.at(-1)!.referenceRangeDeg;
  const values = [...points.map((p) => p.mean), ref];
  const top = Math.max(...values) * 1.15 || 10;
  const x = (i: number) =>
    pad.left +
    (points.length === 1 ? 0.5 : i / (points.length - 1)) *
      (width - pad.left - pad.right);
  const y = (v: number) => pad.top + (1 - v / top) * (height - pad.top - pad.bottom);
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((t) => Math.round(t * top));
  const path = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(p.mean).toFixed(1)}`)
    .join(' ');
  return (
    <svg
      className="progress-chart"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={tr(
        'مدى الحركة في كل جلسة مقارنةً بالمرجع',
        'Range of motion per session against the reference',
      )}
    >
      {ticks.map((t) => (
        <g key={t}>
          <line
            x1={pad.left}
            x2={width - pad.right}
            y1={y(t)}
            y2={y(t)}
            className="grid"
          />
          <text x={pad.left - 6} y={y(t) + 4} className="axis" textAnchor="end">
            {t}°
          </text>
        </g>
      ))}
      <line
        x1={pad.left}
        x2={width - pad.right}
        y1={y(ref)}
        y2={y(ref)}
        className="reference-line"
      />
      <text
        x={width - pad.right}
        y={y(ref) - 6}
        className="reference-label"
        textAnchor="start"
        direction="rtl"
      >
        {tr(`المرجع ${Math.round(ref)}°`, `Reference ${Math.round(ref)}°`)}
      </text>
      <path d={path} className="progress-line" />
      {points.map((p, i) => (
        <g key={p.s.id}>
          <circle cx={x(i)} cy={y(p.mean)} r={5} className="progress-dot" />
          <text x={x(i)} y={height - 12} className="axis" textAnchor="middle">
            {new Date(p.s.dateIso).getDate()}/{new Date(p.s.dateIso).getMonth() + 1}
          </text>
        </g>
      ))}
    </svg>
  );
}

export default function ProgressReport({
  patient,
  packId,
  refreshKey,
}: {
  patient: string;
  packId: string;
  refreshKey: number;
}) {
  const [phone, setPhone] = useState(readPhone);
  const [cleared, setCleared] = useState(0);
  void refreshKey;
  void cleared;
  const pack = packById(packId);
  const copy = packCopy(pack);
  const sessions = sessionsFor(patient, packId);
  const last = sessions.at(-1);
  const lastStats = last ? sessionStats(last) : null;
  const summary = whatsappSummary(patient, sessions);

  function downloadCsv() {
    const blob = new Blob(['﻿' + sessionsCsv(sessionsFor(patient))], {
      type: 'text/csv;charset=utf-8',
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `qawam-${patient.replace(/\s+/g, '-')}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="session-summary physio-report" aria-labelledby="progress-title">
      <div className="summary-heading">
        <div>
          <p className="summary-kicker">
            {tr('تقرير الأخصائي', 'Physio report')} · {tr(pack.names.ar, pack.names.en)}
          </p>
          <h2 id="progress-title">
            {tr('تقدّم المريض', 'Patient progress')}: {patient}
          </h2>
        </div>
        <span className="simulation-badge">
          {tr('محفوظ على هذا الجهاز فقط', 'Saved on this device only')}
        </span>
      </div>
      {sessions.length === 0 ? (
        <p>
          {tr(
            'لا توجد جلسات محفوظة لهذا المريض في هذا التمرين بعد. كل تمرين ينتهي في الخطوة ٢ يُحفظ هنا تلقائيًا.',
            'No saved sessions for this patient and exercise yet. Every exercise finished in step 2 is saved here automatically.',
          )}
        </p>
      ) : (
        <>
          <div className="summary-metrics">
            <div className="summary-metric">
              <span className="metric-value" dir="ltr">
                {sessions.length}
              </span>
              <span>{tr('جلسات', 'Sessions')}</span>
            </div>
            <div className="summary-metric">
              <span className="metric-value" dir="ltr">
                {sessionsInLastDays(sessions, 7)}
              </span>
              <span>{tr('جلسات في آخر 7 أيام', 'Sessions in the last 7 days')}</span>
            </div>
            <div className="summary-metric">
              <span className="metric-value" dir="ltr">
                {lastStats ? `${lastStats.matches}/${lastStats.reps}` : '—'}
              </span>
              <span>
                {tr(
                  'قريبة من المرجع في آخر جلسة',
                  'Close to the reference, last session',
                )}
              </span>
            </div>
          </div>
          <h3 className="report-subtitle">
            {tr('مدى', 'Range of')} {copy.measureAr}{' '}
            {tr('في كل جلسة (متوسط التكرارات)', 'per session (mean of reps)')}
          </h3>
          <ProgressChart sessions={sessions} />
          <table className="report-table">
            <thead>
              <tr>
                <th>{tr('التاريخ', 'Date')}</th>
                <th>{tr('الطريقة', 'Method')}</th>
                <th>{tr('تكرارات', 'Reps')}</th>
                <th>{tr('قريبة من المرجع', 'Close to reference')}</th>
                <th>{tr('متوسط المدى', 'Mean range')}</th>
                <th>{tr('ملاحظات وضعية', 'Posture notes')}</th>
              </tr>
            </thead>
            <tbody>
              {[...sessions].reverse().map((s) => {
                const st = sessionStats(s);
                return (
                  <tr key={s.id}>
                    <td dir="ltr">{formatDate(s.dateIso)}</td>
                    <td>
                      {s.mode === 'live'
                        ? tr('كاميرا', 'Camera')
                        : tr('فيديو', 'Video')}
                    </td>
                    <td>{st.reps}</td>
                    <td>{st.matches}</td>
                    <td dir="ltr">
                      {st.meanRangeDeg === null
                        ? '—'
                        : `${Math.round(st.meanRangeDeg)}°`}
                    </td>
                    <td>{st.postureIssues}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="field-help report-note">
            {tr(
              'المدى مقاس بالكاميرا من وضع راحة المريض في كل جلسة (زاوية ثنائية الأبعاد)، وهو نموذج بحثي غير معتمد سريريًا وليس تشخيصًا.',
              'Range is measured by the camera from the patient’s resting pose in each session (a 2D angle). This is a research prototype, not clinically approved and not a diagnosis.',
            )}
          </p>
        </>
      )}
      <div className="report-actions no-print">
        <label className="pain-demo-label" htmlFor="physio-phone">
          {tr(
            'رقم واتساب الأخصائي (اختياري، مع كود الدولة مثل 2010…)',
            'Physio’s WhatsApp number (optional, with country code, e.g. 2010…)',
          )}
        </label>
        <input
          id="physio-phone"
          type="tel"
          inputMode="tel"
          dir="ltr"
          value={phone}
          onChange={(event) => {
            setPhone(event.currentTarget.value);
            writePhone(event.currentTarget.value);
          }}
        />
        <div className="report-buttons">
          <a
            className="demo-run-button whatsapp-button"
            href={whatsappUrl(summary, phone)}
            target="_blank"
            rel="noreferrer"
          >
            {tr('أرسل الملخص على واتساب', 'Send the summary on WhatsApp')}
          </a>
          <button
            className="secondary-button"
            type="button"
            disabled={sessions.length === 0}
            onClick={() => window.print()}
          >
            {tr('اطبع التقرير / احفظه PDF', 'Print the report / save as PDF')}
          </button>
          <button
            className="secondary-button"
            type="button"
            disabled={sessions.length === 0}
            onClick={downloadCsv}
          >
            {tr('تنزيل البيانات (CSV)', 'Download the data (CSV)')}
          </button>
          <button
            className="secondary-button danger"
            type="button"
            disabled={sessions.length === 0}
            onClick={() => {
              deletePatient(patient);
              setCleared((n) => n + 1);
            }}
          >
            {tr('امسح بيانات هذا المريض', 'Delete this patient’s data')}
          </button>
        </div>
        <details>
          <summary>
            {tr('نص الملخص الذي سيُرسل', 'Summary text that will be sent')}
          </summary>
          <pre className="whatsapp-preview">{summary}</pre>
        </details>
      </div>
    </section>
  );
}

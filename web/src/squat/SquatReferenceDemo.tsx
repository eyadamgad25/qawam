import { useMemo, useState } from 'react';
import { SQUAT_PACK } from './exercisePack';
import type { PoseFrame } from './poseFrames';
import {
  analyseClip,
  assessSession,
  gateClip,
  TEST_DEFAULT_TOLERANCE_DEG,
  type ClipAnalysis,
} from './squatSession';
import LiveCamera from './LiveCamera';
import { extractPoseFrames } from './videoPose';

type Stage = 'reference' | 'home';
type Source = 'file' | 'camera';

function SourcePicker({
  value,
  onChange,
  label,
}: {
  value: Source;
  onChange: (source: Source) => void;
  label: string;
}) {
  return (
    <div className="scenario-picker" role="group" aria-label={label}>
      <button
        type="button"
        aria-pressed={value === 'camera'}
        onClick={() => onChange('camera')}
      >
        بالكاميرا الآن
      </button>
      <button
        type="button"
        aria-pressed={value === 'file'}
        onClick={() => onChange('file')}
      >
        من ملف فيديو
      </button>
    </div>
  );
}

/** Parse a positive number typed by the physio; null if empty. */
export function parseOptionalDegrees(value: string): number | null {
  const text = value.trim();
  if (!text) {
    return null;
  }
  const number = Number(text);
  if (!Number.isFinite(number) || number <= 0 || number >= 180) {
    throw new Error('أدخل رقمًا بين 0 و180 درجة.');
  }
  return number;
}

export function formatDegrees(value: number, signed = false): string {
  const rounded = Math.round(value);
  return `${signed && rounded > 0 ? '+' : ''}${rounded}°`;
}

export function CurveChart({
  reference,
  rep,
}: {
  reference: readonly number[];
  rep: readonly number[];
}) {
  const width = 240;
  const height = 90;
  const max = Math.max(...reference, ...rep, 1);
  const toPath = (curve: readonly number[]) =>
    curve
      .map((value, i) => {
        const x = (i / Math.max(1, curve.length - 1)) * width;
        const y = height - (value / max) * (height - 8) - 4;
        return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');
  return (
    <svg
      className="curve-chart"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label="منحنى ثني الركبة: المرجع مقابل هذا التكرار"
    >
      <path d={toPath(reference)} className="curve-reference" />
      <path d={toPath(rep)} className="curve-rep" />
    </svg>
  );
}

function ClipStatus({ clip }: { clip: ClipAnalysis }) {
  const gate = gateClip(clip);
  return (
    <div
      className={gate.ok ? 'clip-status clip-ok' : 'clip-status clip-refused'}
      role="status"
    >
      <p>
        <strong>{gate.ok ? 'التصوير مناسب' : 'لا أستطيع التقييم'}</strong> —{' '}
        {gate.messageAr}
      </p>
      <p className="clip-facts">
        <span>اكتشاف الجسم: {Math.round(clip.detectionRate * 100)}%</span>
        <span>
          زاوية التصوير (frontalness):{' '}
          {clip.view.frontalness === null ? '—' : clip.view.frontalness.toFixed(2)}{' '}
          (المقبول للتصوير الجانبي حتى {clip.view.cutoff})
        </span>
        <span>الرجل المتابَعة: {clip.side === 'left' ? 'اليسرى' : 'اليمنى'}</span>
        <span>تكرارات وُجدت: {clip.reps.length}</span>
      </p>
    </div>
  );
}

export default function SquatReferenceDemo() {
  const [reference, setReference] = useState<ClipAnalysis | null>(null);
  const [home, setHome] = useState<ClipAnalysis | null>(null);
  const [busy, setBusy] = useState<Stage | null>(null);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [referenceRep, setReferenceRep] = useState(0);
  const [toleranceText, setToleranceText] = useState(
    String(TEST_DEFAULT_TOLERANCE_DEG),
  );
  const [goniometerText, setGoniometerText] = useState('');
  const [referenceSource, setReferenceSource] = useState<Source>('camera');
  const [homeSource, setHomeSource] = useState<Source>('camera');

  async function analyse(stage: Stage, file: File | undefined) {
    if (!file) {
      return;
    }
    if (!file.type.startsWith('video/')) {
      setError('اختر ملف فيديو صالحًا.');
      return;
    }
    setError(null);
    setBusy(stage);
    setProgress(0);
    if (stage === 'reference') {
      setReference(null);
      setHome(null);
      setReferenceRep(0);
    } else {
      setHome(null);
    }
    try {
      const frames: PoseFrame[] = await extractPoseFrames(file, setProgress);
      const clip = analyseClip(frames, SQUAT_PACK);
      if (stage === 'reference') {
        setReference(clip);
      } else {
        setHome(clip);
      }
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : 'تعذّر تحميل نموذج MediaPipe. تحقق من اتصال الإنترنت ثم أعد المحاولة.',
      );
    } finally {
      setBusy(null);
    }
  }

  const settings = useMemo(() => {
    try {
      const tolerance = parseOptionalDegrees(toleranceText);
      const goniometer = parseOptionalDegrees(goniometerText);
      if (tolerance === null) {
        return { error: 'أدخل هامش السماح.' } as const;
      }
      return { tolerance, goniometer } as const;
    } catch (cause) {
      return {
        error: cause instanceof Error ? cause.message : 'قيمة غير صالحة.',
      } as const;
    }
  }, [toleranceText, goniometerText]);

  const referenceReady = reference !== null && gateClip(reference).ok;
  const result = useMemo(() => {
    if (!reference || !home || !referenceReady || 'error' in settings) {
      return null;
    }
    return assessSession(
      reference,
      referenceRep,
      home,
      settings.tolerance,
      settings.goniometer ?? null,
    );
  }, [reference, home, referenceReady, referenceRep, settings]);
  const referenceCurve = reference?.reps[referenceRep]?.curve ?? [];

  return (
    <section className="session-summary squat-demo" aria-labelledby="squat-demo-title">
      <div className="summary-heading">
        <div>
          <p className="summary-kicker">تمرين واحد من البداية للنهاية · تجريبي</p>
          <h2 id="squat-demo-title">سكوات مقارنةً بتكرارك المرجعي</h2>
        </div>
        <span className="simulation-badge">الفيديو لا يُرفع</span>
      </div>
      <p>
        يسجّل الأخصائي معك تكرارًا صحيحًا في العيادة، ثم يقارن قوام كل تكرار في البيت
        بهذا التكرار نفسه، وليس بقاعدة واحدة للجميع. إذا لم تكن زاوية التصوير مناسبة،
        يقول قوام إنه لا يراك جيدًا بدل أن يخمّن.
      </p>
      <div className="cannot-assess-result" role="note">
        <strong>تنبيه: نموذج بحثي غير معتمد سريريًا</strong>
        <p>
          حزمة السكوات وحدودها تنتظر موافقة أخصائي علاج طبيعي. النتائج للتجربة فقط ولا
          تُستخدم لتغيير خطة العلاج.
        </p>
        <details>
          <summary>ماذا يقيس قوام هنا؟</summary>
          <ul>
            <li>
              زاوية ثني الركبة ثنائية الأبعاد للرجل الأقرب للكاميرا، من نقاط MediaPipe.
            </li>
            <li>
              يقبل التقييم فقط إذا كان التصوير من الجنب: نسبة عرض الكتفين إلى طول الجذع
              لا تتجاوز 0.178 (قيمة بحثية من بيانات REHAB24-6).
            </li>
            <li>
              لكل تكرار: فرق أقصى عمق عن المرجع، ومتوسط فرق المسار بعد محاذاة الزمن
              (DTW).
            </li>
            <li>
              في التجربة البحثية على 5 أشخاص لم تُستخدم بياناتهم في الضبط، أخطأ القياس
              في 3 من 88 تكرار سكوات صُوّر من الجنب.
            </li>
          </ul>
        </details>
      </div>

      <div className="squat-step">
        <h3>١. فيديو المرجع — يُسجَّل مع الأخصائي في العيادة</h3>
        <p className="field-help">
          صوّر من الجنب، والجسم كله ظاهر، وأدِّ تكرارًا واحدًا على الأقل.
        </p>
        <SourcePicker
          value={referenceSource}
          onChange={setReferenceSource}
          label="طريقة تسجيل المرجع"
        />
        {referenceSource === 'file' && (
          <>
            <label className="pain-demo-label" htmlFor="squat-reference-video">
              ملف فيديو المرجع
            </label>
            <input
              id="squat-reference-video"
              type="file"
              accept="video/*"
              disabled={busy !== null}
              onChange={(event) =>
                void analyse('reference', event.currentTarget.files?.[0])
              }
            />
          </>
        )}
        {referenceSource === 'camera' &&
          (reference ? (
            <button
              className="secondary-button"
              type="button"
              onClick={() => {
                setReference(null);
                setHome(null);
              }}
            >
              سجّل مرجعًا جديدًا بالكاميرا
            </button>
          ) : (
            <LiveCamera
              mode="reference"
              onReference={(frames) => {
                setReference(analyseClip(frames, SQUAT_PACK));
                setHome(null);
                setReferenceRep(0);
              }}
            />
          ))}
        {busy === 'reference' && <Progress value={progress} />}
        {reference && <ClipStatus clip={reference} />}
        {reference && referenceReady && (
          <div className="squat-settings">
            <label className="pain-demo-label" htmlFor="squat-reference-rep">
              التكرار المرجعي
            </label>
            <select
              id="squat-reference-rep"
              value={referenceRep}
              onChange={(event) => setReferenceRep(Number(event.currentTarget.value))}
            >
              {reference.reps.map((rep, index) => (
                <option key={rep.start} value={index}>
                  تكرار {index + 1} — أقصى ثني مقاس {formatDegrees(rep.peakDeg)}
                </option>
              ))}
            </select>
            <label className="pain-demo-label" htmlFor="squat-tolerance">
              هامش السماح بالدرجات (يحدده الأخصائي)
            </label>
            <input
              id="squat-tolerance"
              type="number"
              min="1"
              max="45"
              inputMode="decimal"
              value={toleranceText}
              onChange={(event) => setToleranceText(event.currentTarget.value)}
            />
            <p className="field-help">
              القيمة الافتراضية {TEST_DEFAULT_TOLERANCE_DEG}° قيمة اختبار فقط، وليست
              قيمة سريرية.
            </p>
            <label className="pain-demo-label" htmlFor="squat-goniometer">
              قراءة الجونيوميتر لثني الركبة في التكرار المرجعي (اختياري)
            </label>
            <input
              id="squat-goniometer"
              type="number"
              min="1"
              max="179"
              inputMode="decimal"
              value={goniometerText}
              onChange={(event) => setGoniometerText(event.currentTarget.value)}
            />
            <p className="field-help">
              إذا أدخلها الأخصائي، يعرض قوام العمق بالدرجات الحقيقية بعد تصحيح فرق
              الكاميرا.
            </p>
            {'error' in settings && (
              <p className="pose-error" role="alert">
                {settings.error}
              </p>
            )}
          </div>
        )}
      </div>

      <div className="squat-step" aria-disabled={!referenceReady}>
        <h3>٢. التمرين في البيت</h3>
        {!referenceReady && (
          <p className="field-help">سجّل فيديو مرجعيًا مناسبًا أولًا.</p>
        )}
        <SourcePicker
          value={homeSource}
          onChange={setHomeSource}
          label="طريقة التمرين"
        />
        {homeSource === 'camera' &&
          referenceReady &&
          !('error' in settings) &&
          referenceCurve.length > 1 && (
            <LiveCamera
              key={`${referenceRep}-${settings.tolerance}`}
              mode="home"
              referenceCurve={referenceCurve}
              toleranceDeg={settings.tolerance}
            />
          )}
        {homeSource === 'file' && (
          <>
            <label className="pain-demo-label" htmlFor="squat-home-video">
              ملف فيديو التمرين
            </label>
            <input
              id="squat-home-video"
              type="file"
              accept="video/*"
              disabled={!referenceReady || busy !== null}
              onChange={(event) => void analyse('home', event.currentTarget.files?.[0])}
            />
          </>
        )}
        {busy === 'home' && <Progress value={progress} />}
        {home && <ClipStatus clip={home} />}
        {result?.status === 'CANNOT_ASSESS' && (
          <div className="cannot-assess-result" role="status">
            <h3>لا أراك جيدًا</h3>
            <p>{result.messageAr}</p>
            <span className="reason-code" dir="ltr">
              {result.reasons.join(', ')}
            </span>
          </div>
        )}
        {result?.status === 'ASSESSED' && home && (
          <div className="pose-session-result" role="status" aria-live="polite">
            <h3>{result.summaryAr}</h3>
            <p className="curve-legend">
              <span className="legend-reference">المرجع</span>
              <span className="legend-rep">هذا التكرار</span>
            </p>
            <ol className="rep-feedback-list">
              {result.reps.map((rep) => (
                <li key={rep.index} className="rep-feedback" data-cue={rep.cue}>
                  <div>
                    <strong>
                      تكرار {rep.index + 1} ({rep.startSeconds.toFixed(1)}–
                      {rep.endSeconds.toFixed(1)} ث)
                    </strong>
                    <p>{rep.messageAr}</p>
                    <p className="rep-numbers">
                      فرق العمق {formatDegrees(rep.comparison.depthDiffDeg, true)} · فرق
                      المسار {formatDegrees(rep.comparison.dtwMeanAbsDeg)}
                      {rep.calibratedPeakDeg !== null &&
                        ` · ثني الركبة المصحح ${formatDegrees(rep.calibratedPeakDeg)}`}
                    </p>
                  </div>
                  <CurveChart
                    reference={referenceCurve}
                    rep={home.reps[rep.index]?.curve ?? []}
                  />
                </li>
              ))}
            </ol>
          </div>
        )}
      </div>
      {error && (
        <p className="pose-error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}

function Progress({ value }: { value: number }) {
  return (
    <p className="analysis-progress" role="status" aria-live="polite">
      جارٍ تحليل الفيديو على جهازك… {Math.round(value * 100)}%
      <progress max={1} value={value} />
    </p>
  );
}

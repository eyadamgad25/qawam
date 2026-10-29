import { useMemo, useState } from 'react';
import {
  EXERCISE_PACKS,
  packById,
  packCopy,
  SQUAT_PACK,
  type ExercisePack,
} from './exercisePack';
import LiveCamera from './LiveCamera';
import type { LiveReference } from './liveCoach';
import type { PoseFrame } from './poseFrames';
import {
  analyseClip,
  assessSession,
  gateClip,
  repPosture,
  TEST_DEFAULT_TOLERANCE_DEG,
  type ClipAnalysis,
  type SideChoice,
} from './session';
import { extractPoseFrames } from './videoPose';

type Stage = 'reference' | 'home';
type Source = 'file' | 'camera';

/** Test defaults for the number of reps; the physio sets the real plan. */
export const TEST_DEFAULT_HOME_REPS = 8;
const REFERENCE_REPS = 2;

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

export function parseRepCount(value: string): number {
  const number = Number(value.trim());
  if (!Number.isInteger(number) || number < 1 || number > 30) {
    throw new Error('أدخل عدد تكرارات بين 1 و30.');
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
  label = 'منحنى الحركة: المرجع مقابل هذا التكرار',
}: {
  reference: readonly number[];
  rep: readonly number[];
  label?: string;
}) {
  const width = 240;
  const height = 90;
  const max = Math.max(...reference, ...rep, 1);
  const min = Math.min(...reference, ...rep, 0);
  const toPath = (curve: readonly number[]) =>
    curve
      .map((value, i) => {
        const x = (i / Math.max(1, curve.length - 1)) * width;
        const y = height - ((value - min) / (max - min || 1)) * (height - 8) - 4;
        return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');
  return (
    <svg
      className="curve-chart"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={label}
    >
      <path d={toPath(reference)} className="curve-reference" />
      <path d={toPath(rep)} className="curve-rep" />
    </svg>
  );
}

const SIDE_AR = { left: 'اليسرى', right: 'اليمنى' } as const;

function ClipStatus({ clip, pack }: { clip: ClipAnalysis; pack: ExercisePack }) {
  const gate = gateClip(clip);
  const limb = pack.packId.startsWith('upper-limb') ? 'الذراع' : 'الرجل';
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
          {pack.view === 'side'
            ? `(المقبول للتصوير الجانبي حتى ${clip.view.cutoff})`
            : `(المقبول للتصوير الأمامي من ${clip.view.cutoff})`}
        </span>
        <span>
          {limb} المتابَعة: {SIDE_AR[clip.side]}
        </span>
        <span>تكرارات وُجدت: {clip.reps.length}</span>
      </p>
    </div>
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

export default function ExerciseCoach() {
  const [packId, setPackId] = useState(SQUAT_PACK.packId);
  const pack = packById(packId);
  const copy = packCopy(pack);
  const [side, setSide] = useState<SideChoice>('auto');
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
  const [repsText, setRepsText] = useState(String(TEST_DEFAULT_HOME_REPS));
  const [referenceSource, setReferenceSource] = useState<Source>('camera');
  const [homeSource, setHomeSource] = useState<Source>('camera');

  function reset() {
    setReference(null);
    setHome(null);
    setReferenceRep(0);
    setError(null);
  }

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
      reset();
    } else {
      setHome(null);
    }
    try {
      const frames: PoseFrame[] = await extractPoseFrames(file, setProgress);
      if (stage === 'reference') {
        setReference(analyseClip(frames, pack, side));
      } else {
        // measure the same limb as the reference for one-sided exercises
        setHome(
          analyseClip(
            frames,
            pack,
            pack.sides === 'both' ? 'auto' : (reference?.side ?? side),
          ),
        );
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
      const reps = parseRepCount(repsText);
      if (tolerance === null) {
        return { error: 'أدخل هامش السماح.' } as const;
      }
      return { tolerance, goniometer, reps } as const;
    } catch (cause) {
      return {
        error: cause instanceof Error ? cause.message : 'قيمة غير صالحة.',
      } as const;
    }
  }, [toleranceText, goniometerText, repsText]);

  const referenceReady = reference !== null && gateClip(reference).ok;
  const chosenRep = reference?.reps[referenceRep];
  const result = useMemo(() => {
    if (!reference || !home || !referenceReady || 'error' in settings) {
      return null;
    }
    return assessSession(
      pack,
      reference,
      referenceRep,
      home,
      settings.tolerance,
      settings.goniometer ?? null,
    );
  }, [pack, reference, home, referenceReady, referenceRep, settings]);

  const liveReference: LiveReference | null =
    reference && chosenRep && chosenRep.curve.length > 1
      ? {
          curve: chosenRep.curve,
          baseDeg: reference.baseDeg,
          durationSeconds:
            (reference.times[chosenRep.end] ?? 0) -
            (reference.times[chosenRep.start] ?? 0),
          side: reference.side,
          posture: repPosture(reference, chosenRep.start, chosenRep.end),
        }
      : null;
  const liveRangeOk =
    liveReference !== null &&
    Math.max(...liveReference.curve) - liveReference.baseDeg >= 10;
  const referenceCurve = chosenRep?.curve ?? [];

  return (
    <section
      className="session-summary squat-demo"
      aria-labelledby="exercise-coach-title"
    >
      <div className="summary-heading">
        <div>
          <p className="summary-kicker">مدرب تمارين مباشر · تجريبي</p>
          <h2 id="exercise-coach-title">تمرينك مقارنةً بتكرارك المرجعي</h2>
        </div>
        <span className="simulation-badge">الفيديو لا يُرفع</span>
      </div>
      <p>
        يسجّل الأخصائي معك تكرارًا صحيحًا في العيادة، ثم يقارن قوام كل تكرار في البيت
        بهذا التكرار نفسه، وليس بقاعدة واحدة للجميع. إذا لم تكن زاوية التصوير مناسبة،
        يقول قوام إنه لا يراك جيدًا بدل أن يخمّن.
      </p>

      <div className="exercise-picker">
        <label className="pain-demo-label" htmlFor="exercise-pack">
          التمرين
        </label>
        <select
          id="exercise-pack"
          value={packId}
          disabled={busy !== null}
          onChange={(event) => {
            setPackId(event.currentTarget.value);
            setSide('auto');
            reset();
          }}
        >
          {EXERCISE_PACKS.map((item) => (
            <option key={item.packId} value={item.packId}>
              {item.names.ar}
            </option>
          ))}
        </select>
        <p className="field-help">
          {copy.setupAr} {pack.view === 'side' ? '(تصوير جانبي)' : '(تصوير أمامي)'}
        </p>
        {pack.sides !== 'both' && (
          <>
            <label className="pain-demo-label" htmlFor="exercise-side">
              {pack.packId.startsWith('upper-limb') ? 'الذراع' : 'الرجل'} التي تتمرن بها
            </label>
            <select
              id="exercise-side"
              value={side}
              disabled={busy !== null}
              onChange={(event) => {
                const value = event.currentTarget.value;
                setSide(value === 'left' || value === 'right' ? value : 'auto');
                reset();
              }}
            >
              <option value="auto">تلقائي: التي تتحرك أكثر</option>
              <option value="left">اليسرى</option>
              <option value="right">اليمنى</option>
            </select>
          </>
        )}
      </div>

      <div className="cannot-assess-result" role="note">
        <strong>تنبيه: نموذج بحثي غير معتمد سريريًا</strong>
        <p>
          حزم التمارين وحدودها تنتظر موافقة أخصائي علاج طبيعي. النتائج للتجربة فقط ولا
          تُستخدم لتغيير خطة العلاج.
        </p>
        <details>
          <summary>ماذا يقيس قوام هنا؟</summary>
          <ul>
            <li>
              {copy.measureAr} بالدرجات (زاوية ثنائية الأبعاد) من نقاط MediaPipe، للجهة{' '}
              {pack.sides === 'both' ? 'الأقرب للكاميرا' : 'التي تتمرن بها'}.
            </li>
            <li>
              يقبل التقييم فقط إذا كان التصوير{' '}
              {pack.view === 'side'
                ? 'من الجنب (نسبة عرض الكتفين إلى طول الجذع لا تتجاوز 0.178)'
                : 'من الأمام (نسبة عرض الكتفين إلى طول الجذع 0.601 على الأقل)'}
              ، وهي قيمة بحثية من بيانات REHAB24-6.
            </li>
            <li>
              لكل تكرار: فرق المدى عن المرجع مقاسًا من وضع راحتك، ومتوسط فرق المسار بعد
              محاذاة الزمن (DTW).
            </li>
            <li>{copy.evidenceAr}</li>
          </ul>
        </details>
      </div>

      <div className="squat-step">
        <h3>١. التكرار المرجعي — يُسجَّل مع الأخصائي في العيادة</h3>
        <p className="field-help">
          {copy.setupAr} أدِّ تكرارين صحيحين ببطء؛ يتوقف التسجيل بالكاميرا تلقائيًا
          بعدهما.
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
            <button className="secondary-button" type="button" onClick={reset}>
              سجّل مرجعًا جديدًا بالكاميرا
            </button>
          ) : (
            <LiveCamera
              key={`ref-${packId}-${side}`}
              pack={pack}
              mode="reference"
              targetReps={REFERENCE_REPS}
              onReference={(frames) => {
                setReference(analyseClip(frames, pack, side));
                setHome(null);
                setReferenceRep(0);
              }}
            />
          ))}
        {busy === 'reference' && <Progress value={progress} />}
        {reference && <ClipStatus clip={reference} pack={pack} />}
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
                  تكرار {index + 1} — مدى الحركة{' '}
                  {formatDegrees(rep.peakDeg - reference.baseDeg)}
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
            <label className="pain-demo-label" htmlFor="exercise-reps">
              عدد التكرارات في البيت (يحدده الأخصائي)
            </label>
            <input
              id="exercise-reps"
              type="number"
              min="1"
              max="30"
              inputMode="numeric"
              value={repsText}
              onChange={(event) => setRepsText(event.currentTarget.value)}
            />
            <p className="field-help">
              القيمة الافتراضية {TEST_DEFAULT_HOME_REPS} للتجربة فقط؛ ينتهي التمرين
              بالكاميرا تلقائيًا عند بلوغها.
            </p>
            <label className="pain-demo-label" htmlFor="squat-goniometer">
              قراءة الجونيوميتر لـ{copy.measureAr} في التكرار المرجعي (اختياري)
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
              إذا أدخلها الأخصائي، يعرض قوام الزاوية بالدرجات الحقيقية بعد تصحيح فرق
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
          <p className="field-help">سجّل تكرارًا مرجعيًا مناسبًا أولًا.</p>
        )}
        <SourcePicker
          value={homeSource}
          onChange={setHomeSource}
          label="طريقة التمرين"
        />
        {homeSource === 'camera' && referenceReady && !liveRangeOk && (
          <p className="pose-error" role="alert">
            التكرار المرجعي المختار يكاد لا يحتوي على حركة. اختر تكرارًا آخر أو سجّل
            المرجع من جديد.
          </p>
        )}
        {homeSource === 'camera' &&
          referenceReady &&
          liveReference &&
          liveRangeOk &&
          !('error' in settings) && (
            <LiveCamera
              key={`home-${packId}-${referenceRep}-${settings.tolerance}-${settings.reps}`}
              pack={pack}
              mode="home"
              reference={liveReference}
              toleranceDeg={settings.tolerance}
              targetReps={settings.reps}
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
        {homeSource === 'file' && home && <ClipStatus clip={home} pack={pack} />}
        {homeSource === 'file' && result?.status === 'CANNOT_ASSESS' && (
          <div className="cannot-assess-result" role="status">
            <h3>لا أراك جيدًا</h3>
            <p>{result.messageAr}</p>
            <span className="reason-code" dir="ltr">
              {result.reasons.join(', ')}
            </span>
          </div>
        )}
        {homeSource === 'file' &&
          result?.status === 'ASSESSED' &&
          home &&
          reference && (
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
                        فرق المدى {formatDegrees(rep.comparison.depthDiffDeg, true)} ·
                        فرق المسار {formatDegrees(rep.comparison.dtwMeanAbsDeg)}
                        {rep.calibratedPeakDeg !== null &&
                          ` · الزاوية المصححة ${formatDegrees(rep.calibratedPeakDeg)}`}
                      </p>
                    </div>
                    <CurveChart
                      reference={referenceCurve.map((v) => v - reference.baseDeg)}
                      rep={(home.reps[rep.index]?.curve ?? []).map(
                        (v) => v - home.baseDeg,
                      )}
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

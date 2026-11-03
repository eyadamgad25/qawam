import { tr } from '../i18n';
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  EXERCISE_PACKS,
  packById,
  packCopy,
  SQUAT_PACK,
  type ExercisePack,
} from './exercisePack';
import LiveCamera from './LiveCamera';
import ProgressReport from './ProgressReport';
import {
  newSessionId,
  repsFromFile,
  repsFromLive,
  saveSession,
  COACH_ENGINE_VERSION,
  type StoredRep,
} from './sessionStore';
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
import { DEMO_DEFAULTS, sourceOf } from '../demoDefaults';
import LiteratureNote from '../LiteratureNote';

type Stage = 'reference' | 'home';
type Source = 'file' | 'camera';

/** Default number of reps, from a published guideline; the physio sets the real plan. */
export const TEST_DEFAULT_HOME_REPS = DEMO_DEFAULTS.homeReps.value;
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
        {tr('بالكاميرا الآن', 'Camera now')}
      </button>
      <button
        type="button"
        aria-pressed={value === 'file'}
        onClick={() => onChange('file')}
      >
        {tr('من ملف فيديو', 'From a video file')}
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
    throw new Error(
      tr('أدخل رقمًا بين 0 و180 درجة.', 'Enter a number between 0 and 180 degrees.'),
    );
  }
  return number;
}

export function parseRepCount(value: string): number {
  const number = Number(value.trim());
  if (!Number.isInteger(number) || number < 1 || number > 30) {
    throw new Error(
      tr('أدخل عدد تكرارات بين 1 و30.', 'Enter a rep count between 1 and 30.'),
    );
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
  label = tr(
    'منحنى الحركة: المرجع مقابل هذا التكرار',
    'Movement curve: reference vs this rep',
  ),
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

const sideName = (side: 'left' | 'right') =>
  side === 'left' ? tr('اليسرى', 'Left') : tr('اليمنى', 'Right');

function ClipStatus({ clip, pack }: { clip: ClipAnalysis; pack: ExercisePack }) {
  const gate = gateClip(clip);
  const limb = pack.packId.startsWith('upper-limb')
    ? tr('الذراع', 'Arm')
    : tr('الرجل', 'Leg');
  return (
    <div
      className={gate.ok ? 'clip-status clip-ok' : 'clip-status clip-refused'}
      role="status"
    >
      <p>
        <strong>
          {gate.ok
            ? tr('التصوير مناسب', 'Camera view OK')
            : tr('لا أستطيع التقييم', 'Cannot assess')}
        </strong>{' '}
        — {gate.messageAr}
      </p>
      <p className="clip-facts">
        <span>
          {tr('اكتشاف الجسم', 'Body detected')}: {Math.round(clip.detectionRate * 100)}%
        </span>
        <span>
          {tr('زاوية التصوير', 'Camera angle')} (frontalness):{' '}
          {clip.view.frontalness === null ? '—' : clip.view.frontalness.toFixed(2)}{' '}
          {pack.view === 'side'
            ? tr(
                `(المقبول للتصوير الجانبي حتى ${clip.view.cutoff})`,
                `(side view accepted up to ${clip.view.cutoff})`,
              )
            : tr(
                `(المقبول للتصوير الأمامي من ${clip.view.cutoff})`,
                `(front view accepted from ${clip.view.cutoff})`,
              )}
        </span>
        <span>
          {limb} {tr('المتابَعة', 'tracked')}: {sideName(clip.side)}
        </span>
        <span>
          {tr('تكرارات وُجدت', 'Reps found')}: {clip.reps.length}
        </span>
      </p>
    </div>
  );
}

const PATIENT_KEY = 'qawam.patient';
const DEFAULT_PATIENT = 'مريض تجريبي'; // stored key, not shown translated

function readPatient(): string {
  try {
    return globalThis.localStorage?.getItem(PATIENT_KEY) || DEFAULT_PATIENT;
  } catch {
    return DEFAULT_PATIENT;
  }
}

function writePatient(value: string): void {
  try {
    globalThis.localStorage?.setItem(PATIENT_KEY, value);
  } catch {
    // optional convenience
  }
}

function Progress({ value }: { value: number }) {
  return (
    <p className="analysis-progress" role="status" aria-live="polite">
      {tr('جارٍ تحليل الفيديو على جهازك…', 'Analysing the video on your device…')}{' '}
      {Math.round(value * 100)}%
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
  const [patient, setPatient] = useState(readPatient);
  const [savedCount, setSavedCount] = useState(0);
  const savedHomes = useRef(new WeakSet<ClipAnalysis>());
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
      setError(tr('اختر ملف فيديو صالحًا.', 'Choose a valid video file.'));
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
          : tr(
              'تعذّر تحميل نموذج MediaPipe. تحقق من اتصال الإنترنت ثم أعد المحاولة.',
              'Could not load the MediaPipe model. Check the internet connection and try again.',
            ),
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
        return { error: tr('أدخل هامش السماح.', 'Enter the tolerance.') } as const;
      }
      return { tolerance, goniometer, reps } as const;
    } catch (cause) {
      return {
        error:
          cause instanceof Error
            ? cause.message
            : tr('قيمة غير صالحة.', 'Invalid value.'),
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

  const referenceRangeDeg =
    chosenRep && reference ? chosenRep.peakDeg - reference.baseDeg : 0;

  function store(mode: 'live' | 'file', reps: StoredRep[]) {
    if (!reference || 'error' in settings) {
      return;
    }
    saveSession({
      id: newSessionId(),
      patient: patient.trim() || DEFAULT_PATIENT,
      packId,
      packVersion: pack.version,
      engineVersion: COACH_ENGINE_VERSION,
      dateIso: new Date().toISOString(),
      mode,
      side: reference.side,
      toleranceDeg: settings.tolerance,
      referenceRangeDeg,
      goniometerDeg: settings.goniometer ?? null,
      reps,
    });
    setSavedCount((n) => n + 1);
  }

  // a home video analysed from a file is saved once, when its result first appears
  useEffect(() => {
    if (result?.status === 'ASSESSED' && home && !savedHomes.current.has(home)) {
      savedHomes.current.add(home);
      store(
        'file',
        repsFromFile(
          result.reps,
          home.reps.map((r) => r.peakDeg),
          referenceRangeDeg,
        ),
      );
    }
    // saving is keyed on the home clip; store reads the latest settings
  }, [result, home]);

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
    <>
      <section
        className="session-summary squat-demo"
        aria-labelledby="exercise-coach-title"
      >
        <div className="summary-heading">
          <div>
            <p className="summary-kicker">
              {tr('مدرب تمارين مباشر · تجريبي', 'Live exercise coach · prototype')}
            </p>
            <h2 id="exercise-coach-title">
              {tr(
                'تمرينك مقارنةً بتكرارك المرجعي',
                'Your exercise against your own reference rep',
              )}
            </h2>
          </div>
          <span className="simulation-badge">
            {tr('الفيديو لا يُرفع', 'Video is never uploaded')}
          </span>
        </div>
        <p>
          {tr(
            'يسجّل الأخصائي معك تكرارًا صحيحًا في العيادة، ثم يقارن التطبيق كل تكرار في البيت بهذا التكرار نفسه، وليس بقاعدة واحدة للجميع. إذا لم تكن زاوية التصوير مناسبة، يقول قوام إنه لا يراك جيدًا بدل أن يخمّن.',
            'Your physio records one correct rep with you in the clinic. At home, the app compares every rep with that same rep, not with one rule for everyone. If the camera angle is wrong, it says it cannot see you well instead of guessing.',
          )}
        </p>

        <div className="exercise-picker">
          <label className="pain-demo-label" htmlFor="patient-label">
            {tr(
              'المريض (اسم أو رمز، يُحفظ على هذا الجهاز فقط)',
              'Patient (name or code, saved on this device only)',
            )}
          </label>
          <input
            id="patient-label"
            type="text"
            value={patient}
            onChange={(event) => {
              setPatient(event.currentTarget.value);
              writePatient(event.currentTarget.value);
            }}
          />
          <label className="pain-demo-label" htmlFor="exercise-pack">
            {tr('التمرين', 'Exercise')}
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
                {tr(item.names.ar, item.names.en)}
              </option>
            ))}
          </select>
          <p className="field-help">
            {copy.setupAr}{' '}
            {pack.view === 'side'
              ? tr('(تصوير جانبي)', '(side view)')
              : tr('(تصوير أمامي)', '(front view)')}
          </p>
          {pack.sides !== 'both' && (
            <>
              <label className="pain-demo-label" htmlFor="exercise-side">
                {pack.packId.startsWith('upper-limb')
                  ? tr('الذراع التي تتمرن بها', 'Arm you exercise')
                  : tr('الرجل التي تتمرن بها', 'Leg you exercise')}
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
                <option value="auto">
                  {tr('تلقائي: التي تتحرك أكثر', 'Automatic: the one that moves most')}
                </option>
                <option value="left">{tr('اليسرى', 'Left')}</option>
                <option value="right">{tr('اليمنى', 'Right')}</option>
              </select>
            </>
          )}
        </div>

        <div className="cannot-assess-result" role="note">
          <strong>
            {tr(
              'تنبيه: نموذج بحثي غير معتمد سريريًا',
              'Note: research prototype, not clinically approved',
            )}
          </strong>
          <p>
            {tr(
              'حزم التمارين وحدودها تنتظر موافقة أخصائي علاج طبيعي. القيم الافتراضية هنا مأخوذة من دراسات وإرشادات منشورة (المصدر بجانب كل قيمة) ولم يراجعها أخصائي بعد. النتائج للتجربة فقط ولا تُستخدم لتغيير خطة العلاج.',
              'Exercise packs and their limits await a physiotherapist’s approval. Defaults here come from published studies and guidelines (source next to each value) and have not been reviewed by a physio yet. Results are for testing only and must not change a care plan.',
            )}
          </p>
          {pack.literatureGoals?.map((goal) => (
            <p key={goal.metric} className="field-help">
              {tr('هدف من دراسة منشورة لـ', 'Published goal for ')}
              {copy.measureAr}: {goal.value}°
              {goal.population ? ` (${goal.population})` : ''}.{' '}
              <LiteratureNote source={goal} />
            </p>
          ))}
          <details>
            <summary>
              {tr('ماذا يقيس التطبيق هنا؟', 'What does the app measure here?')}
            </summary>
            <ul>
              <li>
                {copy.measureAr}{' '}
                {tr(
                  'بالدرجات (زاوية ثنائية الأبعاد) من نقاط MediaPipe، للجهة',
                  'in degrees (a 2D angle) from MediaPipe points, for the side',
                )}{' '}
                {pack.sides === 'both'
                  ? tr('الأقرب للكاميرا', 'nearest the camera')
                  : tr('التي تتمرن بها', 'you exercise')}
                .
              </li>
              <li>
                {tr(
                  'يقبل التقييم فقط إذا كان التصوير',
                  'Reps are judged only when filmed',
                )}{' '}
                {pack.view === 'side'
                  ? tr(
                      'من الجنب (نسبة عرض الكتفين إلى طول الجذع لا تتجاوز 0.178)',
                      'from the side (shoulder width ÷ torso length at most 0.178)',
                    )
                  : tr(
                      'من الأمام (نسبة عرض الكتفين إلى طول الجذع 0.601 على الأقل)',
                      'from the front (shoulder width ÷ torso length at least 0.601)',
                    )}
                {tr(
                  '، وهي قيمة بحثية من بيانات REHAB24-6.',
                  ', a research value from REHAB24-6 data.',
                )}
              </li>
              <li>
                {tr(
                  'لكل تكرار: فرق المدى عن المرجع مقاسًا من وضع راحتك، ومتوسط فرق المسار بعد محاذاة الزمن (DTW).',
                  'For each rep: the range difference from the reference, measured from your resting pose, and the mean path difference after time alignment (DTW).',
                )}
              </li>
              <li>{copy.evidenceAr}</li>
            </ul>
          </details>
        </div>

        <div className="squat-step">
          <h3>
            {tr(
              '١. التكرار المرجعي — يُسجَّل مع الأخصائي في العيادة',
              '1. Reference rep — recorded with the physio in the clinic',
            )}
          </h3>
          <p className="field-help">
            {copy.setupAr}{' '}
            {tr(
              'أدِّ تكرارين صحيحين ببطء؛ يتوقف التسجيل بالكاميرا تلقائيًا بعدهما.',
              'Do two correct reps slowly; camera recording stops by itself after them.',
            )}
          </p>
          <SourcePicker
            value={referenceSource}
            onChange={setReferenceSource}
            label={tr('طريقة تسجيل المرجع', 'How to record the reference')}
          />
          {referenceSource === 'file' && (
            <>
              <label className="pain-demo-label" htmlFor="squat-reference-video">
                {tr('ملف فيديو المرجع', 'Reference video file')}
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
                {tr(
                  'سجّل مرجعًا جديدًا بالكاميرا',
                  'Record a new reference with the camera',
                )}
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
                {tr('التكرار المرجعي', 'Reference rep')}
              </label>
              <select
                id="squat-reference-rep"
                value={referenceRep}
                onChange={(event) => setReferenceRep(Number(event.currentTarget.value))}
              >
                {reference.reps.map((rep, index) => (
                  <option key={rep.start} value={index}>
                    {tr('تكرار', 'Rep')} {index + 1} — {tr('مدى الحركة', 'range')}{' '}
                    {formatDegrees(rep.peakDeg - reference.baseDeg)}
                  </option>
                ))}
              </select>
              <label className="pain-demo-label" htmlFor="squat-tolerance">
                {tr(
                  'هامش السماح بالدرجات (يحدده الأخصائي)',
                  'Tolerance in degrees (set by the physio)',
                )}
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
                {tr('القيمة الافتراضية', 'Default')} {TEST_DEFAULT_TOLERANCE_DEG}°:{' '}
                {tr(
                  'بهذا الفرق تقريبًا يستطيع التقدير بالعين أو الجونيوميتر القصير التمييز بين زاويتين، فلا ننبّه على فرق أصغر.',
                  'about the smallest gap that eye estimation or a short goniometer can tell apart, so smaller gaps are not cued.',
                )}{' '}
                <LiteratureNote source={sourceOf(DEMO_DEFAULTS.toleranceDeg.source)} />
              </p>
              <label className="pain-demo-label" htmlFor="exercise-reps">
                {tr(
                  'عدد التكرارات في البيت (يحدده الأخصائي)',
                  'Reps at home (set by the physio)',
                )}
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
                {tr('القيمة الافتراضية', 'Default')} {TEST_DEFAULT_HOME_REPS}{' '}
                {tr(
                  '(أقل المدى الموصى به للمبتدئين 8–12)؛ ينتهي التمرين بالكاميرا تلقائيًا عند بلوغها.',
                  '(low end of the 8–12 recommended for beginners); a camera session ends by itself when it is reached.',
                )}{' '}
                <LiteratureNote source={sourceOf(DEMO_DEFAULTS.homeReps.source)} />
              </p>
              <label className="pain-demo-label" htmlFor="squat-goniometer">
                {tr('قراءة الجونيوميتر لـ', 'Goniometer reading for ')}
                {copy.measureAr}
                {tr(
                  ' في التكرار المرجعي (اختياري)',
                  ' in the reference rep (optional)',
                )}
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
                {tr(
                  'إذا أدخلها الأخصائي، يعرض التطبيق الزاوية بالدرجات الحقيقية بعد تصحيح فرق الكاميرا.',
                  'If the physio enters it, the app shows the angle in true degrees after correcting for the camera.',
                )}
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
          <h3>{tr('٢. التمرين في البيت', '2. Exercise at home')}</h3>
          {!referenceReady && (
            <p className="field-help">
              {tr(
                'سجّل تكرارًا مرجعيًا مناسبًا أولًا.',
                'Record a suitable reference rep first.',
              )}
            </p>
          )}
          <SourcePicker
            value={homeSource}
            onChange={setHomeSource}
            label={tr('طريقة التمرين', 'How to exercise')}
          />
          {homeSource === 'camera' && referenceReady && !liveRangeOk && (
            <p className="pose-error" role="alert">
              {tr(
                'التكرار المرجعي المختار يكاد لا يحتوي على حركة. اختر تكرارًا آخر أو سجّل المرجع من جديد.',
                'The chosen reference rep has almost no movement. Pick another rep or record the reference again.',
              )}
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
                onSessionComplete={(reps) =>
                  store('live', repsFromLive(reps, referenceRangeDeg))
                }
              />
            )}
          {homeSource === 'file' && (
            <>
              <label className="pain-demo-label" htmlFor="squat-home-video">
                {tr('ملف فيديو التمرين', 'Exercise video file')}
              </label>
              <input
                id="squat-home-video"
                type="file"
                accept="video/*"
                disabled={!referenceReady || busy !== null}
                onChange={(event) =>
                  void analyse('home', event.currentTarget.files?.[0])
                }
              />
            </>
          )}
          {busy === 'home' && <Progress value={progress} />}
          {homeSource === 'file' && home && <ClipStatus clip={home} pack={pack} />}
          {homeSource === 'file' && result?.status === 'CANNOT_ASSESS' && (
            <div className="cannot-assess-result" role="status">
              <h3>{tr('لا أراك جيدًا', 'I cannot see you well')}</h3>
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
                  <span className="legend-reference">{tr('المرجع', 'Reference')}</span>
                  <span className="legend-rep">{tr('هذا التكرار', 'This rep')}</span>
                </p>
                <ol className="rep-feedback-list">
                  {result.reps.map((rep) => (
                    <li key={rep.index} className="rep-feedback" data-cue={rep.cue}>
                      <div>
                        <strong>
                          {tr('تكرار', 'Rep')} {rep.index + 1} (
                          {rep.startSeconds.toFixed(1)}–{rep.endSeconds.toFixed(1)}{' '}
                          {tr('ث', 's')})
                        </strong>
                        <p>{rep.messageAr}</p>
                        <p className="rep-numbers">
                          {tr('فرق المدى', 'Range diff')}{' '}
                          {formatDegrees(rep.comparison.depthDiffDeg, true)} ·{' '}
                          {tr('فرق المسار', 'path diff')}{' '}
                          {formatDegrees(rep.comparison.dtwMeanAbsDeg)}
                          {rep.calibratedPeakDeg !== null &&
                            tr(
                              ` · الزاوية المصححة ${formatDegrees(rep.calibratedPeakDeg)}`,
                              ` · corrected angle ${formatDegrees(rep.calibratedPeakDeg)}`,
                            )}
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
      <ProgressReport
        patient={patient.trim() || DEFAULT_PATIENT}
        packId={packId}
        refreshKey={savedCount}
      />
    </>
  );
}

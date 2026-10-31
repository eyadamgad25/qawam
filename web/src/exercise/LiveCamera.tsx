import { useEffect, useRef, useState } from 'react';
import { drawPoseOverlay } from '../LocalVideoPoseDemo';
import { packCopy, type ExercisePack } from './exercisePack';
import {
  arabicNumberWord,
  hasArabicVoice,
  LiveCoach,
  setupStatus,
  speakAr,
  summarise,
  type LiveReference,
  type LiveRepFeedback,
  type SessionSummary,
  type SetupStatus,
} from './liveCoach';
import type { PoseFrame } from './poseFrames';
import { analyseClip } from './session';
import { detectCurrentFrame, landmarkerDelegate, loadLandmarker } from './videoPose';

type Props =
  | {
      pack: ExercisePack;
      mode: 'reference';
      targetReps: number;
      onReference: (frames: PoseFrame[]) => void;
    }
  | {
      pack: ExercisePack;
      mode: 'home';
      reference: LiveReference;
      toleranceDeg: number;
      targetReps: number;
      /** called once when a home session ends, with every rep's feedback */
      onSessionComplete?: (reps: LiveRepFeedback[]) => void;
    };

/** Frames used for the live setup check (about one second). */
const SETUP_WINDOW = 20;
/** Longest live recording, same limit as uploaded videos. */
const MAX_RECORDING_SECONDS = 120;
/** Seconds of "ready" before the hands-free countdown starts. */
const READY_HOLD_SECONDS = 1.5;
const COUNTDOWN_SECONDS = 3;
/** Seconds between two spoken setup reminders. */
const SETUP_VOICE_GAP_SECONDS = 4;

export const SETUP_TITLE_AR: Readonly<Record<SetupStatus['state'], string>> = {
  NO_PERSON: 'لا أرى أحدًا',
  NOT_FULL_BODY: 'جسمك غير ظاهر كاملًا',
  WRONG_VIEW: 'غيّر زاوية الكاميرا',
  READY: 'جاهز',
};

export function signedDegrees(value: number): string {
  const rounded = Math.round(value);
  return `${rounded > 0 ? '+' : ''}${rounded}°`;
}

type Phase = 'idle' | 'countdown' | 'recording' | 'done';

export default function LiveCamera(props: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const phaseRef = useRef<Phase>('idle');
  const framesRef = useRef<PoseFrame[]>([]);
  const coachRef = useRef<LiveCoach | null>(null);
  const voiceRef = useRef(true);
  const autoRef = useRef(true);
  const propsRef = useRef(props);
  propsRef.current = props;
  const timersRef = useRef<number[]>([]);
  const referenceRepsRef = useRef(0);

  const [cameraOn, setCameraOn] = useState(false);
  const [starting, setStarting] = useState(false);
  const [facing, setFacing] = useState<'user' | 'environment'>('user');
  const [setup, setSetup] = useState<SetupStatus | null>(null);
  const [phase, setPhaseState] = useState<Phase>('idle');
  const [countdown, setCountdown] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [angle, setAngle] = useState<number | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [reps, setReps] = useState<LiveRepFeedback[]>([]);
  const [referenceReps, setReferenceReps] = useState(0);
  const [summary, setSummary] = useState<SessionSummary | null>(null);
  const [voice, setVoice] = useState(true);
  const [auto, setAuto] = useState(true);
  const [fps, setFps] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const copy = packCopy(props.pack);

  function setPhase(next: Phase) {
    phaseRef.current = next;
    setPhaseState(next);
  }

  function say(text: string, interrupt = true) {
    if (voiceRef.current) {
      speakAr(text, interrupt);
    }
  }

  useEffect(() => {
    if (!cameraOn) {
      return;
    }
    let cancelled = false;
    let frame = 0;
    let lastTime = -1;
    let tick = 0;
    const recent: PoseFrame[] = [];
    const startedAt = performance.now();
    let recordStart = 0;
    let readySince: number | null = null;
    let notReadySince: number | null = null;
    let lastState: SetupStatus['state'] | null = null;
    let lastSpokenAt = -Infinity;
    let fpsCount = 0;
    let fpsSince = performance.now();

    async function run() {
      try {
        const landmarker = await loadLandmarker();
        const { PoseLandmarker } = await import('@mediapipe/tasks-vision');
        const video = videoRef.current;
        const canvas = canvasRef.current;
        if (cancelled || !video || !canvas) {
          return;
        }
        const loop = () => {
          if (cancelled) {
            return;
          }
          if (
            video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA &&
            video.currentTime !== lastTime
          ) {
            lastTime = video.currentTime;
            if (
              canvas.width !== video.videoWidth ||
              canvas.height !== video.videoHeight
            ) {
              canvas.width = video.videoWidth;
              canvas.height = video.videoHeight;
            }
            const now = (performance.now() - startedAt) / 1000;
            const pose = detectCurrentFrame(landmarker, video, now);
            drawPoseOverlay(
              canvas,
              pose.landmarks ?? undefined,
              PoseLandmarker.POSE_CONNECTIONS,
            );
            fpsCount += 1;
            if (performance.now() - fpsSince >= 1000) {
              setFps(fpsCount);
              fpsCount = 0;
              fpsSince = performance.now();
            }
            recent.push(pose);
            if (recent.length > SETUP_WINDOW) {
              recent.shift();
            }
            tick += 1;
            const current = propsRef.current;
            const status = setupStatus(recent, current.pack);
            if (tick % 5 === 0) {
              setSetup(status);
            }
            const ready = status.state === 'READY';
            readySince = ready ? (readySince ?? now) : null;
            notReadySince = ready ? null : (notReadySince ?? now);
            const phaseNow = phaseRef.current;

            // spoken setup guidance, before and during the exercise
            if (
              tick % 5 === 0 &&
              status.state !== lastState &&
              now - lastSpokenAt >= SETUP_VOICE_GAP_SECONDS &&
              phaseNow !== 'countdown' &&
              (phaseNow !== 'recording' ||
                (notReadySince !== null && now - notReadySince > 2))
            ) {
              if (!(phaseNow === 'idle' && ready && autoRef.current)) {
                say(status.spokenAr);
              }
              lastState = status.state;
              lastSpokenAt = now;
            }

            // hands-free start
            if (
              phaseNow === 'idle' &&
              autoRef.current &&
              readySince !== null &&
              now - readySince >= READY_HOLD_SECONDS
            ) {
              beginCountdown();
            }

            if (phaseNow === 'recording') {
              if (framesRef.current.length === 0) {
                recordStart = pose.timeSeconds;
              }
              framesRef.current.push({
                ...pose,
                timeSeconds: pose.timeSeconds - recordStart,
              });
              const seconds = pose.timeSeconds - recordStart;
              if (tick % 10 === 0) {
                setElapsed(seconds);
              }
              const coach = coachRef.current;
              if (coach) {
                const update = coach.push(pose);
                if (tick % 2 === 0) {
                  setAngle(update.angleDeg);
                  setProgress(update.progress);
                }
                if (update.newRep) {
                  setReps([...coach.reps]);
                  say(update.newRep.spokenAr);
                  if (coach.reps.length >= current.targetReps) {
                    finish();
                  }
                }
              } else if (current.mode === 'reference' && tick % 15 === 0) {
                const clip = analyseClip(framesRef.current, current.pack);
                const found = clip.reps.filter(
                  (rep) => rep.end < clip.curve.length - 3,
                ).length;
                if (found !== referenceRepsRef.current) {
                  referenceRepsRef.current = found;
                  setReferenceReps(found);
                  if (found > 0) {
                    say(arabicNumberWord(found));
                  }
                }
                if (found >= current.targetReps) {
                  finish();
                }
              }
              if (seconds >= MAX_RECORDING_SECONDS) {
                finish();
              }
            }
          }
          frame = requestAnimationFrame(loop);
        };
        frame = requestAnimationFrame(loop);
      } catch (cause) {
        if (!cancelled) {
          setError(
            cause instanceof Error
              ? cause.message
              : 'تعذّر تحميل نموذج MediaPipe. تحقق من اتصال الإنترنت.',
          );
        }
      }
    }
    void run();
    return () => {
      cancelled = true;
      cancelAnimationFrame(frame);
    };
  }, [cameraOn]);

  useEffect(
    () => () => {
      timersRef.current.forEach((id) => window.clearTimeout(id));
      streamRef.current?.getTracks().forEach((track) => track.stop());
    },
    [],
  );

  async function startCamera() {
    setError(null);
    setStarting(true);
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error(
          'المتصفح لا يسمح بالكاميرا هنا. افتح الصفحة من localhost أو من رابط https.',
        );
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: facing, width: { ideal: 640 }, height: { ideal: 480 } },
        audio: false,
      });
      streamRef.current = stream;
      const video = videoRef.current;
      if (!video) {
        throw new Error('عنصر الفيديو غير متاح.');
      }
      video.srcObject = stream;
      await video.play();
      setPhase('idle');
      setSummary(null);
      setCameraOn(true);
      say(copy.setupAr);
    } catch (cause) {
      stopCamera();
      const denied = cause instanceof DOMException && cause.name === 'NotAllowedError';
      setError(
        denied
          ? 'لم يُسمح باستخدام الكاميرا. اسمح بها من إعدادات المتصفح ثم أعد المحاولة.'
          : cause instanceof Error
            ? cause.message
            : 'تعذّر تشغيل الكاميرا.',
      );
    } finally {
      setStarting(false);
    }
  }

  function clearTimers() {
    timersRef.current.forEach((id) => window.clearTimeout(id));
    timersRef.current = [];
  }

  function stopCamera() {
    clearTimers();
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    setCameraOn(false);
    setSetup(null);
    if (phaseRef.current !== 'done') {
      setPhase('idle');
    }
  }

  function beginCountdown() {
    if (phaseRef.current !== 'idle') {
      return;
    }
    setPhase('countdown');
    setCountdown(COUNTDOWN_SECONDS);
    say('جاهز. ثلاثة');
    for (let k = 1; k <= COUNTDOWN_SECONDS; k += 1) {
      const id = window.setTimeout(() => {
        const left = COUNTDOWN_SECONDS - k;
        setCountdown(left);
        if (left > 0) {
          say(arabicNumberWord(left));
        } else {
          startRecording();
        }
      }, k * 1000);
      timersRef.current.push(id);
    }
  }

  function startRecording() {
    framesRef.current = [];
    setReps([]);
    referenceRepsRef.current = 0;
    setReferenceReps(0);
    setSummary(null);
    setElapsed(0);
    setAngle(null);
    setProgress(null);
    const current = propsRef.current;
    coachRef.current =
      current.mode === 'home'
        ? new LiveCoach(current.pack, current.reference, current.toleranceDeg)
        : null;
    setPhase('recording');
    say('ابدأ');
  }

  function finish() {
    if (phaseRef.current !== 'recording') {
      return;
    }
    setPhase('done');
    const current = propsRef.current;
    if (current.mode === 'reference') {
      const frames = framesRef.current;
      say('تم تسجيل المرجع');
      stopCamera();
      current.onReference(frames);
      return;
    }
    const finished = [...(coachRef.current?.reps ?? [])];
    const result = summarise(finished, current.pack);
    setSummary(result);
    if (finished.length > 0) {
      current.onSessionComplete?.(finished);
    }
    window.setTimeout(() => say(result.spokenAr, false), 1200);
  }

  function again() {
    clearTimers();
    setSummary(null);
    setReps([]);
    setPhase('idle');
  }

  const ready = setup?.state === 'READY';
  const isHome = props.mode === 'home';
  const tolerance = isHome ? props.toleranceDeg : 0;
  const range = isHome ? coachRangeFor(props.reference) : 1;
  const band = isHome ? Math.min(0.5, tolerance / range) : 0;

  return (
    <div className="live-camera">
      <div className="live-controls">
        {!cameraOn ? (
          <>
            <label className="pain-demo-label" htmlFor={`live-facing-${props.mode}`}>
              الكاميرا
            </label>
            <select
              id={`live-facing-${props.mode}`}
              value={facing}
              onChange={(event) =>
                setFacing(
                  event.currentTarget.value === 'environment' ? 'environment' : 'user',
                )
              }
            >
              <option value="user">الأمامية (كاميرا اللابتوب أو السيلفي)</option>
              <option value="environment">الخلفية (الهاتف)</option>
            </select>
            <button
              className="demo-run-button"
              type="button"
              disabled={starting}
              onClick={() => void startCamera()}
            >
              {starting ? 'جارٍ تشغيل الكاميرا…' : 'شغّل الكاميرا'}
            </button>
          </>
        ) : (
          <button className="secondary-button" type="button" onClick={stopCamera}>
            أوقف الكاميرا
          </button>
        )}
        <label className="pain-model-toggle">
          <input
            type="checkbox"
            checked={voice}
            onChange={(event) => {
              voiceRef.current = event.currentTarget.checked;
              setVoice(event.currentTarget.checked);
            }}
          />
          <span>إرشاد صوتي</span>
        </label>
        <label className="pain-model-toggle">
          <input
            type="checkbox"
            checked={auto}
            onChange={(event) => {
              autoRef.current = event.currentTarget.checked;
              setAuto(event.currentTarget.checked);
            }}
          />
          <span>ابدأ تلقائيًا عندما أكون جاهزًا</span>
        </label>
      </div>
      {voice && cameraOn && !hasArabicVoice() && (
        <p className="field-help">
          لا يوجد صوت عربي مثبّت في المتصفح، فقد يكون النطق غير واضح. جرّب Chrome أو
          Edge.
        </p>
      )}

      <div className="pose-video-stage" hidden={!cameraOn}>
        <div
          className={
            facing === 'user' ? 'pose-video-frame mirrored' : 'pose-video-frame'
          }
        >
          <video ref={videoRef} playsInline muted />
          <canvas ref={canvasRef} aria-label="نقاط الوضعية المكتشفة" />
        </div>
        {setup && phase !== 'countdown' && (
          <div
            className="setup-banner"
            data-state={setup.state}
            role="status"
            aria-live="polite"
          >
            <strong>
              {phase === 'recording' && ready
                ? `تكرار ${(isHome ? reps.length : referenceReps) + 1}`
                : SETUP_TITLE_AR[setup.state]}
            </strong>
            <span>
              {phase === 'recording' && ready
                ? isHome
                  ? `${copy.measureAr}: ${angle === null ? '—' : `${Math.round(angle)}°`}`
                  : 'أدِّ الحركة ببطء كما يطلب الأخصائي.'
                : setup.messageAr}
            </span>
          </div>
        )}
        {phase === 'countdown' && (
          <div className="countdown" aria-live="assertive">
            {countdown > 0 ? countdown : 'ابدأ'}
          </div>
        )}
        {isHome && phase === 'recording' && (
          <div
            className="range-meter"
            role="meter"
            aria-label={`${copy.measureAr} مقارنةً بالمرجع`}
            aria-valuemin={0}
            aria-valuemax={150}
            aria-valuenow={Math.round((progress ?? 0) * 100)}
          >
            <div
              className="range-band"
              style={{ bottom: `${(1 - band) * 66}%`, height: `${2 * band * 66}%` }}
            />
            <div className="range-target" style={{ bottom: '66%' }} />
            <div
              className="range-fill"
              style={{ height: `${Math.max(0, Math.min(1.5, progress ?? 0)) * 66}%` }}
            />
            <span className="range-label">المرجع</span>
          </div>
        )}
      </div>

      {cameraOn && (
        <div className="live-actions">
          {phase === 'idle' && (
            <button
              className="demo-run-button"
              type="button"
              disabled={!ready}
              onClick={beginCountdown}
            >
              {props.mode === 'reference' ? 'ابدأ تسجيل المرجع' : 'ابدأ التمرين'}
            </button>
          )}
          {(phase === 'recording' || phase === 'countdown') && (
            <button className="demo-run-button stop" type="button" onClick={finish}>
              {props.mode === 'reference' ? 'أنهِ التسجيل' : 'أنهِ التمرين'}
            </button>
          )}
          {phase === 'idle' && !ready && (
            <span className="field-help">
              {auto
                ? 'سيبدأ العد تلقائيًا عندما تظهر «جاهز».'
                : 'يُفعَّل الزر عندما يقول قوام «جاهز».'}
            </span>
          )}
          {phase === 'recording' && (
            <span className="live-meter" aria-live="off">
              {Math.floor(elapsed)} ث · {isHome ? reps.length : referenceReps} /{' '}
              {props.targetReps} تكرارات
            </span>
          )}
        </div>
      )}

      {isHome && summary && (
        <div className="session-summary-card" role="status">
          <h3>ملخص التمرين</h3>
          <p>{summary.textAr}</p>
          <div className="summary-metrics">
            <div className="summary-metric">
              <span className="metric-value" dir="ltr">
                {summary.reps}
              </span>
              <span>تكرارات</span>
            </div>
            <div className="summary-metric">
              <span className="metric-value" dir="ltr">
                {summary.matches}
              </span>
              <span>قريبة من المرجع</span>
            </div>
            <div className="summary-metric">
              <span className="metric-value" dir="ltr">
                {summary.meanRangeDiffDeg === null
                  ? '—'
                  : signedDegrees(summary.meanRangeDiffDeg)}
              </span>
              <span>متوسط الفرق عن المرجع</span>
            </div>
          </div>
          <button className="secondary-button" type="button" onClick={again}>
            جولة جديدة
          </button>
        </div>
      )}

      {isHome && reps.length > 0 && (
        <ol className="rep-feedback-list">
          {reps
            .slice()
            .reverse()
            .map((rep) => (
              <li
                key={rep.index}
                className="rep-feedback live"
                data-cue={rep.assessed ? rep.cue : 'NOT_ASSESSED'}
              >
                <div>
                  <strong>تكرار {rep.index + 1}</strong>
                  <p>{rep.messageAr}</p>
                  {rep.assessed && rep.tempoNoteAr && <p>{rep.tempoNoteAr}</p>}
                  {rep.assessed && (
                    <p className="rep-numbers">
                      فرق المدى {signedDegrees(rep.comparison.depthDiffDeg)} · فرق
                      المسار {Math.round(rep.comparison.dtwMeanAbsDeg)}°
                    </p>
                  )}
                </div>
              </li>
            ))}
        </ol>
      )}

      {cameraOn && (
        <details className="live-diagnostics">
          <summary>تفاصيل تقنية (للتجربة)</summary>
          <p dir="ltr">
            {fps} fps · {landmarkerDelegate ?? '—'} · state {setup?.state ?? '—'} ·
            frontalness {setup?.frontalness?.toFixed(2) ?? '—'} · missing{' '}
            {setup?.missingParts.join(',') || '—'} · angle{' '}
            {angle === null ? '—' : angle.toFixed(0)} · progress{' '}
            {progress === null ? '—' : progress.toFixed(2)}
          </p>
          <p className="field-help">
            إذا كانت السرعة أقل من 10 fps فقد تتأخر الهيكلة؛ أغلق البرامج الأخرى أو حسّن
            الإضاءة.
          </p>
        </details>
      )}
      {error && (
        <p className="pose-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

function coachRangeFor(reference: LiveReference): number {
  return Math.max(10, Math.max(...reference.curve) - reference.baseDeg);
}

import { useEffect, useRef, useState } from 'react';
import { drawPoseOverlay } from '../LocalVideoPoseDemo';
import { SQUAT_PACK } from './exercisePack';
import {
  LiveSquatCoach,
  setupStatus,
  speakAr,
  spokenText,
  type LiveRepFeedback,
  type SetupStatus,
} from './liveCoach';
import type { PoseFrame } from './poseFrames';
import { detectCurrentFrame, loadLandmarker } from './videoPose';

type Props =
  | { mode: 'reference'; onReference: (frames: PoseFrame[]) => void }
  | { mode: 'home'; referenceCurve: readonly number[]; toleranceDeg: number };

/** Frames used for the live setup check (about one second). */
const SETUP_WINDOW = 20;
/** Longest live recording, same limit as uploaded videos. */
const MAX_RECORDING_SECONDS = 120;

export function signedDegrees(value: number): string {
  const rounded = Math.round(value);
  return `${rounded > 0 ? '+' : ''}${rounded}°`;
}

export const SETUP_TITLE_AR: Readonly<Record<SetupStatus['state'], string>> = {
  NO_PERSON: 'لا أرى أحدًا',
  NOT_FULL_BODY: 'جسمك غير ظاهر كاملًا',
  WRONG_VIEW: 'غيّر زاوية الهاتف',
  READY: 'جاهز',
};

export default function LiveCamera(props: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const recordingRef = useRef(false);
  const framesRef = useRef<PoseFrame[]>([]);
  const coachRef = useRef<LiveSquatCoach | null>(null);
  const voiceRef = useRef(true);
  const propsRef = useRef(props);
  propsRef.current = props;

  const [cameraOn, setCameraOn] = useState(false);
  const [starting, setStarting] = useState(false);
  const [facing, setFacing] = useState<'user' | 'environment'>('user');
  const [setup, setSetup] = useState<SetupStatus | null>(null);
  const [recording, setRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [angle, setAngle] = useState<number | null>(null);
  const [reps, setReps] = useState<LiveRepFeedback[]>([]);
  const [voice, setVoice] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
            const pose = detectCurrentFrame(
              landmarker,
              video,
              (performance.now() - startedAt) / 1000,
            );
            drawPoseOverlay(
              canvas,
              pose.landmarks ?? undefined,
              PoseLandmarker.POSE_CONNECTIONS,
            );
            recent.push(pose);
            if (recent.length > SETUP_WINDOW) {
              recent.shift();
            }
            tick += 1;
            if (tick % 5 === 0) {
              setSetup(setupStatus(recent, SQUAT_PACK));
            }
            if (recordingRef.current) {
              if (framesRef.current.length === 0) {
                recordStart = pose.timeSeconds;
              }
              framesRef.current.push({
                ...pose,
                timeSeconds: pose.timeSeconds - recordStart,
              });
              const coach = coachRef.current;
              if (coach) {
                const update = coach.push(pose);
                if (tick % 3 === 0) {
                  setAngle(update.angleDeg);
                }
                if (update.newRep) {
                  setReps([...coach.reps]);
                  if (voiceRef.current) {
                    speakAr(spokenText(update.newRep));
                  }
                }
              }
              const seconds = pose.timeSeconds - recordStart;
              if (tick % 10 === 0) {
                setElapsed(seconds);
              }
              if (seconds >= MAX_RECORDING_SECONDS) {
                stopRecording();
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

  useEffect(() => () => stopCamera(), []);

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
        video: { facingMode: facing, width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      streamRef.current = stream;
      const video = videoRef.current;
      if (!video) {
        throw new Error('عنصر الفيديو غير متاح.');
      }
      video.srcObject = stream;
      await video.play();
      setCameraOn(true);
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

  function stopCamera() {
    recordingRef.current = false;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    setCameraOn(false);
    setRecording(false);
    setSetup(null);
  }

  function startRecording() {
    framesRef.current = [];
    setReps([]);
    setElapsed(0);
    setAngle(null);
    const current = propsRef.current;
    coachRef.current =
      current.mode === 'home'
        ? new LiveSquatCoach(
            SQUAT_PACK,
            { curve: current.referenceCurve },
            current.toleranceDeg,
          )
        : null;
    recordingRef.current = true;
    setRecording(true);
    if (voiceRef.current) {
      speakAr('ابدأ');
    }
  }

  function stopRecording() {
    recordingRef.current = false;
    setRecording(false);
    const current = propsRef.current;
    if (current.mode === 'reference') {
      const frames = framesRef.current;
      stopCamera();
      current.onReference(frames);
    }
  }

  const ready = setup?.state === 'READY';
  const assessed = reps.filter((rep) => rep.assessed);
  const close = assessed.filter(
    (rep) => rep.assessed && rep.cue === 'MATCHES_REFERENCE',
  );

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
      </div>

      <div className="pose-video-stage" hidden={!cameraOn}>
        <div
          className={
            facing === 'user' ? 'pose-video-frame mirrored' : 'pose-video-frame'
          }
        >
          <video ref={videoRef} playsInline muted />
          <canvas ref={canvasRef} aria-label="نقاط الوضعية المكتشفة" />
        </div>
        {setup && (
          <div
            className="setup-banner"
            data-state={setup.state}
            role="status"
            aria-live="polite"
          >
            <strong>{SETUP_TITLE_AR[setup.state]}</strong>
            <span>{setup.messageAr}</span>
          </div>
        )}
      </div>

      {cameraOn && (
        <div className="live-actions">
          {!recording ? (
            <button
              className="demo-run-button"
              type="button"
              disabled={!ready}
              onClick={startRecording}
            >
              {props.mode === 'reference' ? 'ابدأ تسجيل المرجع' : 'ابدأ التمرين'}
            </button>
          ) : (
            <button
              className="demo-run-button stop"
              type="button"
              onClick={stopRecording}
            >
              {props.mode === 'reference' ? 'أنهِ التسجيل' : 'أنهِ التمرين'}
            </button>
          )}
          {!ready && !recording && (
            <span className="field-help">يُفعَّل الزر عندما يقول قوام «جاهز».</span>
          )}
          {recording && (
            <span className="live-meter" aria-live="off">
              {Math.floor(elapsed)} ث
              {props.mode === 'home' &&
                ` · زاوية الركبة ${angle === null ? '—' : `${Math.round(angle)}°`}`}
            </span>
          )}
        </div>
      )}

      {props.mode === 'home' && reps.length > 0 && (
        <div className="pose-session-result" role="status" aria-live="polite">
          <h3>
            {close.length} من {reps.length} تكرارات قريبة من المرجع
            {assessed.length < reps.length &&
              ` · ${reps.length - assessed.length} لم تُقيَّم`}
          </h3>
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
                    {rep.assessed && (
                      <p className="rep-numbers">
                        فرق العمق {signedDegrees(rep.comparison.depthDiffDeg)} · فرق
                        المسار {Math.round(rep.comparison.dtwMeanAbsDeg)}°
                      </p>
                    )}
                  </div>
                </li>
              ))}
          </ol>
        </div>
      )}
      {error && (
        <p className="pose-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

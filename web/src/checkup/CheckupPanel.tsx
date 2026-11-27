/**
 * Check-up tests at home: five-times sit-to-stand, 30-second sit-to-stand, Timed Up and Go.
 * Spec: docs/superpowers/specs/2026-11-26-checkup-test-mode-design.md. Body points stay in memory during the test,
 * the result is computed when it ends (checkupTiming.ts), then the points are dropped. The face is pixelated on screen.
 */
import { useEffect, useRef, useState } from 'react';
import { drawPoseOverlay } from '../LocalVideoPoseDemo';
import { tr } from '../i18n';
import { speakAr, spokenNumber } from '../exercise/liveCoach';
import type { PoseFrame } from '../exercise/poseFrames';
import { detectCurrentFrame, loadLandmarker } from '../exercise/videoPose';
import {
  analyseCheckup,
  heightSignal,
  type CheckupKind,
  type CheckupResult,
  type NoResultReason,
} from './checkupTiming';
import {
  CHECKUP_ENGINE_VERSION,
  checkupsFor,
  deleteCheckups,
  saveCheckup,
  type StoredCheckup,
} from './checkupStore';
import { blurFace } from './faceBlur';
import { checkupBundle } from './fhir';

/** Set to true for a test only after its validation in docs/experiments.md passes the spec's rule. */
export const VALIDATED: Readonly<Record<CheckupKind, boolean>> = {
  sts5: false,
  sts30: false,
  tug: false,
};

/** Published at-risk cut-offs, shown to the physio for reference only (KINECAL: five-times > 16.7 s, TUG > 14 s). */
export const CUTOFF: Readonly<Partial<Record<CheckupKind, number>>> = {
  sts5: 16.7,
  tug: 14,
};

const READY_HOLD_SECONDS = 1.5;
const COUNTDOWN_SECONDS = 3;
const MAX_SECONDS: Readonly<Record<CheckupKind, number>> = {
  sts5: 60,
  sts30: 31,
  tug: 60,
};
const SETUP_WINDOW = 20;

export const TEST_COPY: Readonly<
  Record<
    CheckupKind,
    { titleAr: string; titleEn: string; stepsAr: string; stepsEn: string; goAr: string }
  >
> = {
  sts5: {
    titleAr: 'الجلوس والوقوف خمس مرات',
    titleEn: 'Five-times sit-to-stand',
    stepsAr:
      'اجلس على كرسي ثابت بلا مساند، وذراعاك متقاطعتان على صدرك. ضع الهاتف على جانبك على بعد ٣ أمتار تقريبًا. عند كلمة «ابدأ» قف تمامًا ثم اجلس، خمس مرات، بأسرع ما تستطيع بأمان.',
    stepsEn:
      'Sit on a firm chair without armrests, arms crossed on your chest. Put the phone to your side, about 3 m away. At "go", stand up fully and sit down five times, as fast as you safely can.',
    goAr: 'قف واجلس خمس مرات',
  },
  sts30: {
    titleAr: 'الجلوس والوقوف في ٣٠ ثانية',
    titleEn: '30-second sit-to-stand',
    stepsAr:
      'نفس وضع الجلوس. ضع الهاتف على جانبك. عند كلمة «ابدأ» قف تمامًا واجلس أكبر عدد ممكن من المرات خلال ٣٠ ثانية.',
    stepsEn:
      'Same seated position, phone to your side. At "go", stand up fully and sit down as many times as you can in 30 seconds.',
    goAr: 'قف واجلس حتى أقول توقف',
  },
  tug: {
    titleAr: 'اختبار القيام والمشي',
    titleEn: 'Timed Up and Go',
    stepsAr:
      'ضع علامة على الأرض على بعد ٣ أمتار من الكرسي. ضع الهاتف بعيدًا على الجانب ليرى الكرسي والعلامة. عند كلمة «ابدأ» قف وامشِ بخطوتك المعتادة حتى العلامة، استدر، ارجع واجلس. يُفضّل وجود شخص بجانبك.',
    stepsEn:
      'Mark the floor 3 m from the chair. Place the phone far to the side so it sees the chair and the mark. At "go", stand, walk at your usual pace to the mark, turn, walk back and sit down. Have someone nearby.',
    goAr: 'قم وامشِ حتى العلامة وارجع',
  },
};

export const REASON_COPY: Readonly<Record<NoResultReason, [string, string]>> = {
  'person-missing': [
    'لم أرَ وركك وركبتك وكاحلك معظم الوقت. ابتعد قليلًا وأعد المحاولة.',
    'I could not see your hip, knee and ankle most of the time. Step back and try again.',
  ],
  'no-movement': [
    'لم أرَ حركة وقوف وجلوس.',
    'I did not see you stand up and sit down.',
  ],
  'too-few-stands': [
    'لم أعدّ عدد الوقفات المطلوب.',
    'I did not count enough stand-ups.',
  ],
  'not-seated': ['لم أرَك تجلس في النهاية.', 'I did not see you sit down at the end.'],
  'no-walk': [
    'لم أرَك تمشي حتى العلامة وترجع.',
    'I did not see you walk to the mark and back.',
  ],
};

const PATIENT_KEY = 'qawam.patient';
function readPatient(): string {
  try {
    return globalThis.localStorage?.getItem(PATIENT_KEY) || 'مريض تجريبي';
  } catch {
    return 'مريض تجريبي';
  }
}

type Phase = 'idle' | 'countdown' | 'testing' | 'done';

export function resultText(result: CheckupResult): string {
  if (!result.ok) {
    const [ar, en] = REASON_COPY[result.reason];
    return tr(`لا توجد نتيجة: ${ar} أعد الاختبار.`, `No result: ${en} Please repeat.`);
  }
  if (result.kind === 'sts30') {
    return tr(
      `${result.count} وقفات في ٣٠ ثانية`,
      `${result.count} stand-ups in 30 seconds`,
    );
  }
  return tr(
    `${result.seconds!.toFixed(1)} ثانية`,
    `${result.seconds!.toFixed(1)} seconds`,
  );
}

export default function CheckupPanel() {
  const [kind, setKind] = useState<CheckupKind>('sts5');
  const [patient] = useState(readPatient);
  const [refresh, setRefresh] = useState(0);
  const copy = TEST_COPY[kind];
  void refresh;
  const history = checkupsFor(patient);

  function downloadFhir() {
    const bundle = checkupBundle(history, VALIDATED);
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(bundle, null, 2)], { type: 'application/fhir+json' }),
    );
    const link = document.createElement('a');
    link.href = url;
    link.download = 'checkup-fhir-bundle.json';
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="session-summary" aria-labelledby="checkup-title">
      <div className="summary-heading">
        <h2 id="checkup-title">{tr('اختبارات الفحص الدوري', 'Check-up tests')}</h2>
      </div>
      <p className="field-help">
        {tr(
          'اختبارات قصيرة يستخدمها أخصائيو العلاج الطبيعي لقياس قوة الساقين والتوازن. تقيس الكاميرا الوقت أو العدد، وتُحفظ الأرقام فقط: لا فيديو ولا صور، ووجهك مخفي على الشاشة. النتيجة ليست تشخيصًا. توقف فورًا إذا شعرت بدوخة أو ألم في الصدر.',
          'Short tests physiotherapists use to measure leg strength and balance. The camera measures the time or count, and only the numbers are kept: no video or images, and your face is hidden on screen. The result is not a diagnosis. Stop at once if you feel dizzy or have chest pain.',
        )}
      </p>
      <div
        className="checkup-choices"
        role="radiogroup"
        aria-label={tr('اختر الاختبار', 'Choose the test')}
      >
        {(Object.keys(TEST_COPY) as CheckupKind[]).map((option) => (
          <button
            key={option}
            type="button"
            role="radio"
            aria-checked={kind === option}
            className={kind === option ? 'demo-run-button' : 'secondary-button'}
            onClick={() => setKind(option)}
          >
            {tr(TEST_COPY[option].titleAr, TEST_COPY[option].titleEn)}
          </button>
        ))}
      </div>
      <h3>{tr(copy.titleAr, copy.titleEn)}</h3>
      <p>{tr(copy.stepsAr, copy.stepsEn)}</p>
      {!VALIDATED[kind] && (
        <p className="field-help" role="note">
          {tr(
            'هذا الاختبار لم يُتحقق من دقته بعد: النتيجة للتجربة فقط.',
            'This test has not been validated yet: the result is for practice only.',
          )}
        </p>
      )}
      <CheckupCamera
        key={kind}
        kind={kind}
        onResult={(result) => {
          if (result.ok) {
            saveCheckup({
              id: `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`,
              patient,
              kind: result.kind,
              dateIso: new Date().toISOString(),
              ...(result.count !== undefined ? { count: result.count } : {}),
              ...(result.seconds !== undefined ? { seconds: result.seconds } : {}),
              engine: CHECKUP_ENGINE_VERSION,
            });
            setRefresh((n) => n + 1);
          }
        }}
      />
      <CheckupHistory items={history} />
      <div className="live-controls">
        <button
          type="button"
          className="secondary-button"
          disabled={history.length === 0}
          onClick={downloadFhir}
        >
          {tr(
            'تنزيل النتائج بصيغة FHIR للأخصائي',
            'Download results as FHIR for the physio',
          )}
        </button>
        <button
          type="button"
          className="secondary-button"
          disabled={history.length === 0}
          onClick={() => {
            deleteCheckups(patient);
            setRefresh((n) => n + 1);
          }}
        >
          {tr(
            'احذف نتائج الفحص من هذا الجهاز',
            'Delete check-up results from this device',
          )}
        </button>
      </div>
    </section>
  );
}

function CheckupHistory({ items }: { items: readonly StoredCheckup[] }) {
  if (items.length === 0) {
    return (
      <p className="field-help">
        {tr('لا توجد نتائج محفوظة بعد.', 'No saved results yet.')}
      </p>
    );
  }
  return (
    <table className="report-table">
      <caption>
        {tr('النتائج السابقة (للأخصائي)', 'Earlier results (for the physio)')}
      </caption>
      <thead>
        <tr>
          <th scope="col">{tr('التاريخ', 'Date')}</th>
          <th scope="col">{tr('الاختبار', 'Test')}</th>
          <th scope="col">{tr('النتيجة', 'Result')}</th>
          <th scope="col">{tr('حدّ الخطر المنشور', 'Published at-risk cut-off')}</th>
        </tr>
      </thead>
      <tbody>
        {[...items].reverse().map((item) => (
          <tr key={item.id}>
            <td>{new Date(item.dateIso).toLocaleDateString()}</td>
            <td>{tr(TEST_COPY[item.kind].titleAr, TEST_COPY[item.kind].titleEn)}</td>
            <td>
              {item.kind === 'sts30'
                ? `${item.count}`
                : `${item.seconds?.toFixed(1)} ${tr('ث', 's')}`}
              {!VALIDATED[item.kind] && ` (${tr('غير متحقق منه', 'not validated')})`}
            </td>
            <td>
              {CUTOFF[item.kind] ? `> ${CUTOFF[item.kind]} ${tr('ث', 's')}` : '—'}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function CheckupCamera({
  kind,
  onResult,
}: {
  kind: CheckupKind;
  onResult: (result: CheckupResult) => void;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const phaseRef = useRef<Phase>('idle');
  const framesRef = useRef<PoseFrame[]>([]);
  const timersRef = useRef<number[]>([]);
  const onResultRef = useRef(onResult);
  onResultRef.current = onResult;

  const [cameraOn, setCameraOn] = useState(false);
  const [facing, setFacing] = useState<'user' | 'environment'>('environment');
  const [ready, setReady] = useState(false);
  const [phase, setPhaseState] = useState<Phase>('idle');
  const [countdown, setCountdown] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [count, setCount] = useState(0);
  const [result, setResult] = useState<CheckupResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  function setPhase(next: Phase) {
    phaseRef.current = next;
    setPhaseState(next);
  }

  useEffect(() => {
    if (!cameraOn) {
      return;
    }
    let cancelled = false;
    let raf = 0;
    let lastTime = -1;
    let tick = 0;
    let goAt = 0;
    let readySince: number | null = null;
    let spokenCount = 0;
    const recent: PoseFrame[] = [];
    const startedAt = performance.now();

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
            blurFace(canvas, video, pose.landmarks);
            tick += 1;
            recent.push(pose);
            if (recent.length > SETUP_WINDOW) {
              recent.shift();
            }
            const seen = heightSignal(recent).height.filter((h) => h !== null).length;
            const isReady = seen >= SETUP_WINDOW * 0.7;
            if (tick % 5 === 0) {
              setReady(isReady);
            }
            readySince = isReady ? (readySince ?? now) : null;
            if (
              phaseRef.current === 'idle' &&
              readySince !== null &&
              now - readySince >= READY_HOLD_SECONDS
            ) {
              beginCountdown();
            }
            if (phaseRef.current === 'testing') {
              if (framesRef.current.length === 0) {
                goAt = pose.timeSeconds;
              }
              framesRef.current.push({ ...pose, timeSeconds: pose.timeSeconds - goAt });
              const seconds = pose.timeSeconds - goAt;
              if (tick % 10 === 0) {
                setElapsed(seconds);
              }
              if (tick % 15 === 0) {
                const live = analyseCheckup(kind, framesRef.current);
                const stands = analyseCheckup('sts30', framesRef.current);
                const n = stands.ok ? stands.standUps.length : 0;
                if (kind !== 'tug' && n > spokenCount) {
                  spokenCount = n;
                  setCount(n);
                  speakAr(spokenNumber(n));
                }
                if ((kind === 'sts5' || kind === 'tug') && live.ok) {
                  finish();
                }
              }
              if (seconds >= MAX_SECONDS[kind]) {
                finish();
              }
            }
          }
          raf = requestAnimationFrame(loop);
        };
        raf = requestAnimationFrame(loop);
      } catch (cause) {
        if (!cancelled) {
          setError(
            cause instanceof Error
              ? cause.message
              : tr('تعذّر تحميل نموذج الوضعية.', 'Could not load the pose model.'),
          );
        }
      }
    }
    void run();
    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
    };
  }, [cameraOn, kind]);

  useEffect(
    () => () => {
      timersRef.current.forEach((id) => window.clearTimeout(id));
      streamRef.current?.getTracks().forEach((track) => track.stop());
    },
    [],
  );

  async function startCamera() {
    setError(null);
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error(
          tr(
            'المتصفح لا يسمح بالكاميرا هنا. افتح الصفحة من رابط https.',
            'This browser blocks the camera here. Open the page on an https link.',
          ),
        );
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: facing, width: { ideal: 640 }, height: { ideal: 480 } },
        audio: false,
      });
      streamRef.current = stream;
      const video = videoRef.current;
      if (!video) {
        throw new Error(tr('عنصر الفيديو غير متاح.', 'Video element not available.'));
      }
      video.srcObject = stream;
      await video.play();
      setPhase('idle');
      setResult(null);
      setCameraOn(true);
      speakAr(
        tr(
          'اجلس على الكرسي وأنت على جانب الكاميرا',
          'Sit on the chair, side-on to the camera',
        ),
      );
    } catch (cause) {
      stopCamera();
      setError(
        cause instanceof Error
          ? cause.message
          : tr('تعذّر تشغيل الكاميرا.', 'Could not start the camera.'),
      );
    }
  }

  function stopCamera() {
    timersRef.current.forEach((id) => window.clearTimeout(id));
    timersRef.current = [];
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    setCameraOn(false);
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
    speakAr(tr('جاهز. ثلاثة', 'Ready. Three'));
    for (let k = 1; k <= COUNTDOWN_SECONDS; k += 1) {
      const id = window.setTimeout(() => {
        const left = COUNTDOWN_SECONDS - k;
        setCountdown(left);
        if (left > 0) {
          speakAr(spokenNumber(left));
        } else {
          framesRef.current = [];
          setCount(0);
          setElapsed(0);
          setPhase('testing');
          speakAr(tr(`ابدأ. ${TEST_COPY[kind].goAr}`, 'Go'));
        }
      }, k * 1000);
      timersRef.current.push(id);
    }
  }

  function finish() {
    if (phaseRef.current !== 'testing') {
      return;
    }
    setPhase('done');
    const outcome = analyseCheckup(kind, framesRef.current);
    framesRef.current = []; // body points are not kept after the result
    setResult(outcome);
    onResultRef.current(outcome);
    speakAr(kind === 'sts30' ? tr('توقف', 'Stop') : tr('انتهى', 'Done'));
    window.setTimeout(() => speakAr(resultText(outcome), false), 900);
  }

  return (
    <div className="live-camera">
      <div className="live-controls">
        {!cameraOn ? (
          <>
            <label className="pain-demo-label" htmlFor="checkup-facing">
              {tr('الكاميرا', 'Camera')}
            </label>
            <select
              id="checkup-facing"
              value={facing}
              onChange={(event) =>
                setFacing(event.currentTarget.value === 'user' ? 'user' : 'environment')
              }
            >
              <option value="environment">
                {tr('الخلفية (الهاتف)', 'Back (phone)')}
              </option>
              <option value="user">{tr('الأمامية', 'Front')}</option>
            </select>
            <button
              className="demo-run-button"
              type="button"
              onClick={() => void startCamera()}
            >
              {tr('شغّل الكاميرا وابدأ', 'Start camera and begin')}
            </button>
          </>
        ) : (
          <button className="secondary-button" type="button" onClick={stopCamera}>
            {tr('أوقف الكاميرا', 'Stop camera')}
          </button>
        )}
      </div>
      {error && (
        <p className="field-help" role="alert">
          {error}
        </p>
      )}
      <div className="pose-video-stage" hidden={!cameraOn}>
        <div
          className={
            facing === 'user' ? 'pose-video-frame mirrored' : 'pose-video-frame'
          }
        >
          <video ref={videoRef} playsInline muted />
          <canvas
            ref={canvasRef}
            aria-label={tr('نقاط الوضعية، والوجه مخفي', 'Pose points, face hidden')}
          />
        </div>
        {phase === 'countdown' ? (
          <div className="countdown" aria-live="assertive">
            {countdown > 0 ? countdown : tr('ابدأ', 'Go')}
          </div>
        ) : (
          <div
            className="setup-banner"
            data-state={ready ? 'READY' : 'NOT_FULL_BODY'}
            role="status"
            aria-live="polite"
          >
            <strong>
              {phase === 'testing'
                ? kind === 'tug'
                  ? `${elapsed.toFixed(0)} ${tr('ث', 's')}`
                  : tr(`${count} وقفات`, `${count} stand-ups`)
                : ready
                  ? tr('جاهز', 'Ready')
                  : tr('لا أرى ساقك كاملة', 'I cannot see your whole leg')}
            </strong>
            <span>
              {phase === 'testing'
                ? `${elapsed.toFixed(0)} ${tr('ث', 's')}`
                : ready
                  ? tr(
                      'ابقَ جالسًا، سنبدأ بعد العدّ',
                      'Stay seated; we start after the count',
                    )
                  : tr(
                      'ابتعد قليلًا واجعل جانبك للكاميرا',
                      'Step back and turn your side to the camera',
                    )}
            </span>
          </div>
        )}
      </div>
      {result && (
        <div className="checkup-result" role="status">
          <strong>{resultText(result)}</strong>
          <button
            type="button"
            className="secondary-button"
            onClick={() => {
              setResult(null);
              setPhase('idle');
            }}
          >
            {tr('أعد الاختبار', 'Repeat the test')}
          </button>
        </div>
      )}
    </div>
  );
}

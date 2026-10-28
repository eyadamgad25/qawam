import { useEffect, useRef, useState } from 'react';
import {
  advanceArmRaiseCounter,
  ARM_RAISE_DEMO,
  INITIAL_ARM_RAISE_STATE,
  type ArmRaiseSideSelection,
  type ArmRaiseCounterState,
} from './armRaiseCounter';

const MAX_VIDEO_SECONDS = 120;
const WASM_URL = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.1.1/wasm';
const MODEL_URL =
  'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task';

type PosePoint = {
  x: number;
  y: number;
  visibility?: number;
};

type PoseConnection = {
  start: number;
  end: number;
};

export interface LocalVideoSummary {
  detectedRepetitions: number;
  durationSeconds: number;
  manualReferenceRepetitions: number | null;
}

export function parseManualRepCount(value: string): number | null {
  if (!value.trim()) {
    return null;
  }
  const repetitions = Number(value);
  if (!Number.isSafeInteger(repetitions) || repetitions < 0) {
    throw new Error('أدخل عددًا صحيحًا غير سالب للتكرارات اليدوية.');
  }
  return repetitions;
}

export function formatClipDuration(durationSeconds: number): string {
  if (!Number.isFinite(durationSeconds) || durationSeconds < 0) {
    throw new Error('durationSeconds must be a finite, non-negative number');
  }
  const totalSeconds = Math.floor(durationSeconds);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, '0')}`;
}

function isArmRaiseSideSelection(value: string): value is ArmRaiseSideSelection {
  return value === 'auto' || value === 'left' || value === 'right';
}

export function drawPoseOverlay(
  canvas: HTMLCanvasElement,
  landmarks: readonly PosePoint[] | undefined,
  connections: readonly PoseConnection[],
): void {
  const context = canvas.getContext('2d');
  if (!context) {
    throw new Error('Canvas 2D context is unavailable');
  }

  context.clearRect(0, 0, canvas.width, canvas.height);
  if (!landmarks?.length) {
    return;
  }

  context.lineWidth = Math.max(2, canvas.width / 500);
  context.strokeStyle = '#43e0b0';
  context.fillStyle = '#ffc857';
  for (const { start, end } of connections) {
    const from = landmarks[start];
    const to = landmarks[end];
    if (!from || !to || !isDrawablePoint(from) || !isDrawablePoint(to)) {
      continue;
    }
    context.beginPath();
    context.moveTo(from.x * canvas.width, from.y * canvas.height);
    context.lineTo(to.x * canvas.width, to.y * canvas.height);
    context.stroke();
  }

  const radius = Math.max(3, canvas.width / 180);
  for (const landmark of landmarks) {
    if (!isDrawablePoint(landmark)) {
      continue;
    }
    context.beginPath();
    context.arc(
      landmark.x * canvas.width,
      landmark.y * canvas.height,
      radius,
      0,
      Math.PI * 2,
    );
    context.fill();
  }
}

export function validateVideoDuration(duration: number): string | null {
  if (!Number.isFinite(duration) || duration <= 0) {
    return 'تعذّر قراءة مدة الفيديو.';
  }
  if (duration > MAX_VIDEO_SECONDS) {
    return 'اختر فيديو مدته دقيقتان أو أقل.';
  }
  return null;
}

export default function LocalVideoPoseDemo() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const hasAnalyzedFrameRef = useRef(false);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [videoName, setVideoName] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [status, setStatus] = useState('اختر فيديو محليًا للبدء.');
  const [error, setError] = useState<string | null>(null);
  const [landmarkCount, setLandmarkCount] = useState(0);
  const [counter, setCounter] = useState<ArmRaiseCounterState>(INITIAL_ARM_RAISE_STATE);
  const counterRef = useRef(INITIAL_ARM_RAISE_STATE);
  const [sideSelection, setSideSelection] = useState<ArmRaiseSideSelection>('auto');
  const sideSelectionRef = useRef<ArmRaiseSideSelection>('auto');
  const [manualReferenceCount, setManualReferenceCount] = useState('');
  const [referenceCountError, setReferenceCountError] = useState<string | null>(null);
  const [summary, setSummary] = useState<LocalVideoSummary | null>(null);

  useEffect(() => {
    if (!videoUrl) {
      return;
    }
    return () => URL.revokeObjectURL(videoUrl);
  }, [videoUrl]);

  useEffect(() => {
    if (!isRunning || !videoUrl) {
      return;
    }

    let cancelled = false;
    let animationFrame = 0;
    let lastVideoTime = -1;
    let timestamp = 0;
    let landmarker: import('@mediapipe/tasks-vision').PoseLandmarker | null = null;
    let connections: PoseConnection[] = [];

    async function initializeAndAnalyze() {
      try {
        setError(null);
        setStatus('جارٍ تحميل نموذج الوضعية محليًا داخل المتصفح…');
        const { FilesetResolver, PoseLandmarker } =
          await import('@mediapipe/tasks-vision');
        const fileset = await FilesetResolver.forVisionTasks(WASM_URL);
        landmarker = await PoseLandmarker.createFromOptions(fileset, {
          baseOptions: {
            modelAssetPath: MODEL_URL,
            delegate: 'CPU',
          },
          runningMode: 'VIDEO',
          numPoses: 1,
        });
        connections = PoseLandmarker.POSE_CONNECTIONS;
        if (cancelled) {
          landmarker.close();
          return;
        }

        const video = videoRef.current;
        const canvas = canvasRef.current;
        if (!video || !canvas) {
          throw new Error('Video preview elements are unavailable');
        }

        const renderFrame = () => {
          if (cancelled) {
            return;
          }
          if (video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) {
            if (
              canvas.width !== video.videoWidth ||
              canvas.height !== video.videoHeight
            ) {
              canvas.width = video.videoWidth;
              canvas.height = video.videoHeight;
            }
            if (video.currentTime !== lastVideoTime) {
              if (lastVideoTime >= 0 && video.currentTime < lastVideoTime) {
                counterRef.current = INITIAL_ARM_RAISE_STATE;
                setCounter(INITIAL_ARM_RAISE_STATE);
              }
              timestamp = Math.max(timestamp + 1, performance.now());
              const result = landmarker!.detectForVideo(video, timestamp);
              const landmarks = result.landmarks[0];
              hasAnalyzedFrameRef.current = true;
              lastVideoTime = video.currentTime;
              counterRef.current = advanceArmRaiseCounter(
                counterRef.current,
                landmarks,
                sideSelectionRef.current,
              );
              setLandmarkCount(landmarks?.length ?? 0);
              setCounter(counterRef.current);
              setStatus(
                landmarks?.length
                  ? `تم اكتشاف ${landmarks.length} نقطة وضعية في الإطار الحالي.`
                  : 'لم يُكتشف جسم واضح في الإطار الحالي.',
              );
              drawPoseOverlay(canvas, landmarks, connections);
            }
          }
          animationFrame = requestAnimationFrame(renderFrame);
        };

        setStatus('النموذج جاهز. شغّل الفيديو لمشاهدة النقاط المكتشفة.');
        animationFrame = requestAnimationFrame(renderFrame);
      } catch (cause) {
        if (!cancelled) {
          setError(
            cause instanceof Error
              ? cause.message
              : 'تعذّر تحميل نموذج MediaPipe. تحقق من اتصال الإنترنت ثم أعد المحاولة.',
          );
          setStatus('لم يبدأ تحليل الفيديو.');
          setIsRunning(false);
        }
      }
    }

    void initializeAndAnalyze();
    return () => {
      cancelled = true;
      cancelAnimationFrame(animationFrame);
      landmarker?.close();
    };
  }, [isRunning, videoUrl]);

  function selectVideo(file: File | undefined) {
    setIsRunning(false);
    setLandmarkCount(0);
    counterRef.current = INITIAL_ARM_RAISE_STATE;
    setCounter(INITIAL_ARM_RAISE_STATE);
    setSummary(null);
    setReferenceCountError(null);
    setManualReferenceCount('');
    hasAnalyzedFrameRef.current = false;
    setError(null);
    if (!file) {
      return;
    }
    if (!file.type.startsWith('video/')) {
      setError('اختر ملف فيديو صالحًا.');
      return;
    }
    setVideoName(file.name);
    setVideoUrl(URL.createObjectURL(file));
    setStatus('تم اختيار الفيديو. اضغط بدء تحليل الوضعية.');
  }

  function checkDuration() {
    const video = videoRef.current;
    if (!video) {
      return;
    }
    const durationError = validateVideoDuration(video.duration);
    if (durationError) {
      setError(durationError);
      setVideoUrl(null);
      setVideoName('');
      setStatus('لم يتم قبول الفيديو.');
      setIsRunning(false);
    }
  }

  return (
    <section className="session-summary" aria-labelledby="local-pose-title">
      <div className="summary-heading">
        <div>
          <p className="summary-kicker">تحليل محلي في المتصفح</p>
          <h2 id="local-pose-title">جرّب فيديو قصيرًا</h2>
        </div>
        <span className="simulation-badge">الفيديو لا يُرفع</span>
      </div>
      <p>
        اختر فيديو لا يتجاوز دقيقتين. يُحمّل المتصفح MediaPipe من الإنترنت، ثم يحلل
        الفيديو على جهازك ويعرض هيكل النقاط المكتشفة. لا يُرسل الفيديو إلى خادم. أضفنا
        عدّادًا تجريبيًا لحركة رفع الذراع لاختبار الوظيفة؛ دقته ومطابقة الحركة غير متحقق
        منهما، وليس تقييمًا للتمرين أو نصيحة علاجية.
      </p>
      <div className="cannot-assess-result" role="note">
        <strong>تنبيه: عدّاد تجريبي غير مُعتمد</strong>
        <p>
          خريطة النقاط والحدود أدناه افتراضات برمجية للاختبار فقط. لم تُراجع طبيًا أو
          تُتحقق مقابل مجموعة بيانات؛ قد يكون العدد خاطئًا ولا تستخدمه لتحديد جرعة
          تمرين.
        </p>
        <details>
          <summary>خريطة النقاط والحدود التجريبية</summary>
          <ul>
            <li>
              النقاط: كتف ومعصم وورك من الجهة الأوضح في MediaPipe Pose (يسار 11/15/23،
              يمين 12/16/24).
            </li>
            <li>
              الزاوية ثنائية الأبعاد بين اتجاه الكتف إلى الورك واتجاه الكتف إلى المعصم.
            </li>
            <li>
              بداية الحركة عند زاوية ≤ {ARM_RAISE_DEMO.loweredAngleDegrees}°، وبلوغ
              الرفع عند ≥ {ARM_RAISE_DEMO.raisedAngleDegrees}°؛ يُحتسب تكرار بعد الرجوع
              إلى زاوية البداية.
            </li>
            <li>
              يلزم ظهور النقاط الثلاث بوضوح MediaPipe visibility ≥{' '}
              {ARM_RAISE_DEMO.minimumVisibility}.
            </li>
            <li>
              قد تقل دقة النقاط والعدّ عند التصوير الجانبي أو حجب الذراع؛ الزاوية ثنائية
              الأبعاد ولا تعوّض العمق أو تغيّر اتجاه الكاميرا.
            </li>
            <li>
              هدف العرض {ARM_RAISE_DEMO.targetRepetitions} تكرارات للتجربة فقط، وليس
              هدفًا علاجيًا؛ العدد المعروض يحسب الحركة المكتشفة ولا يُملأ مسبقًا.
            </li>
          </ul>
        </details>
      </div>
      <label className="pain-demo-label" htmlFor="local-pose-video">
        ملف فيديو من جهازك
      </label>
      <input
        id="local-pose-video"
        type="file"
        accept="video/*"
        onChange={(event) => selectVideo(event.currentTarget.files?.[0])}
      />
      <label className="pain-demo-label" htmlFor="arm-raise-side">
        جهة الذراع المراد تتبعها
      </label>
      <select
        id="arm-raise-side"
        value={sideSelection}
        onChange={(event) => {
          const value = event.currentTarget.value;
          if (!isArmRaiseSideSelection(value)) {
            throw new Error(`Unsupported arm side selection: ${value}`);
          }
          const nextSelection = value;
          sideSelectionRef.current = nextSelection;
          setSideSelection(nextSelection);
          counterRef.current = INITIAL_ARM_RAISE_STATE;
          setCounter(INITIAL_ARM_RAISE_STATE);
          setSummary(null);
        }}
      >
        <option value="auto">تلقائي: أوضح جهة</option>
        <option value="left">يسار الشخص حسب MediaPipe</option>
        <option value="right">يمين الشخص حسب MediaPipe</option>
      </select>
      <label className="pain-demo-label" htmlFor="manual-reference-count">
        عدد التكرارات الذي لاحظته يدويًا (اختياري للمقارنة)
      </label>
      <input
        id="manual-reference-count"
        type="number"
        min="0"
        step="1"
        inputMode="numeric"
        value={manualReferenceCount}
        onChange={(event) => {
          setManualReferenceCount(event.currentTarget.value);
          setReferenceCountError(null);
          setSummary(null);
        }}
      />
      <p className="field-help">
        احسب التكرارات المكتملة بنفسك، ثم قارنها بعد انتهاء الفيديو. العدد اليدوي مرجع
        ملاحظتك فقط وليس تقييمًا سريريًا.
      </p>
      {referenceCountError && (
        <p className="pose-error" role="alert">
          {referenceCountError}
        </p>
      )}
      {videoName && <p dir="ltr">المحدد: {videoName}</p>}
      {videoUrl && (
        <>
          <div className="pose-video-stage">
            <div className="pose-video-frame">
              <video
                ref={videoRef}
                src={videoUrl}
                controls
                playsInline
                onLoadedMetadata={checkDuration}
                onPlay={() => setSummary(null)}
                onEnded={() => {
                  const video = videoRef.current;
                  if (!hasAnalyzedFrameRef.current) {
                    setStatus('ابدأ تحليل الوضعية قبل انتهاء الفيديو لعرض الملخص.');
                    return;
                  }
                  if (video && Number.isFinite(video.duration)) {
                    try {
                      const manualCount = parseManualRepCount(manualReferenceCount);
                      setReferenceCountError(null);
                      setSummary({
                        detectedRepetitions: counterRef.current.repetitions,
                        durationSeconds: video.duration,
                        manualReferenceRepetitions: manualCount,
                      });
                    } catch (cause) {
                      setReferenceCountError(
                        cause instanceof Error
                          ? cause.message
                          : 'تعذّر قراءة العدد اليدوي.',
                      );
                      setSummary(null);
                    }
                  }
                }}
                onError={() => setError('تعذّر فتح الفيديو. جرّب ملف MP4 مدعومًا.')}
              />
              <canvas ref={canvasRef} aria-label="نقاط الوضعية المكتشفة" />
            </div>
          </div>
          <button
            className="demo-run-button"
            type="button"
            disabled={isRunning}
            onClick={() => {
              setError(null);
              setSummary(null);
              counterRef.current = INITIAL_ARM_RAISE_STATE;
              setCounter(INITIAL_ARM_RAISE_STATE);
              hasAnalyzedFrameRef.current = false;
              setIsRunning(true);
            }}
          >
            {isRunning ? 'جارٍ التحليل…' : 'بدء تحليل الوضعية'}
          </button>
          <p className="rep-counter" aria-live="polite">
            التكرارات المكتملة المكتشفة: {counter.repetitions} /{' '}
            {ARM_RAISE_DEMO.targetRepetitions}
          </p>
          <div className="counter-diagnostics" aria-live="polite">
            <p>
              الجانب المتابع:{' '}
              {counter.side === 'left'
                ? 'الأيسر حسب MediaPipe'
                : counter.side === 'right'
                  ? 'الأيمن حسب MediaPipe'
                  : 'غير متاح — أظهر الكتف والمعصم والورك بوضوح'}
            </p>
            <p>
              زاوية الذراع المقدّرة:{' '}
              {counter.angleDegrees === null
                ? 'غير متاحة'
                : `${Math.round(counter.angleDegrees)}°`}
            </p>
            <p>
              أدنى visibility للنقاط الثلاث:{' '}
              {counter.visibility === null
                ? 'غير متاح'
                : `${Math.round(counter.visibility * 100)}%`}
            </p>
            <p>
              حالة العدّ:{' '}
              {counter.phase === 'waiting'
                ? 'بانتظار بدء الحركة من وضع الذراع لأسفل'
                : counter.phase === 'lowered'
                  ? 'تم رصد الوضع المنخفض؛ ارفع الذراع'
                  : 'تم رصد الرفع؛ أعد الذراع إلى وضع البداية'}
            </p>
            <p className="counter-test-instruction">
              جرّب نفس الحركة مرتين: مرة مواجهًا للكاميرا ومرة جانبيًا. ارفع ذراعًا
              واحدة من أسفل إلى أعلى ثم أعدها، وقارن الزاوية والـ visibility والعدد.
              يمكنك اختيار الجهة بدل التلقائي إذا كانت جهة واحدة أوضح.
            </p>
          </div>
          {summary && (
            <div className="pose-session-result" role="status" aria-live="polite">
              <h3>ملخص تجريبي لهذا الفيديو</h3>
              <p>التكرارات المكتملة التي رصدها العداد: {summary.detectedRepetitions}</p>
              <p>مدة الفيديو: {formatClipDuration(summary.durationSeconds)}</p>
              {summary.manualReferenceRepetitions !== null && (
                <>
                  <p>العدد اليدوي الذي أدخلته: {summary.manualReferenceRepetitions}</p>
                  <p>
                    الفرق المطلق عن العدد اليدوي:{' '}
                    {Math.abs(
                      summary.detectedRepetitions - summary.manualReferenceRepetitions,
                    )}{' '}
                    تكرارات
                  </p>
                </>
              )}
              <p>
                هذا ملخص آلي مؤقت داخل الصفحة فقط، وليس تقييمًا دقيقًا أو سجلًا طبيًا.
              </p>
              <button
                className="demo-run-button"
                type="button"
                onClick={() => {
                  const video = videoRef.current;
                  if (video) {
                    video.currentTime = 0;
                    void video.play();
                  }
                }}
              >
                إعادة الفيديو
              </button>
            </div>
          )}
        </>
      )}
      <p role="status" aria-live="polite">
        {status}
        {landmarkCount > 0 ? ` (${landmarkCount} نقطة)` : ''}
      </p>
      {error && (
        <p className="pose-error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}

function isDrawablePoint(point: PosePoint): boolean {
  return (
    Number.isFinite(point.x) &&
    Number.isFinite(point.y) &&
    point.x >= 0 &&
    point.x <= 1 &&
    point.y >= 0 &&
    point.y <= 1
  );
}

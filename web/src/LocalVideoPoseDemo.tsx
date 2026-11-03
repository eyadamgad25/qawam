import { tr } from './i18n';
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
    throw new Error(
      tr(
        'أدخل عددًا صحيحًا غير سالب للتكرارات اليدوية.',
        'Enter a whole number of zero or more for the manual reps.',
      ),
    );
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
    return tr('تعذّر قراءة مدة الفيديو.', 'Could not read the video length.');
  }
  if (duration > MAX_VIDEO_SECONDS) {
    return tr(
      'اختر فيديو مدته دقيقتان أو أقل.',
      'Choose a video of two minutes or less.',
    );
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
  const [status, setStatus] = useState(
    tr('اختر فيديو محليًا للبدء.', 'Choose a local video to start.'),
  );
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
        setStatus(
          tr(
            'جارٍ تحميل نموذج الوضعية محليًا داخل المتصفح…',
            'Loading the pose model in the browser…',
          ),
        );
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
                  ? tr(
                      `تم اكتشاف ${landmarks.length} نقطة وضعية في الإطار الحالي.`,
                      `Found ${landmarks.length} pose points in the current frame.`,
                    )
                  : tr(
                      'لم يُكتشف جسم واضح في الإطار الحالي.',
                      'No clear body found in the current frame.',
                    ),
              );
              drawPoseOverlay(canvas, landmarks, connections);
            }
          }
          animationFrame = requestAnimationFrame(renderFrame);
        };

        setStatus(
          tr(
            'النموذج جاهز. شغّل الفيديو لمشاهدة النقاط المكتشفة.',
            'Model ready. Play the video to see the detected points.',
          ),
        );
        animationFrame = requestAnimationFrame(renderFrame);
      } catch (cause) {
        if (!cancelled) {
          setError(
            cause instanceof Error
              ? cause.message
              : tr(
                  'تعذّر تحميل نموذج MediaPipe. تحقق من اتصال الإنترنت ثم أعد المحاولة.',
                  'Could not load the MediaPipe model. Check the internet connection and try again.',
                ),
          );
          setStatus(tr('لم يبدأ تحليل الفيديو.', 'Video analysis did not start.'));
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
      setError(tr('اختر ملف فيديو صالحًا.', 'Choose a valid video file.'));
      return;
    }
    setVideoName(file.name);
    setVideoUrl(URL.createObjectURL(file));
    setStatus(
      tr(
        'تم اختيار الفيديو. اضغط بدء تحليل الوضعية.',
        'Video chosen. Press Start pose analysis.',
      ),
    );
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
      setStatus(tr('لم يتم قبول الفيديو.', 'The video was not accepted.'));
      setIsRunning(false);
    }
  }

  return (
    <section className="session-summary" aria-labelledby="local-pose-title">
      <div className="summary-heading">
        <div>
          <p className="summary-kicker">
            {tr('تحليل محلي في المتصفح', 'Local analysis in the browser')}
          </p>
          <h2 id="local-pose-title">{tr('جرّب فيديو قصيرًا', 'Try a short video')}</h2>
        </div>
        <span className="simulation-badge">
          {tr('الفيديو لا يُرفع', 'Video is never uploaded')}
        </span>
      </div>
      <p>
        {tr(
          'اختر فيديو لا يتجاوز دقيقتين. يُحمّل المتصفح MediaPipe من الإنترنت، ثم يحلل الفيديو على جهازك ويعرض هيكل النقاط المكتشفة. لا يُرسل الفيديو إلى خادم. أضفنا عدّادًا تجريبيًا لحركة رفع الذراع لاختبار الوظيفة؛ دقته ومطابقة الحركة غير متحقق منهما، وليس تقييمًا للتمرين أو نصيحة علاجية.',
          'Choose a video of up to two minutes. The browser runs MediaPipe and draws the detected skeleton on your device; the video is never sent to a server. An experimental arm-raise counter tests the function; its accuracy is unverified, and it is not an exercise assessment or treatment advice.',
        )}
      </p>
      <div className="cannot-assess-result" role="note">
        <strong>
          {tr(
            'تنبيه: عدّاد تجريبي غير مُعتمد',
            'Note: experimental, unapproved counter',
          )}
        </strong>
        <p>
          {tr(
            'خريطة النقاط والحدود أدناه افتراضات برمجية للاختبار فقط. لم تُراجع طبيًا أو تُتحقق مقابل مجموعة بيانات؛ قد يكون العدد خاطئًا ولا تستخدمه لتحديد جرعة تمرين.',
            'The point mapping and limits below are test assumptions only. They are not medically reviewed or checked against a dataset; the count may be wrong, so do not use it to set an exercise dose.',
          )}
        </p>
        <details>
          <summary>
            {tr(
              'خريطة النقاط والحدود التجريبية',
              'Experimental point mapping and limits',
            )}
          </summary>
          <ul>
            <li>
              {tr(
                'النقاط: كتف ومعصم وورك من الجهة الأوضح في MediaPipe Pose (يسار 11/15/23، يمين 12/16/24).',
                'Points: shoulder, wrist and hip on the clearer side in MediaPipe Pose (left 11/15/23, right 12/16/24).',
              )}
            </li>
            <li>
              {tr(
                'الزاوية ثنائية الأبعاد بين اتجاه الكتف إلى الورك واتجاه الكتف إلى المعصم.',
                'The 2D angle between shoulder-to-hip and shoulder-to-wrist.',
              )}
            </li>
            <li>
              {tr('بداية الحركة عند زاوية ≤', 'Movement starts at ≤')}{' '}
              {ARM_RAISE_DEMO.loweredAngleDegrees}°
              {tr('، وبلوغ الرفع عند ≥', ', the raise is reached at ≥')}{' '}
              {ARM_RAISE_DEMO.raisedAngleDegrees}°
              {tr(
                '؛ يُحتسب تكرار بعد الرجوع إلى زاوية البداية.',
                '; a rep counts after returning to the start angle.',
              )}
            </li>
            <li>
              {tr(
                'يلزم ظهور النقاط الثلاث بوضوح MediaPipe visibility ≥',
                'All three points must be visible, MediaPipe visibility ≥',
              )}{' '}
              {ARM_RAISE_DEMO.minimumVisibility}.
            </li>
            <li>
              {tr(
                'قد تقل دقة النقاط والعدّ عند التصوير الجانبي أو حجب الذراع؛ الزاوية ثنائية الأبعاد ولا تعوّض العمق أو تغيّر اتجاه الكاميرا.',
                'Points and counting may be less accurate side-on or when the arm is hidden; the angle is 2D and does not correct for depth or camera direction.',
              )}
            </li>
            <li>
              {tr('هدف العرض', 'Demo target')} {ARM_RAISE_DEMO.targetRepetitions}{' '}
              {tr(
                'تكرارات للتجربة فقط، وليس هدفًا علاجيًا؛ العدد المعروض يحسب الحركة المكتشفة ولا يُملأ مسبقًا.',
                'reps for testing only, not a treatment target; the count shows detected movement and is never pre-filled.',
              )}
            </li>
          </ul>
        </details>
      </div>
      <label className="pain-demo-label" htmlFor="local-pose-video">
        {tr('ملف فيديو من جهازك', 'Video file from your device')}
      </label>
      <input
        id="local-pose-video"
        type="file"
        accept="video/*"
        onChange={(event) => selectVideo(event.currentTarget.files?.[0])}
      />
      <label className="pain-demo-label" htmlFor="arm-raise-side">
        {tr('جهة الذراع المراد تتبعها', 'Arm side to track')}
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
        <option value="auto">
          {tr('تلقائي: أوضح جهة', 'Automatic: clearer side')}
        </option>
        <option value="left">
          {tr('يسار الشخص حسب MediaPipe', 'Person’s left (MediaPipe)')}
        </option>
        <option value="right">
          {tr('يمين الشخص حسب MediaPipe', 'Person’s right (MediaPipe)')}
        </option>
      </select>
      <label className="pain-demo-label" htmlFor="manual-reference-count">
        {tr(
          'عدد التكرارات الذي لاحظته يدويًا (اختياري للمقارنة)',
          'Reps you counted yourself (optional, for comparison)',
        )}
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
        {tr(
          'احسب التكرارات المكتملة بنفسك، ثم قارنها بعد انتهاء الفيديو. العدد اليدوي مرجع ملاحظتك فقط وليس تقييمًا سريريًا.',
          'Count the completed reps yourself, then compare after the video ends. Your count is only your observation, not a clinical assessment.',
        )}
      </p>
      {referenceCountError && (
        <p className="pose-error" role="alert">
          {referenceCountError}
        </p>
      )}
      {videoName && (
        <p dir="ltr">
          {tr('المحدد', 'Selected')}: {videoName}
        </p>
      )}
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
                    setStatus(
                      tr(
                        'ابدأ تحليل الوضعية قبل انتهاء الفيديو لعرض الملخص.',
                        'Start pose analysis before the video ends to see the summary.',
                      ),
                    );
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
                          : tr(
                              'تعذّر قراءة العدد اليدوي.',
                              'Could not read the manual count.',
                            ),
                      );
                      setSummary(null);
                    }
                  }
                }}
                onError={() =>
                  setError(
                    tr(
                      'تعذّر فتح الفيديو. جرّب ملف MP4 مدعومًا.',
                      'Could not open the video. Try a supported MP4 file.',
                    ),
                  )
                }
              />
              <canvas
                ref={canvasRef}
                aria-label={tr('نقاط الوضعية المكتشفة', 'Detected pose points')}
              />
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
            {isRunning
              ? tr('جارٍ التحليل…', 'Analysing…')
              : tr('بدء تحليل الوضعية', 'Start pose analysis')}
          </button>
          <p className="rep-counter" aria-live="polite">
            {tr('التكرارات المكتملة المكتشفة', 'Completed reps detected')}:{' '}
            {counter.repetitions} / {ARM_RAISE_DEMO.targetRepetitions}
          </p>
          <div className="counter-diagnostics" aria-live="polite">
            <p>
              {tr('الجانب المتابع', 'Tracked side')}:{' '}
              {counter.side === 'left'
                ? tr('الأيسر حسب MediaPipe', 'Left (MediaPipe)')
                : counter.side === 'right'
                  ? tr('الأيمن حسب MediaPipe', 'Right (MediaPipe)')
                  : tr(
                      'غير متاح — أظهر الكتف والمعصم والورك بوضوح',
                      'Not available — show the shoulder, wrist and hip clearly',
                    )}
            </p>
            <p>
              {tr('زاوية الذراع المقدّرة', 'Estimated arm angle')}:{' '}
              {counter.angleDegrees === null
                ? tr('غير متاحة', 'Not available')
                : `${Math.round(counter.angleDegrees)}°`}
            </p>
            <p>
              {tr(
                'أدنى visibility للنقاط الثلاث',
                'Lowest visibility of the three points',
              )}
              :{' '}
              {counter.visibility === null
                ? tr('غير متاح', 'Not available')
                : `${Math.round(counter.visibility * 100)}%`}
            </p>
            <p>
              {tr('حالة العدّ', 'Counter state')}:{' '}
              {counter.phase === 'waiting'
                ? tr(
                    'بانتظار بدء الحركة من وضع الذراع لأسفل',
                    'Waiting for the movement to start with the arm down',
                  )
                : counter.phase === 'lowered'
                  ? tr(
                      'تم رصد الوضع المنخفض؛ ارفع الذراع',
                      'Low position seen; raise the arm',
                    )
                  : tr(
                      'تم رصد الرفع؛ أعد الذراع إلى وضع البداية',
                      'Raise seen; return the arm to the start',
                    )}
            </p>
            <p className="counter-test-instruction">
              {tr(
                'جرّب نفس الحركة مرتين: مرة مواجهًا للكاميرا ومرة جانبيًا. ارفع ذراعًا واحدة من أسفل إلى أعلى ثم أعدها، وقارن الزاوية والـ visibility والعدد. يمكنك اختيار الجهة بدل التلقائي إذا كانت جهة واحدة أوضح.',
                'Try the same movement twice: once facing the camera and once side-on. Raise one arm from low to high and back, and compare the angle, visibility and count. Pick a side instead of automatic if one side is clearer.',
              )}
            </p>
          </div>
          {summary && (
            <div className="pose-session-result" role="status" aria-live="polite">
              <h3>
                {tr('ملخص تجريبي لهذا الفيديو', 'Experimental summary for this video')}
              </h3>
              <p>
                {tr(
                  'التكرارات المكتملة التي رصدها العداد',
                  'Completed reps the counter saw',
                )}
                : {summary.detectedRepetitions}
              </p>
              <p>
                {tr('مدة الفيديو', 'Video length')}:{' '}
                {formatClipDuration(summary.durationSeconds)}
              </p>
              {summary.manualReferenceRepetitions !== null && (
                <>
                  <p>
                    {tr('العدد اليدوي الذي أدخلته', 'Your manual count')}:{' '}
                    {summary.manualReferenceRepetitions}
                  </p>
                  <p>
                    {tr(
                      'الفرق المطلق عن العدد اليدوي',
                      'Absolute difference from your count',
                    )}
                    :{' '}
                    {Math.abs(
                      summary.detectedRepetitions - summary.manualReferenceRepetitions,
                    )}{' '}
                    {tr('تكرارات', 'reps')}
                  </p>
                </>
              )}
              <p>
                {tr(
                  'هذا ملخص آلي مؤقت داخل الصفحة فقط، وليس تقييمًا دقيقًا أو سجلًا طبيًا.',
                  'This is a temporary in-page summary, not an accurate assessment or a medical record.',
                )}
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
                {tr('إعادة الفيديو', 'Replay the video')}
              </button>
            </div>
          )}
        </>
      )}
      <p role="status" aria-live="polite">
        {status}
        {landmarkCount > 0
          ? tr(` (${landmarkCount} نقطة)`, ` (${landmarkCount} points)`)
          : ''}
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

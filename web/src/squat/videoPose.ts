/**
 * Run MediaPipe Pose Landmarker over a local video file, frame by frame, in
 * the browser. The video never leaves the device; only the model and WASM
 * runtime are downloaded.
 */
import type { PoseFrame } from './poseFrames';

export const WASM_URL =
  'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.1.1/wasm';
export const MODEL_URL =
  'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task';
export const MAX_SECONDS = 120;
/** Frames analysed per second of video. */
export const SAMPLE_FPS = 15;

type Landmarker = import('@mediapipe/tasks-vision').PoseLandmarker;

let landmarkerPromise: Promise<Landmarker> | null = null;

export function loadLandmarker(): Promise<Landmarker> {
  if (!landmarkerPromise) {
    landmarkerPromise = (async () => {
      const { FilesetResolver, PoseLandmarker } =
        await import('@mediapipe/tasks-vision');
      const fileset = await FilesetResolver.forVisionTasks(WASM_URL);
      return PoseLandmarker.createFromOptions(fileset, {
        baseOptions: { modelAssetPath: MODEL_URL, delegate: 'CPU' },
        runningMode: 'VIDEO',
        numPoses: 1,
      });
    })().catch((error: unknown) => {
      landmarkerPromise = null;
      throw error;
    });
  }
  return landmarkerPromise;
}

/** Monotonic timestamps across clips: VIDEO mode rejects going back in time. */
let lastTimestampMs = 0;

function waitFor(
  video: HTMLVideoElement,
  event: 'loadeddata' | 'seeked',
): Promise<void> {
  return new Promise((resolve, reject) => {
    const done = () => {
      video.removeEventListener(event, done);
      video.removeEventListener('error', fail);
      resolve();
    };
    const fail = () => {
      video.removeEventListener(event, done);
      video.removeEventListener('error', fail);
      reject(new Error('تعذّر فتح الفيديو. جرّب ملف MP4 مدعومًا.'));
    };
    video.addEventListener(event, done);
    video.addEventListener('error', fail);
  });
}

export async function extractPoseFrames(
  file: File,
  onProgress: (fraction: number) => void,
  signal?: AbortSignal,
): Promise<PoseFrame[]> {
  const landmarker = await loadLandmarker();
  const url = URL.createObjectURL(file);
  const video = document.createElement('video');
  video.muted = true;
  video.playsInline = true;
  video.preload = 'auto';
  try {
    const ready = waitFor(video, 'loadeddata');
    video.src = url;
    await ready;
    const duration = video.duration;
    if (!Number.isFinite(duration) || duration <= 0) {
      throw new Error('تعذّر قراءة مدة الفيديو.');
    }
    if (duration > MAX_SECONDS) {
      throw new Error('اختر فيديو مدته دقيقتان أو أقل.');
    }
    const frames: PoseFrame[] = [];
    const total = Math.floor(duration * SAMPLE_FPS);
    for (let i = 0; i < total; i += 1) {
      if (signal?.aborted) {
        throw new Error('أُلغي التحليل.');
      }
      const time = i / SAMPLE_FPS;
      const seeked = waitFor(video, 'seeked');
      video.currentTime = time;
      await seeked;
      lastTimestampMs = Math.max(lastTimestampMs + 1, Math.round(performance.now()));
      const result = landmarker.detectForVideo(video, lastTimestampMs);
      const marks = result.landmarks[0];
      frames.push({
        timeSeconds: time,
        width: video.videoWidth,
        height: video.videoHeight,
        landmarks: marks
          ? marks.map((m) => ({ x: m.x, y: m.y, z: m.z, visibility: m.visibility }))
          : null,
      });
      onProgress((i + 1) / total);
    }
    return frames;
  } finally {
    video.removeAttribute('src');
    video.load();
    URL.revokeObjectURL(url);
  }
}

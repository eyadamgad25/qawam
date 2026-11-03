/**
 * Run MediaPipe Pose Landmarker over a local video file, frame by frame, in
 * the browser. The video never leaves the device. The model and WASM runtime
 * are served from this app when `prepare-offline` copied them into public/
 * (works with no internet), otherwise from the public CDN.
 */
import { tr } from '../i18n';
import type { PoseFrame } from './poseFrames';

export const WASM_URL =
  'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.1.1/wasm';
export const MODEL_URL =
  'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task';
const BASE = import.meta.env.BASE_URL ?? '/';
export const LOCAL_WASM_URL = `${BASE}mediapipe/wasm`;
export const LOCAL_MODEL_URL = `${BASE}models/pose_landmarker_lite.task`;
/** Smallest plausible model file; a dev server answers unknown paths with index.html. */
const MIN_MODEL_BYTES = 1_000_000;

export type AssetSource = 'local' | 'cdn';

export interface PoseAssets {
  wasmUrl: string;
  modelUrl: string;
  source: AssetSource;
}

/** True when the response is the real file, not a dev server's HTML fallback. */
export function looksLikeAsset(
  response: Pick<Response, 'ok' | 'headers'>,
  minBytes = 0,
): boolean {
  if (!response.ok) return false;
  const type = response.headers.get('content-type') ?? '';
  if (type.includes('text/html')) return false;
  const length = Number(response.headers.get('content-length') ?? NaN);
  return Number.isNaN(length) ? true : length >= minBytes;
}

/** Prefer the copies served by this app; fall back to the CDN. */
export async function resolvePoseAssets(
  fetcher: typeof fetch = globalThis.fetch.bind(globalThis),
): Promise<PoseAssets> {
  try {
    const [wasm, model] = await Promise.all([
      fetcher(`${LOCAL_WASM_URL}/vision_wasm_internal.wasm`, { method: 'HEAD' }),
      fetcher(LOCAL_MODEL_URL, { method: 'HEAD' }),
    ]);
    if (looksLikeAsset(wasm) && looksLikeAsset(model, MIN_MODEL_BYTES)) {
      return { wasmUrl: LOCAL_WASM_URL, modelUrl: LOCAL_MODEL_URL, source: 'local' };
    }
  } catch {
    // no local copy: use the CDN
  }
  return { wasmUrl: WASM_URL, modelUrl: MODEL_URL, source: 'cdn' };
}

/** Where the pose files came from, for the diagnostics panel. */
export let poseAssetSource: AssetSource | null = null;
export const MAX_SECONDS = 120;
/** Frames analysed per second of video. */
export const SAMPLE_FPS = 15;

type Landmarker = import('@mediapipe/tasks-vision').PoseLandmarker;

let landmarkerPromise: Promise<Landmarker> | null = null;
/** Which processor the pose model ended up on, for the diagnostics panel. */
export let landmarkerDelegate: 'GPU' | 'CPU' | null = null;

export function loadLandmarker(): Promise<Landmarker> {
  if (!landmarkerPromise) {
    landmarkerPromise = (async () => {
      const { FilesetResolver, PoseLandmarker } =
        await import('@mediapipe/tasks-vision');
      const assets = await resolvePoseAssets();
      poseAssetSource = assets.source;
      const fileset = await FilesetResolver.forVisionTasks(assets.wasmUrl);
      const create = (delegate: 'GPU' | 'CPU') =>
        PoseLandmarker.createFromOptions(fileset, {
          baseOptions: { modelAssetPath: assets.modelUrl, delegate },
          runningMode: 'VIDEO',
          numPoses: 1,
        });
      // The graphics card is several times faster; fall back to the CPU.
      try {
        const landmarker = await create('GPU');
        landmarkerDelegate = 'GPU';
        return landmarker;
      } catch {
        const landmarker = await create('CPU');
        landmarkerDelegate = 'CPU';
        return landmarker;
      }
    })().catch((error: unknown) => {
      landmarkerPromise = null;
      throw error;
    });
  }
  return landmarkerPromise;
}

/** Monotonic timestamps across clips: VIDEO mode rejects going back in time. */
let lastTimestampMs = 0;

function nextTimestamp(): number {
  lastTimestampMs = Math.max(lastTimestampMs + 1, Math.round(performance.now()));
  return lastTimestampMs;
}

/** Pose of the frame the video element shows right now (live camera). */
export function detectCurrentFrame(
  landmarker: Landmarker,
  video: HTMLVideoElement,
  timeSeconds: number,
): PoseFrame {
  const result = landmarker.detectForVideo(video, nextTimestamp());
  const marks = result.landmarks[0];
  return {
    timeSeconds,
    width: video.videoWidth,
    height: video.videoHeight,
    landmarks: marks
      ? marks.map((m) => ({ x: m.x, y: m.y, z: m.z, visibility: m.visibility }))
      : null,
  };
}

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
      reject(
        new Error(
          tr(
            'تعذّر فتح الفيديو. جرّب ملف MP4 مدعومًا.',
            'Could not open the video. Try a supported MP4 file.',
          ),
        ),
      );
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
      throw new Error(
        tr('تعذّر قراءة مدة الفيديو.', 'Could not read the video length.'),
      );
    }
    if (duration > MAX_SECONDS) {
      throw new Error(
        tr('اختر فيديو مدته دقيقتان أو أقل.', 'Choose a video of two minutes or less.'),
      );
    }
    const frames: PoseFrame[] = [];
    const total = Math.floor(duration * SAMPLE_FPS);
    for (let i = 0; i < total; i += 1) {
      if (signal?.aborted) {
        throw new Error(tr('أُلغي التحليل.', 'Analysis cancelled.'));
      }
      const time = i / SAMPLE_FPS;
      const seeked = waitFor(video, 'seeked');
      video.currentTime = time;
      await seeked;
      frames.push(detectCurrentFrame(landmarker, video, time));
      onProgress((i + 1) / total);
    }
    return frames;
  } finally {
    video.removeAttribute('src');
    video.load();
    URL.revokeObjectURL(url);
  }
}

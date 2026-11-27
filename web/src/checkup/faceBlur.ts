/**
 * Hides the face in the camera view: the head region (MediaPipe points 0-10: nose, eyes, ears, mouth) is drawn
 * pixelated on the overlay canvas. Pixelation by down- and up-scaling works in every browser, unlike canvas blur
 * filters. Nothing is stored; this only changes what is shown.
 */
import type { PoseLandmark } from '../exercise/poseFrames';

const HEAD = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
const MIN_VISIBILITY = 0.3;
const PAD = 0.6;
const BLOCKS = 8;

export interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
}

/** The head box in pixels, padded and kept inside the frame; null when no head point is seen. */
export function faceBox(
  landmarks: readonly PoseLandmark[] | null | undefined,
  width: number,
  height: number,
): Box | null {
  const points = HEAD.map((i) => landmarks?.[i]).filter(
    (p): p is PoseLandmark =>
      !!p &&
      (p.visibility ?? 1) >= MIN_VISIBILITY &&
      Number.isFinite(p.x) &&
      Number.isFinite(p.y),
  );
  if (points.length === 0) {
    return null;
  }
  const xs = points.map((p) => p.x * width);
  const ys = points.map((p) => p.y * height);
  const size = Math.max(
    Math.max(...xs) - Math.min(...xs),
    Math.max(...ys) - Math.min(...ys),
    width * 0.04,
  );
  const cx = (Math.max(...xs) + Math.min(...xs)) / 2;
  const cy = (Math.max(...ys) + Math.min(...ys)) / 2;
  const half = (size * (1 + PAD * 2)) / 2;
  const x = Math.max(0, cx - half);
  const y = Math.max(0, cy - half);
  return {
    x,
    y,
    w: Math.min(width, cx + half) - x,
    h: Math.min(height, cy + half) - y,
  };
}

/** Draws the pixelated head of `video` onto `canvas` (call after the pose overlay is drawn). */
export function blurFace(
  canvas: HTMLCanvasElement,
  video: HTMLVideoElement,
  landmarks: readonly PoseLandmark[] | null | undefined,
): void {
  const box = faceBox(landmarks, canvas.width, canvas.height);
  const context = canvas.getContext('2d');
  if (!box || !context || box.w < 2 || box.h < 2) {
    return;
  }
  const small = document.createElement('canvas');
  small.width = BLOCKS;
  small.height = BLOCKS;
  const tiny = small.getContext('2d');
  if (!tiny) {
    context.fillStyle = '#3a4a5a';
    context.fillRect(box.x, box.y, box.w, box.h);
    return;
  }
  tiny.drawImage(video, box.x, box.y, box.w, box.h, 0, 0, BLOCKS, BLOCKS);
  context.save();
  context.imageSmoothingEnabled = false;
  context.drawImage(small, 0, 0, BLOCKS, BLOCKS, box.x, box.y, box.w, box.h);
  context.restore();
}

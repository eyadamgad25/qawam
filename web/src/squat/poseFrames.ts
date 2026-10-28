/**
 * Per-frame pose output as the squat session stores it: normalised MediaPipe
 * landmarks plus the frame size, so angles are computed in pixels (a 2D angle
 * in normalised units would be distorted by the video's aspect ratio).
 */
import type { Point2D } from '../anglePipeline';
import { MEDIAPIPE_INDEX } from './exercisePack';

export interface PoseLandmark {
  x: number;
  y: number;
  z?: number;
  visibility?: number;
}

export interface PoseFrame {
  timeSeconds: number;
  width: number;
  height: number;
  /** null when no person was detected in the frame */
  landmarks: readonly PoseLandmark[] | null;
}

export function pixelPoints(frame: PoseFrame): Record<string, Point2D | undefined> {
  const points: Record<string, Point2D | undefined> = {};
  if (!frame.landmarks) {
    return points;
  }
  for (const [name, index] of Object.entries(MEDIAPIPE_INDEX)) {
    const mark = frame.landmarks[index];
    if (mark && Number.isFinite(mark.x) && Number.isFinite(mark.y)) {
      points[name] = [mark.x * frame.width, mark.y * frame.height];
    }
  }
  return points;
}

export function visibilityOf(frame: PoseFrame, name: string): number {
  const index = MEDIAPIPE_INDEX[name];
  if (index === undefined || !frame.landmarks) {
    return 0;
  }
  return frame.landmarks[index]?.visibility ?? 0;
}

export function median(values: readonly number[]): number | null {
  const finite = values.filter(Number.isFinite).sort((a, b) => a - b);
  if (finite.length === 0) {
    return null;
  }
  const middle = Math.floor(finite.length / 2);
  return finite.length % 2
    ? finite[middle]!
    : (finite[middle - 1]! + finite[middle]!) / 2;
}

export function percentile(values: readonly number[], q: number): number | null {
  const finite = values.filter(Number.isFinite).sort((a, b) => a - b);
  if (finite.length === 0) {
    return null;
  }
  const position = (finite.length - 1) * q;
  const low = Math.floor(position);
  const high = Math.ceil(position);
  return finite[low]! + (finite[high]! - finite[low]!) * (position - low);
}

/**
 * Exercise packs (rules/packs/*.json) for the browser.
 *
 * The same JSON drives the Python research code (ml/qawam_ml/packs.py) and
 * the app, so the angle the app measures is the angle the evaluation
 * measured. SIDE_* tokens resolve to the chosen leg, OTHER_* to the other.
 */
import squatPackJson from '../../../rules/packs/lower-limb.squat.json';
import { angleDegrees, type Point2D } from '../anglePipeline';

export type Side = 'left' | 'right';
export type AngleTransform = 'interior' | 'flexion' | 'abduction';

export interface PackAngle {
  name: string;
  triplet: [string, string, string];
  transform: AngleTransform;
}

export interface ExercisePack {
  packId: string;
  version: number;
  names: { ar: string; en: string };
  view: string;
  sides: string;
  angles: PackAngle[];
  primaryAngle: string;
  status: string;
  provenance: string;
  approvedBy: string | null;
}

export interface ResolvedAngle {
  name: string;
  landmarks: [string, string, string];
  transform: AngleTransform;
}

/** MediaPipe Pose landmark indices used by the packs. */
export const MEDIAPIPE_INDEX: Readonly<Record<string, number>> = {
  NOSE: 0,
  LEFT_SHOULDER: 11,
  RIGHT_SHOULDER: 12,
  LEFT_ELBOW: 13,
  RIGHT_ELBOW: 14,
  LEFT_WRIST: 15,
  RIGHT_WRIST: 16,
  LEFT_HIP: 23,
  RIGHT_HIP: 24,
  LEFT_KNEE: 25,
  RIGHT_KNEE: 26,
  LEFT_ANKLE: 27,
  RIGHT_ANKLE: 28,
  LEFT_HEEL: 29,
  RIGHT_HEEL: 30,
  LEFT_FOOT_INDEX: 31,
  RIGHT_FOOT_INDEX: 32,
};

export const SQUAT_PACK = squatPackJson as unknown as ExercisePack;

export function concreteLandmark(token: string, side: Side): string {
  const own = side === 'left' ? 'LEFT' : 'RIGHT';
  const other = side === 'left' ? 'RIGHT' : 'LEFT';
  const name = token.startsWith('SIDE_')
    ? `${own}_${token.slice(5)}`
    : token.startsWith('OTHER_')
      ? `${other}_${token.slice(6)}`
      : token;
  if (!(name in MEDIAPIPE_INDEX)) {
    throw new Error(`unknown landmark ${name}`);
  }
  return name;
}

export function resolvePrimaryAngle(pack: ExercisePack, side: Side): ResolvedAngle {
  const angle = pack.angles.find((item) => item.name === pack.primaryAngle);
  if (!angle) {
    throw new Error(`pack ${pack.packId} has no angle ${pack.primaryAngle}`);
  }
  const [a, b, c] = angle.triplet;
  return {
    name: angle.name,
    landmarks: [
      concreteLandmark(a, side),
      concreteLandmark(b, side),
      concreteLandmark(c, side),
    ],
    transform: angle.transform,
  };
}

export function transformAngle(
  interior: number | null,
  transform: AngleTransform,
): number | null {
  if (interior === null) {
    return null;
  }
  if (transform === 'interior') {
    return interior;
  }
  if (transform === 'flexion') {
    return 180 - interior;
  }
  return interior - 90;
}

/** Pack angle from pixel coordinates keyed by landmark name. */
export function packAngle(
  points: Readonly<Record<string, Point2D | undefined>>,
  angle: ResolvedAngle,
): number | null {
  const [a, b, c] = angle.landmarks.map((name) => points[name]);
  if (!a || !b || !c) {
    return null;
  }
  return transformAngle(angleDegrees(a, b, c), angle.transform);
}

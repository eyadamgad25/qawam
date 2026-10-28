import { assessCaptureQuality } from './captureQuality';

export const ARM_RAISE_DEMO = {
  targetRepetitions: 8,
  minimumVisibility: 0.5,
  loweredAngleDegrees: 45,
  raisedAngleDegrees: 120,
} as const;

const SIDES = {
  left: { shoulder: 11, wrist: 15, hip: 23 },
  right: { shoulder: 12, wrist: 16, hip: 24 },
} as const;

export interface PosePoint {
  x: number;
  y: number;
  visibility?: number;
}

export interface ArmRaiseCounterState {
  phase: 'waiting' | 'lowered' | 'raised';
  side: 'left' | 'right' | null;
  repetitions: number;
  angleDegrees: number | null;
  visibility: number | null;
}

export type ArmRaiseSideSelection = 'auto' | 'left' | 'right';

export const INITIAL_ARM_RAISE_STATE: ArmRaiseCounterState = {
  phase: 'waiting',
  side: null,
  repetitions: 0,
  angleDegrees: null,
  visibility: null,
};

export function getArmElevationAngle(
  landmarks: readonly PosePoint[],
  side: 'left' | 'right',
): number | null {
  const mapping = SIDES[side];
  const shoulder = landmarks[mapping.shoulder];
  const wrist = landmarks[mapping.wrist];
  const hip = landmarks[mapping.hip];
  if (
    !shoulder ||
    !wrist ||
    !hip ||
    ![shoulder.x, shoulder.y, wrist.x, wrist.y, hip.x, hip.y].every(Number.isFinite)
  ) {
    return null;
  }

  const torso = { x: hip.x - shoulder.x, y: hip.y - shoulder.y };
  const arm = { x: wrist.x - shoulder.x, y: wrist.y - shoulder.y };
  const torsoLength = Math.hypot(torso.x, torso.y);
  const armLength = Math.hypot(arm.x, arm.y);
  if (torsoLength === 0 || armLength === 0) {
    return null;
  }

  const cosine = (torso.x * arm.x + torso.y * arm.y) / (torsoLength * armLength);
  return (Math.acos(Math.max(-1, Math.min(1, cosine))) * 180) / Math.PI;
}

export function advanceArmRaiseCounter(
  state: ArmRaiseCounterState,
  landmarks: readonly PosePoint[] | undefined,
  sideSelection: ArmRaiseSideSelection = 'auto',
): ArmRaiseCounterState {
  if (!landmarks) {
    return {
      ...state,
      phase: 'waiting',
      side: null,
      angleDegrees: null,
      visibility: null,
    };
  }

  const sides = (Object.keys(SIDES) as Array<'left' | 'right'>)
    .map((side) => {
      const mapping = SIDES[side];
      const shoulder = landmarks[mapping.shoulder];
      const wrist = landmarks[mapping.wrist];
      const hip = landmarks[mapping.hip];
      if (!shoulder || !wrist || !hip) {
        return null;
      }
      const quality = assessCaptureQuality(
        ['shoulder', 'wrist', 'hip'],
        {
          shoulder: shoulder.visibility,
          wrist: wrist.visibility,
          hip: hip.visibility,
        },
        ARM_RAISE_DEMO.minimumVisibility,
      );
      if (quality.status === 'CANNOT_ASSESS') {
        return null;
      }
      const shoulderVisibility = shoulder.visibility;
      const wristVisibility = wrist.visibility;
      const hipVisibility = hip.visibility;
      if (
        shoulderVisibility === undefined ||
        wristVisibility === undefined ||
        hipVisibility === undefined
      ) {
        return null;
      }
      const angle = getArmElevationAngle(landmarks, side);
      if (angle === null) {
        return null;
      }
      const visibility = Math.min(shoulderVisibility, wristVisibility, hipVisibility);
      return { side, angle, visibility };
    })
    .filter((candidate) => candidate !== null)
    .sort((a, b) => b.visibility - a.visibility);

  const selected =
    sideSelection === 'auto'
      ? (sides.find((candidate) => candidate.side === state.side) ?? sides[0])
      : sides.find((candidate) => candidate.side === sideSelection);
  if (!selected) {
    return {
      ...state,
      phase: 'waiting',
      side: null,
      angleDegrees: null,
      visibility: null,
    };
  }
  let phase = state.phase;
  let repetitions = state.repetitions;
  if (state.side !== selected.side) {
    phase =
      selected.angle <= ARM_RAISE_DEMO.loweredAngleDegrees ? 'lowered' : 'waiting';
  } else if (state.phase === 'waiting') {
    phase =
      selected.angle <= ARM_RAISE_DEMO.loweredAngleDegrees ? 'lowered' : 'waiting';
  } else if (
    state.phase === 'lowered' &&
    selected.angle >= ARM_RAISE_DEMO.raisedAngleDegrees
  ) {
    phase = 'raised';
  } else if (
    state.phase === 'raised' &&
    selected.angle <= ARM_RAISE_DEMO.loweredAngleDegrees
  ) {
    phase = 'lowered';
    repetitions += 1;
  }
  return {
    phase,
    side: selected.side,
    repetitions,
    angleDegrees: selected.angle,
    visibility: selected.visibility,
  };
}

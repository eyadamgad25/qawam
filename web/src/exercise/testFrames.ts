/** Synthetic squat skeletons for tests only (never shipped data). */
import type { PoseFrame, PoseLandmark } from './poseFrames';

const W = 720;
const H = 1280;

/**
 * Synthetic squat filmed in portrait: depths are knee flexion targets (deg)
 * for successive reps. shoulderHalfWidth in px controls the view: small =
 * side-on, large = facing the camera.
 */
export function squatClip(
  depths: number[],
  {
    shoulderHalfWidth = 8,
    framesPerRep = 30,
    nearSide = 'left' as 'left' | 'right',
    dropEvery = 0,
    restDeg = 2,
  } = {},
): PoseFrame[] {
  const frames: PoseFrame[] = [];
  const thigh = 220;
  const shank = 220;
  let t = 0;
  const pushFrame = (flexionDeg: number) => {
    const marks: PoseLandmark[] = Array.from({ length: 33 }, () => ({
      x: 0.5,
      y: 0.5,
      visibility: 0.2,
    }));
    const ankle = [360, 1150];
    // shank leans forward, thigh goes back, so the knee angle is 180 - flexion
    const shankTilt = (flexionDeg / 2) * (Math.PI / 180);
    const knee = [
      ankle[0]! + shank * Math.sin(shankTilt),
      ankle[1]! - shank * Math.cos(shankTilt),
    ];
    const thighTilt = shankTilt - (180 - flexionDeg) * (Math.PI / 180);
    const hip = [
      knee[0]! + thigh * Math.sin(thighTilt),
      knee[1]! + thigh * Math.cos(thighTilt),
    ];
    const shoulder = [hip[0]!, hip[1]! - 300];
    for (const side of ['left', 'right'] as const) {
      const dx = side === 'left' ? -shoulderHalfWidth : shoulderHalfWidth;
      const vis = side === nearSide ? 0.95 : 0.6;
      const set = (name: string, p: number[], offset: number) => {
        marks[indexOf(`${side.toUpperCase()}_${name}`)] = {
          x: (p[0]! + offset) / W,
          y: p[1]! / H,
          visibility: vis,
        };
      };
      set('SHOULDER', shoulder, dx);
      set('HIP', hip, dx / 2);
      set('KNEE', knee, dx / 2);
      set('ANKLE', ankle, dx / 2);
    }
    const index = frames.length;
    frames.push({
      timeSeconds: t,
      width: W,
      height: H,
      landmarks: dropEvery && index % dropEvery === 0 ? null : marks,
    });
    t += 1 / 15;
  };
  for (let i = 0; i < 8; i += 1) pushFrame(restDeg);
  for (const depth of depths) {
    for (let f = 0; f < framesPerRep; f += 1) {
      pushFrame(
        restDeg + (depth - restDeg) * Math.sin((Math.PI * f) / (framesPerRep - 1)),
      );
    }
    for (let i = 0; i < 6; i += 1) pushFrame(restDeg);
  }
  return frames;
}

function indexOf(name: string): number {
  const map: Record<string, number> = {
    LEFT_SHOULDER: 11,
    RIGHT_SHOULDER: 12,
    LEFT_HIP: 23,
    RIGHT_HIP: 24,
    LEFT_KNEE: 25,
    RIGHT_KNEE: 26,
    LEFT_ANKLE: 27,
    RIGHT_ANKLE: 28,
  };
  return map[name]!;
}

/**
 * Synthetic front-view abduction: the leg (or arm) on ``movingSide`` swings
 * out to the given angles (deg) for successive reps. ``offsetDeg`` tilts the
 * resting pose, like a camera placed differently.
 */
export function abductionClip(
  limb: 'leg' | 'arm',
  angles: number[],
  {
    movingSide = 'right' as 'left' | 'right',
    shoulderHalfWidth = 110,
    framesPerRep = 30,
    elbowBendDeg = [] as number[],
  } = {},
): PoseFrame[] {
  const frames: PoseFrame[] = [];
  let t = 0;
  const pushFrame = (deg: number, bendDeg = 0) => {
    const marks: PoseLandmark[] = Array.from({ length: 33 }, () => ({
      x: 0.5,
      y: 0.5,
      visibility: 0.2,
    }));
    for (const side of ['left', 'right'] as const) {
      // the person's left appears on the image's right when facing the camera
      const out = side === 'left' ? 1 : -1;
      const shoulder = [360 + out * shoulderHalfWidth, 380];
      const hip = [360 + out * (shoulderHalfWidth * 0.7), 680];
      const raise = side === movingSide ? (deg * Math.PI) / 180 : 0;
      const legLen = 440;
      const ankle =
        limb === 'leg'
          ? [
              hip[0]! + out * legLen * Math.sin(raise),
              hip[1]! + legLen * Math.cos(raise),
            ]
          : [hip[0]!, hip[1]! + legLen];
      const knee = [(hip[0]! + ankle[0]!) / 2, (hip[1]! + ankle[1]!) / 2];
      const armLen = 260;
      const armRaise = limb === 'arm' ? raise : 0;
      const elbow = [
        shoulder[0]! + out * armLen * Math.sin(armRaise),
        shoulder[1]! + armLen * Math.cos(armRaise),
      ];
      const bend = side === movingSide ? (bendDeg * Math.PI) / 180 : 0;
      const wrist = [
        elbow[0]! + out * armLen * Math.sin(armRaise + bend),
        elbow[1]! + armLen * Math.cos(armRaise + bend),
      ];
      const set = (name: string, p: number[]) => {
        marks[MARK[`${side.toUpperCase()}_${name}`]!] = {
          x: p[0]! / W,
          y: p[1]! / H,
          visibility: 0.95,
        };
      };
      set('SHOULDER', shoulder);
      set('HIP', hip);
      set('KNEE', knee);
      set('ANKLE', ankle);
      set('ELBOW', elbow);
      set('WRIST', wrist);
    }
    frames.push({ timeSeconds: t, width: W, height: H, landmarks: marks });
    t += 1 / 15;
  };
  for (let i = 0; i < 8; i += 1) pushFrame(0);
  angles.forEach((angle, rep) => {
    for (let f = 0; f < framesPerRep; f += 1) {
      const phase = Math.sin((Math.PI * f) / (framesPerRep - 1));
      pushFrame(angle * phase, (elbowBendDeg[rep] ?? 0) * phase);
    }
    for (let i = 0; i < 6; i += 1) pushFrame(0);
  });
  return frames;
}

const MARK: Record<string, number> = {
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
};

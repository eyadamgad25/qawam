/**
 * Exercise session from recorded clips: clinic reference clip + home clip ->
 * per-rep feedback. Works for every exercise pack.
 *
 * Safety design (docs/decisions.md 2026-10-29):
 *  - The coach speaks only when the clip is filmed from the view the pack
 *    asks for and a pose was found on most frames; otherwise it says it
 *    cannot see well and how to fix the camera.
 *  - Every rep is compared with the patient's own reference rep, recorded
 *    with the physio. No universal "correct depth" is used.
 *  - Range of motion is measured from the person's own resting angle in each
 *    clip, so a steady camera offset between clinic and home cancels.
 *  - The tolerance is set by the physiotherapist. The default shown in the
 *    prototype is a test value, not a clinical one.
 */
import {
  packAngle,
  packCopy,
  POSTURE_COPY,
  resolveAngles,
  resolvePrimaryAngle,
  type ExercisePack,
  type ResolvedAngle,
  type Side,
} from './exercisePack';
import { percentile, pixelPoints, visibilityOf, type PoseFrame } from './poseFrames';
import { compareRep, type RepComparison } from './referenceCompare';
import { fillGaps, segmentReps, type Rep } from './repSegmentation';
import { checkView, viewAdviceAr, type ViewCheck } from './viewGate';

/** Below this share of frames with a pose, the clip is not assessed (test value). */
export const MIN_DETECTION_RATE = 0.5;
/** Prototype default for the physio-set tolerance; not clinically chosen. */
export const TEST_DEFAULT_TOLERANCE_DEG = 10;

export type SideChoice = Side | 'auto';

export interface ClipAnalysis {
  packId: string;
  side: Side;
  angle: ResolvedAngle;
  frames: number;
  detectionRate: number;
  view: ViewCheck;
  curve: (number | null)[];
  times: number[];
  reps: Rep[];
  /** resting angle of the clip (10th percentile), the zero of range of motion */
  baseDeg: number;
  /** the pack's other (posture) angles, frame by frame */
  secondary: Record<string, (number | null)[]>;
}

export type CannotAssessReason = 'VIEW_MISMATCH' | 'LOW_DETECTION' | 'NO_REPS';

export interface ClipGate {
  ok: boolean;
  reasons: CannotAssessReason[];
  messageAr: string;
}

export type RepCue =
  | 'MATCHES_REFERENCE'
  | 'LESS_THAN_REFERENCE'
  | 'MORE_THAN_REFERENCE'
  | 'DIFFERENT_PATH'
  | 'POSTURE_DIFFERENT';

export interface PostureFinding {
  angle: string;
  /** mean difference from the reference's posture angle over the rep */
  diffDeg: number;
  messageAr: string;
  spokenAr: string;
}

export interface RepFeedback {
  index: number;
  startSeconds: number;
  endSeconds: number;
  comparison: RepComparison;
  cue: RepCue;
  messageAr: string;
  posture: PostureFinding | null;
  /** real angle at the top of the rep, only when the physio entered a goniometer reading */
  calibratedPeakDeg: number | null;
}

export type SessionResult =
  | { status: 'CANNOT_ASSESS'; reasons: CannotAssessReason[]; messageAr: string }
  | { status: 'ASSESSED'; reps: RepFeedback[]; summaryAr: string };

function visibilityScore(frames: readonly PoseFrame[], pack: ExercisePack, side: Side) {
  const angle = resolvePrimaryAngle(pack, side);
  let total = 0;
  for (const frame of frames) {
    total += Math.min(...angle.landmarks.map((name) => visibilityOf(frame, name)));
  }
  return total;
}

function rangeScore(frames: readonly PoseFrame[], pack: ExercisePack, side: Side) {
  const angle = resolvePrimaryAngle(pack, side);
  const values = frames
    .map((frame) => (frame.landmarks ? packAngle(pixelPoints(frame), angle) : null))
    .filter((v): v is number => v !== null);
  const low = percentile(values, 0.1);
  const high = percentile(values, 0.9);
  return low === null || high === null ? 0 : high - low;
}

/**
 * Which side to measure. Two-sided packs (squat): the side nearer the camera.
 * One-sided packs: the limb that moves most (the exercised leg or arm).
 */
export function chooseSide(frames: readonly PoseFrame[], pack: ExercisePack): Side {
  if (pack.sides !== 'both') {
    const left = rangeScore(frames, pack, 'left');
    const right = rangeScore(frames, pack, 'right');
    if (Math.abs(left - right) >= 10) {
      return left > right ? 'left' : 'right';
    }
  }
  return visibilityScore(frames, pack, 'left') >= visibilityScore(frames, pack, 'right')
    ? 'left'
    : 'right';
}

export function analyseClip(
  frames: readonly PoseFrame[],
  pack: ExercisePack,
  side: SideChoice = 'auto',
): ClipAnalysis {
  const chosen = side === 'auto' ? chooseSide(frames, pack) : side;
  const [angle, ...others] = resolveAngles(pack, chosen);
  if (!angle) {
    throw new Error(`pack ${pack.packId} has no angles`);
  }
  const detected = frames.filter((frame) => frame.landmarks !== null);
  const points = frames.map((frame) => (frame.landmarks ? pixelPoints(frame) : null));
  const curve = points.map((p) => (p ? packAngle(p, angle) : null));
  const secondary: Record<string, (number | null)[]> = {};
  for (const other of others) {
    secondary[other.name] = points.map((p) => (p ? packAngle(p, other) : null));
  }
  const finite = curve.filter((v): v is number => v !== null);
  return {
    packId: pack.packId,
    side: chosen,
    angle,
    frames: frames.length,
    detectionRate: frames.length ? detected.length / frames.length : 0,
    view: checkView(detected, pack.view),
    curve,
    times: frames.map((frame) => frame.timeSeconds),
    reps: segmentReps(curve),
    baseDeg: percentile(finite, 0.1) ?? 0,
    secondary,
  };
}

/** A posture angle over frames [start, end], short gaps filled; null if unusable. */
export function sliceCurve(
  values: readonly (number | null)[] | undefined,
  start: number,
  end: number,
): number[] | null {
  if (!values) {
    return null;
  }
  const filled = fillGaps(values.slice(start, end + 1), 5);
  return filled.length >= 2 && filled.every((v) => v !== null && Number.isFinite(v))
    ? (filled as number[])
    : null;
}

/** Least-squares slope of y on x; null when x barely moves. */
export function slope(x: readonly number[], y: readonly number[]): number | null {
  const n = Math.min(x.length, y.length);
  if (n < 3) {
    return null;
  }
  let mx = 0;
  let my = 0;
  for (let i = 0; i < n; i += 1) {
    mx += x[i]!;
    my += y[i]!;
  }
  mx /= n;
  my /= n;
  let sxx = 0;
  let sxy = 0;
  for (let i = 0; i < n; i += 1) {
    sxx += (x[i]! - mx) ** 2;
    sxy += (x[i]! - mx) * (y[i]! - my);
  }
  return sxx / n < 4 ? null : sxy / sxx;
}

/**
 * Compare the pack's posture angles with the reference rep.
 *
 * A deeper squat naturally bends the trunk more, so posture is compared per
 * degree of the main movement: the slope of each posture angle against the
 * main angle, rep vs reference, turned into degrees at the reference's range
 * of motion. A steady offset (camera placement) does not count. Returns the
 * largest difference above the tolerance, or null.
 */
export function postureCheck(
  repPrimary: readonly number[],
  repPosture: Readonly<Record<string, number[] | null>>,
  refPrimary: readonly number[],
  refPosture: Readonly<Record<string, number[] | null>>,
  toleranceDeg: number,
): PostureFinding | null {
  const refRange = Math.max(...refPrimary) - Math.min(...refPrimary);
  let worst: PostureFinding | null = null;
  for (const [name, curve] of Object.entries(repPosture)) {
    const ref = refPosture[name];
    const copy = POSTURE_COPY[name];
    if (!curve || !ref || !copy) {
      continue;
    }
    const repSlope = slope(repPrimary, curve);
    const refSlope = slope(refPrimary, ref);
    if (repSlope === null || refSlope === null) {
      continue;
    }
    const diff = Math.abs(repSlope - refSlope) * refRange;
    if (diff > toleranceDeg && (worst === null || diff > worst.diffDeg)) {
      worst = {
        angle: name,
        diffDeg: diff,
        messageAr: copy.textAr,
        spokenAr: copy.spokenAr,
      };
    }
  }
  return worst;
}

/** A posture problem becomes the cue only when the range itself was fine. */
export function withPosture(cue: RepCue, posture: PostureFinding | null): RepCue {
  return posture && (cue === 'MATCHES_REFERENCE' || cue === 'DIFFERENT_PATH')
    ? 'POSTURE_DIFFERENT'
    : cue;
}

export function gateClip(clip: ClipAnalysis): ClipGate {
  const reasons: CannotAssessReason[] = [];
  if (clip.detectionRate < MIN_DETECTION_RATE) {
    reasons.push('LOW_DETECTION');
  }
  if (clip.view.verdict !== 'MATCHES') {
    reasons.push('VIEW_MISMATCH');
  }
  if (reasons.length === 0 && clip.reps.length === 0) {
    reasons.push('NO_REPS');
  }
  let messageAr = 'زاوية التصوير مناسبة، والجسم ظاهر بوضوح.';
  if (reasons.includes('LOW_DETECTION')) {
    messageAr =
      'لا أرى جسمك في معظم الفيديو: ابتعد عن الكاميرا حتى يظهر جسمك كاملًا، وأضئ المكان.';
  } else if (reasons.includes('VIEW_MISMATCH')) {
    messageAr = viewAdviceAr(clip.view);
  } else if (reasons.includes('NO_REPS')) {
    messageAr = 'لم أجد تكرارًا كاملًا في هذا الفيديو: أدِّ الحركة كاملة ذهابًا وعودة.';
  }
  return { ok: reasons.length === 0, reasons, messageAr };
}

export function cueFor(comparison: RepComparison, toleranceDeg: number): RepCue {
  if (comparison.depthDiffDeg < -toleranceDeg) {
    return 'LESS_THAN_REFERENCE';
  }
  if (comparison.depthDiffDeg > toleranceDeg) {
    return 'MORE_THAN_REFERENCE';
  }
  if (comparison.dtwMeanAbsDeg > toleranceDeg) {
    return 'DIFFERENT_PATH';
  }
  return 'MATCHES_REFERENCE';
}

export function cueText(pack: ExercisePack, cue: RepCue): string {
  const copy = packCopy(pack);
  switch (cue) {
    case 'MATCHES_REFERENCE':
      return 'أحسنت، هذا التكرار قريب من التكرار الذي سجّلته مع أخصائيك.';
    case 'LESS_THAN_REFERENCE':
      return copy.moreAr;
    case 'MORE_THAN_REFERENCE':
      return copy.lessAr;
    case 'POSTURE_DIFFERENT':
      return 'المدى مناسب لكن وضع جسمك مختلف عن المرجع.';
    default:
      return 'المدى مناسب لكن طريقة الحركة مختلفة عن المرجع. تحرّك ببطء وبنفس الطريقة.';
  }
}

export function spokenCue(pack: ExercisePack, cue: RepCue): string {
  const copy = packCopy(pack);
  switch (cue) {
    case 'MATCHES_REFERENCE':
      return 'ممتاز';
    case 'LESS_THAN_REFERENCE':
      return copy.spokenMoreAr;
    case 'MORE_THAN_REFERENCE':
      return copy.spokenLessAr;
    case 'POSTURE_DIFFERENT':
      return 'انتبه لوضع جسمك';
    default:
      return 'تحرّك ببطء وبنفس الطريقة';
  }
}

export function feedbackText(
  pack: ExercisePack,
  cue: RepCue,
  posture: PostureFinding | null,
): string {
  if (cue === 'POSTURE_DIFFERENT' && posture) {
    return posture.messageAr;
  }
  return posture ? `${cueText(pack, cue)} ${posture.messageAr}` : cueText(pack, cue);
}

/** Posture curves of one rep, keyed by angle name. */
export function repPosture(
  clip: ClipAnalysis,
  start: number,
  end: number,
): Record<string, number[] | null> {
  return Object.fromEntries(
    Object.entries(clip.secondary).map(([name, values]) => [
      name,
      sliceCurve(values, start, end),
    ]),
  );
}

export function assessSession(
  pack: ExercisePack,
  reference: ClipAnalysis,
  referenceRepIndex: number,
  home: ClipAnalysis,
  toleranceDeg: number,
  goniometerPeakDeg: number | null = null,
): SessionResult {
  if (!(toleranceDeg > 0) || !Number.isFinite(toleranceDeg)) {
    throw new Error('toleranceDeg must be a positive number');
  }
  const refRep = reference.reps[referenceRepIndex];
  if (!refRep) {
    throw new Error('reference rep not found');
  }
  const gate = gateClip(home);
  if (!gate.ok) {
    return {
      status: 'CANNOT_ASSESS',
      reasons: gate.reasons,
      messageAr: gate.messageAr,
    };
  }
  const refPosture = repPosture(reference, refRep.start, refRep.end);
  const reps = home.reps.map((rep, index): RepFeedback => {
    const comparison = compareRep(
      rep.curve,
      refRep.curve,
      home.baseDeg,
      reference.baseDeg,
    );
    const posture = postureCheck(
      rep.curve,
      repPosture(home, rep.start, rep.end),
      refRep.curve,
      refPosture,
      toleranceDeg,
    );
    const cue = withPosture(cueFor(comparison, toleranceDeg), posture);
    return {
      index,
      startSeconds: home.times[rep.start] ?? 0,
      endSeconds: home.times[rep.end] ?? 0,
      comparison,
      cue,
      posture,
      messageAr: feedbackText(pack, cue, posture),
      calibratedPeakDeg:
        goniometerPeakDeg === null ? null : goniometerPeakDeg + comparison.depthDiffDeg,
    };
  });
  const matches = reps.filter((rep) => rep.cue === 'MATCHES_REFERENCE').length;
  return {
    status: 'ASSESSED',
    reps,
    summaryAr: `${matches} من ${reps.length} تكرارات قريبة من المرجع.`,
  };
}

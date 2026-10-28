/**
 * Squat session: clinic reference clip + home clip -> per-rep feedback.
 *
 * Safety design (docs/decisions.md 2026-10-29):
 *  - The coach speaks only when the clip is filmed from the view the pack
 *    asks for and a pose was found on most frames; otherwise it says it
 *    cannot see well and how to fix the camera.
 *  - Every rep is compared with the patient's own reference rep, recorded
 *    with the physio. No universal "correct depth" is used.
 *  - The tolerance is set by the physiotherapist. The default shown in the
 *    prototype is a test value, not a clinical one.
 */
import {
  packAngle,
  resolvePrimaryAngle,
  type ExercisePack,
  type ResolvedAngle,
  type Side,
} from './exercisePack';
import { pixelPoints, visibilityOf, type PoseFrame } from './poseFrames';
import { compareRep, type RepComparison } from './referenceCompare';
import { segmentReps, type Rep } from './repSegmentation';
import { checkView, viewAdviceAr, type ViewCheck } from './viewGate';

/** Below this share of frames with a pose, the clip is not assessed (test value). */
export const MIN_DETECTION_RATE = 0.5;
/** Prototype default for the physio-set tolerance; not clinically chosen. */
export const TEST_DEFAULT_TOLERANCE_DEG = 10;

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
}

export type CannotAssessReason = 'VIEW_MISMATCH' | 'LOW_DETECTION' | 'NO_REPS';

export interface ClipGate {
  ok: boolean;
  reasons: CannotAssessReason[];
  messageAr: string;
}

export type RepCue =
  | 'MATCHES_REFERENCE'
  | 'SHALLOWER_THAN_REFERENCE'
  | 'DEEPER_THAN_REFERENCE'
  | 'DIFFERENT_PATH';

export interface RepFeedback {
  index: number;
  startSeconds: number;
  endSeconds: number;
  comparison: RepComparison;
  cue: RepCue;
  messageAr: string;
  /** absolute knee flexion at the bottom, only when the physio entered a goniometer reading */
  calibratedPeakDeg: number | null;
}

export type SessionResult =
  | { status: 'CANNOT_ASSESS'; reasons: CannotAssessReason[]; messageAr: string }
  | { status: 'ASSESSED'; reps: RepFeedback[]; summaryAr: string };

/** The leg nearer the camera: higher landmark visibility on the pack's angle. */
export function chooseSide(frames: readonly PoseFrame[], pack: ExercisePack): Side {
  const score = (side: Side) => {
    const angle = resolvePrimaryAngle(pack, side);
    let total = 0;
    for (const frame of frames) {
      total += Math.min(...angle.landmarks.map((name) => visibilityOf(frame, name)));
    }
    return total;
  };
  return score('left') >= score('right') ? 'left' : 'right';
}

export function analyseClip(
  frames: readonly PoseFrame[],
  pack: ExercisePack,
  side?: Side,
): ClipAnalysis {
  const chosen = side ?? chooseSide(frames, pack);
  const angle = resolvePrimaryAngle(pack, chosen);
  const detected = frames.filter((frame) => frame.landmarks !== null);
  const curve = frames.map((frame) =>
    frame.landmarks ? packAngle(pixelPoints(frame), angle) : null,
  );
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
  };
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
      'لا أرى جسمك في معظم الفيديو: ابتعد عن الهاتف حتى يظهر جسمك كاملًا، وأضئ المكان.';
  } else if (reasons.includes('VIEW_MISMATCH')) {
    messageAr = viewAdviceAr(clip.view);
  } else if (reasons.includes('NO_REPS')) {
    messageAr =
      'لم أجد تكرارًا كاملًا في هذا الفيديو: أدِّ التمرين كاملًا نزولًا وصعودًا.';
  }
  return { ok: reasons.length === 0, reasons, messageAr };
}

export function cueFor(comparison: RepComparison, toleranceDeg: number): RepCue {
  if (comparison.depthDiffDeg < -toleranceDeg) {
    return 'SHALLOWER_THAN_REFERENCE';
  }
  if (comparison.depthDiffDeg > toleranceDeg) {
    return 'DEEPER_THAN_REFERENCE';
  }
  if (comparison.dtwMeanAbsDeg > toleranceDeg) {
    return 'DIFFERENT_PATH';
  }
  return 'MATCHES_REFERENCE';
}

export const CUE_TEXT_AR: Readonly<Record<RepCue, string>> = {
  MATCHES_REFERENCE: 'أحسنت، هذا التكرار قريب من التكرار الذي سجّلته مع أخصائيك.',
  SHALLOWER_THAN_REFERENCE:
    'نزولك أقل من التكرار المرجعي. انزل قليلًا أعمق إن لم تشعر بألم.',
  DEEPER_THAN_REFERENCE:
    'نزلت أعمق من التكرار المرجعي. التزم بالعمق الذي حدده أخصائيك.',
  DIFFERENT_PATH:
    'العمق مناسب لكن مسار الحركة مختلف عن المرجع. تحرّك ببطء وبنفس الطريقة.',
};

export function assessSession(
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
  const offset = goniometerPeakDeg === null ? null : goniometerPeakDeg - refRep.peakDeg;
  const reps = home.reps.map((rep, index): RepFeedback => {
    const comparison = compareRep(rep.curve, refRep.curve);
    const cue = cueFor(comparison, toleranceDeg);
    return {
      index,
      startSeconds: home.times[rep.start] ?? 0,
      endSeconds: home.times[rep.end] ?? 0,
      comparison,
      cue,
      messageAr: CUE_TEXT_AR[cue],
      calibratedPeakDeg: offset === null ? null : rep.peakDeg + offset,
    };
  });
  const matches = reps.filter((rep) => rep.cue === 'MATCHES_REFERENCE').length;
  return {
    status: 'ASSESSED',
    reps,
    summaryAr: `${matches} من ${reps.length} تكرارات قريبة من المرجع.`,
  };
}

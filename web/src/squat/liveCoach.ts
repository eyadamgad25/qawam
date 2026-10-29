/**
 * Live camera coaching for the squat: setup check before starting, then
 * per-rep feedback while the patient exercises.
 *
 * Same rules as the recorded-video flow, applied per rep (the research unit):
 * a rep is judged only if the person was detected on most of its frames and
 * filmed from the pack's view; otherwise the coach says it could not see
 * that rep. Rep thresholds come from the patient's reference rep.
 */
import {
  resolvePrimaryAngle,
  packAngle,
  type ExercisePack,
  type Side,
} from './exercisePack';
import { pixelPoints, visibilityOf, type PoseFrame } from './poseFrames';
import { compareRep, type RepComparison } from './referenceCompare';
import {
  chooseSide,
  cueFor,
  CUE_TEXT_AR,
  MIN_DETECTION_RATE,
  type RepCue,
} from './squatSession';
import { checkView, viewAdviceAr } from './viewGate';

export type SetupState = 'NO_PERSON' | 'NOT_FULL_BODY' | 'WRONG_VIEW' | 'READY';

export interface SetupStatus {
  state: SetupState;
  messageAr: string;
  frontalness: number | null;
}

/** Visibility needed on the near-side shoulder, hip, knee and ankle (test value). */
export const MIN_BODY_VISIBILITY = 0.5;
/** Share of the recent frames that must pass the full-body check. */
const MIN_FULL_BODY_SHARE = 0.6;
const BODY_PARTS = ['SHOULDER', 'HIP', 'KNEE', 'ANKLE'] as const;

export function fullBodyVisible(frame: PoseFrame): boolean {
  if (!frame.landmarks) {
    return false;
  }
  return (['LEFT', 'RIGHT'] as const).some((side) =>
    BODY_PARTS.every((part) => {
      const name = `${side}_${part}`;
      if (visibilityOf(frame, name) < MIN_BODY_VISIBILITY) {
        return false;
      }
      const point = pixelPoints(frame)[name];
      return (
        point !== undefined &&
        point[0] >= 0 &&
        point[0] <= frame.width &&
        point[1] >= 0 &&
        point[1] <= frame.height
      );
    }),
  );
}

/** Setup check on the last second or so of camera frames. */
export function setupStatus(
  recent: readonly PoseFrame[],
  pack: ExercisePack,
): SetupStatus {
  const detected = recent.filter((frame) => frame.landmarks !== null);
  if (recent.length === 0 || detected.length < recent.length / 2) {
    return {
      state: 'NO_PERSON',
      messageAr: 'لا أرى أحدًا أمام الكاميرا. قف في مكان مضاء أمام الهاتف.',
      frontalness: null,
    };
  }
  const fullBody = detected.filter(fullBodyVisible).length;
  if (fullBody < detected.length * MIN_FULL_BODY_SHARE) {
    return {
      state: 'NOT_FULL_BODY',
      messageAr: 'ابتعد قليلًا حتى يظهر جسمك كاملًا من الكتفين إلى القدمين.',
      frontalness: null,
    };
  }
  const view = checkView(detected, pack.view);
  if (view.verdict !== 'MATCHES') {
    return {
      state: 'WRONG_VIEW',
      messageAr: viewAdviceAr(view),
      frontalness: view.frontalness,
    };
  }
  return {
    state: 'READY',
    messageAr: 'ممتاز، أراك جيدًا. يمكنك البدء.',
    frontalness: view.frontalness,
  };
}

export interface LiveReference {
  /** the chosen reference rep's knee-flexion curve, same pipeline */
  curve: readonly number[];
}

export type LiveRepFeedback =
  | {
      index: number;
      assessed: true;
      cue: RepCue;
      comparison: RepComparison;
      messageAr: string;
    }
  | {
      index: number;
      assessed: false;
      reason: 'VIEW_MISMATCH' | 'LOW_DETECTION';
      messageAr: string;
    };

export interface LiveUpdate {
  angleDeg: number | null;
  side: Side;
  inRep: boolean;
  newRep: LiveRepFeedback | null;
}

/** Hold the last angle over a few missed frames instead of breaking the rep. */
const MAX_HELD_FRAMES = 5;
const SMOOTHING = 3;
const MIN_REP_FRAMES = 5;
const SIDE_LOCK_FRAMES = 15;

export class LiveSquatCoach {
  readonly enterDeg: number;
  readonly exitDeg: number;
  private readonly frames: PoseFrame[] = [];
  private readonly raw: number[] = [];
  private readonly smoothed: number[] = [];
  private side: Side | null = null;
  private held = 0;
  private lastLow: number | null = null;
  private start: number | null = null;
  private readonly feedback: LiveRepFeedback[] = [];

  constructor(
    private readonly pack: ExercisePack,
    private readonly reference: LiveReference,
    private readonly toleranceDeg: number,
  ) {
    if (reference.curve.length < 2) {
      throw new Error('reference rep is too short');
    }
    if (!(toleranceDeg > 0)) {
      throw new Error('toleranceDeg must be a positive number');
    }
    const low = Math.min(...reference.curve);
    const peak = Math.max(...reference.curve);
    if (peak - low < 10) {
      throw new Error('reference rep has almost no movement');
    }
    this.enterDeg = low + 0.5 * (peak - low);
    this.exitDeg = low + 0.2 * (peak - low);
  }

  get reps(): readonly LiveRepFeedback[] {
    return this.feedback;
  }

  push(frame: PoseFrame): LiveUpdate {
    this.frames.push(frame);
    if (this.side === null && this.frames.length >= SIDE_LOCK_FRAMES) {
      this.side = chooseSide(this.frames, this.pack);
    }
    const side = this.side ?? chooseSide(this.frames, this.pack);
    const angle = frame.landmarks
      ? packAngle(pixelPoints(frame), resolvePrimaryAngle(this.pack, side))
      : null;

    let value: number | null = angle;
    if (value === null) {
      this.held += 1;
      value = this.held <= MAX_HELD_FRAMES ? (this.raw.at(-1) ?? null) : null;
    } else {
      this.held = 0;
    }
    if (value === null) {
      // long gap: drop any rep in progress
      this.start = null;
      this.lastLow = null;
      this.raw.push(Number.NaN);
      this.smoothed.push(Number.NaN);
      return { angleDeg: null, side, inRep: false, newRep: null };
    }
    this.raw.push(value);
    const window = this.raw.slice(-SMOOTHING).filter(Number.isFinite);
    const smooth = window.reduce((sum, v) => sum + v, 0) / window.length;
    this.smoothed.push(smooth);
    const i = this.smoothed.length - 1;

    let newRep: LiveRepFeedback | null = null;
    if (this.start === null) {
      if (smooth <= this.exitDeg) {
        this.lastLow = i;
      } else if (smooth >= this.enterDeg && this.lastLow !== null) {
        this.start = this.lastLow;
      }
    } else if (smooth <= this.exitDeg) {
      if (i - this.start + 1 >= MIN_REP_FRAMES) {
        newRep = this.judge(this.start, i);
        this.feedback.push(newRep);
      }
      this.start = null;
      this.lastLow = i;
    }
    return { angleDeg: angle, side, inRep: this.start !== null, newRep };
  }

  private judge(start: number, end: number): LiveRepFeedback {
    const index = this.feedback.length;
    const frames = this.frames.slice(start, end + 1);
    const detected = frames.filter((frame) => frame.landmarks !== null);
    if (detected.length < frames.length * MIN_DETECTION_RATE) {
      return {
        index,
        assessed: false,
        reason: 'LOW_DETECTION',
        messageAr: 'لم أرك بوضوح في هذا التكرار، فلن أقيّمه.',
      };
    }
    const view = checkView(detected, this.pack.view);
    if (view.verdict !== 'MATCHES') {
      return {
        index,
        assessed: false,
        reason: 'VIEW_MISMATCH',
        messageAr: `لم أقيّم هذا التكرار. ${viewAdviceAr(view)}`,
      };
    }
    const curve = this.smoothed.slice(start, end + 1);
    const comparison = compareRep(curve, this.reference.curve);
    const cue = cueFor(comparison, this.toleranceDeg);
    return { index, assessed: true, cue, comparison, messageAr: CUE_TEXT_AR[cue] };
  }
}

/** Short spoken version of a cue, for the voice coach. */
export const SPOKEN_CUE_AR: Readonly<Record<RepCue, string>> = {
  MATCHES_REFERENCE: 'ممتاز',
  SHALLOWER_THAN_REFERENCE: 'انزل أعمق قليلًا',
  DEEPER_THAN_REFERENCE: 'لا تنزل أعمق من المرجع',
  DIFFERENT_PATH: 'تحرك ببطء وبنفس الطريقة',
};

export function spokenText(rep: LiveRepFeedback): string {
  return rep.assessed ? SPOKEN_CUE_AR[rep.cue] : 'لم أرك جيدًا';
}

/** Speak Arabic text if the browser can; silently does nothing otherwise. */
export function speakAr(text: string): void {
  try {
    const synth = globalThis.speechSynthesis;
    if (!synth || typeof SpeechSynthesisUtterance === 'undefined') {
      return;
    }
    const utterance = new SpeechSynthesisUtterance(text);
    const voice = synth.getVoices().find((v) => v.lang.toLowerCase().startsWith('ar'));
    utterance.lang = voice?.lang ?? 'ar-EG';
    if (voice) {
      utterance.voice = voice;
    }
    synth.cancel();
    synth.speak(utterance);
  } catch {
    // voice is optional
  }
}

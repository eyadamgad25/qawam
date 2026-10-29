/**
 * Live camera coaching for any exercise pack: a setup check before starting,
 * then counting and per-rep feedback while the patient exercises.
 *
 * Counting is relative to the person's own resting angle in this session
 * (tracked while they are between reps) and the range of motion of their
 * reference rep, so a different camera height or distance at home does not
 * stop reps from being counted. Each rep is judged only if the person was
 * detected on most of its frames and filmed from the pack's view (the
 * research unit is the rep); otherwise the coach says it could not see it.
 */
import {
  packAngle,
  packCopy,
  requiredLandmarks,
  resolveAngles,
  type ExercisePack,
  type Side,
} from './exercisePack';
import { pixelPoints, visibilityOf, type PoseFrame } from './poseFrames';
import { compareRep, type RepComparison } from './referenceCompare';
import {
  chooseSide,
  cueFor,
  feedbackText,
  MIN_DETECTION_RATE,
  postureCheck,
  sliceCurve,
  spokenCue,
  withPosture,
  type PostureFinding,
  type RepCue,
} from './session';
import { checkView, viewAdviceAr } from './viewGate';

// ------------------------------------------------------------------ setup

export type SetupState = 'NO_PERSON' | 'NOT_FULL_BODY' | 'WRONG_VIEW' | 'READY';

export interface SetupStatus {
  state: SetupState;
  messageAr: string;
  /** short sentence for the voice coach */
  spokenAr: string;
  frontalness: number | null;
  /** body parts not seen well, e.g. ANKLE */
  missingParts: string[];
}

/** Landmark visibility counted as "seen" for the setup check (test value). */
export const MIN_BODY_VISIBILITY = 0.35;
/** Share of the recent frames that must pass the full-body check. */
const MIN_FULL_BODY_SHARE = 0.6;
/** Landmarks this close to the image edge count as cut off (share of size). */
const EDGE_MARGIN = 0.01;

export const PART_AR: Readonly<Record<string, string>> = {
  SHOULDER: 'كتفيك',
  ELBOW: 'كوعك',
  WRIST: 'يدك',
  HIP: 'وركك',
  KNEE: 'ركبتيك',
  ANKLE: 'قدميك',
};

function landmarkSeen(frame: PoseFrame, name: string): boolean {
  if (visibilityOf(frame, name) < MIN_BODY_VISIBILITY) {
    return false;
  }
  const point = pixelPoints(frame)[name];
  if (!point) {
    return false;
  }
  const mx = frame.width * EDGE_MARGIN;
  const my = frame.height * EDGE_MARGIN;
  return (
    point[0] >= mx &&
    point[0] <= frame.width - mx &&
    point[1] >= my &&
    point[1] <= frame.height - my
  );
}

/** Missing body parts (SHOULDER, ANKLE, ...) on the better-seen side. */
export function missingParts(frame: PoseFrame, pack: ExercisePack): string[] {
  if (!frame.landmarks) {
    return ['SHOULDER', 'HIP'];
  }
  const missingFor = (side: Side) =>
    requiredLandmarks(pack, side)
      .filter((name) => !landmarkSeen(frame, name))
      .map((name) => name.replace(/^(LEFT|RIGHT)_/, ''));
  const left = missingFor('left');
  const right = missingFor('right');
  return [...new Set(left.length <= right.length ? left : right)];
}

function placementHint(parts: readonly string[]): string {
  if (parts.some((p) => p === 'ANKLE' || p === 'KNEE')) {
    return 'ابتعد عن الكاميرا أو اخفضها قليلًا حتى تظهر قدماك.';
  }
  if (parts.some((p) => p === 'WRIST' || p === 'ELBOW')) {
    return 'ابتعد عن الكاميرا حتى تظهر ذراعاك كاملتين.';
  }
  return 'ابتعد قليلًا حتى يظهر جسمك كاملًا.';
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
      messageAr: 'لا أرى أحدًا أمام الكاميرا. قف في مكان مضاء أمامها.',
      spokenAr: 'قف أمام الكاميرا',
      frontalness: null,
      missingParts: [],
    };
  }
  const counts = new Map<string, number>();
  let fullBody = 0;
  for (const frame of detected) {
    const missing = missingParts(frame, pack);
    if (missing.length === 0) {
      fullBody += 1;
    }
    for (const part of missing) {
      counts.set(part, (counts.get(part) ?? 0) + 1);
    }
  }
  if (fullBody < detected.length * MIN_FULL_BODY_SHARE) {
    const parts = [...counts.entries()]
      .filter(([, n]) => n >= detected.length * (1 - MIN_FULL_BODY_SHARE))
      .sort((a, b) => b[1] - a[1])
      .map(([part]) => part);
    const names = parts.map((part) => PART_AR[part] ?? part).join(' و');
    return {
      state: 'NOT_FULL_BODY',
      messageAr: `لا أرى ${names || 'جسمك كاملًا'} بوضوح. ${placementHint(parts)}`,
      spokenAr: `لا أرى ${names || 'جسمك كاملًا'}`,
      frontalness: null,
      missingParts: parts,
    };
  }
  const view = checkView(detected, pack.view);
  if (view.verdict !== 'MATCHES') {
    const advice = viewAdviceAr(view);
    return {
      state: 'WRONG_VIEW',
      messageAr: advice,
      spokenAr: pack.view === 'side' ? 'استدر للجنب' : 'واجه الكاميرا',
      frontalness: view.frontalness,
      missingParts: [],
    };
  }
  return {
    state: 'READY',
    messageAr: 'ممتاز، أراك جيدًا.',
    spokenAr: 'ممتاز، أراك جيدًا',
    frontalness: view.frontalness,
    missingParts: [],
  };
}

// ------------------------------------------------------------- live coach

export interface LiveReference {
  /** the chosen reference rep's angle curve, same pipeline */
  curve: readonly number[];
  /** resting angle of the reference recording */
  baseDeg: number;
  /** rep duration in seconds, for the tempo note */
  durationSeconds: number;
  /** side measured in the reference */
  side: Side;
  /** the reference rep's posture angles (pack's secondary angles) */
  posture: Readonly<Record<string, number[] | null>>;
}

export type LiveRepFeedback =
  | {
      index: number;
      assessed: true;
      cue: RepCue;
      comparison: RepComparison;
      posture: PostureFinding | null;
      messageAr: string;
      spokenAr: string;
      tempoNoteAr: string | null;
      curve: number[];
    }
  | {
      index: number;
      assessed: false;
      reason: 'VIEW_MISMATCH' | 'LOW_DETECTION';
      messageAr: string;
      spokenAr: string;
    };

export interface LiveUpdate {
  angleDeg: number | null;
  side: Side;
  inRep: boolean;
  /** 0 at rest, 1 at the reference rep's range of motion */
  progress: number | null;
  baseDeg: number | null;
  newRep: LiveRepFeedback | null;
}

/** Hold the last angle over a few missed frames instead of breaking the rep. */
const MAX_HELD_FRAMES = 5;
const SMOOTHING = 3;
const MIN_REP_FRAMES = 4;
const MIN_REP_SECONDS = 0.4;
const SIDE_LOCK_FRAMES = 15;
/** Frames used to track the resting angle between reps. */
const BASELINE_WINDOW = 45;
/** Rep starts past this share of the reference range, ends back below EXIT. */
export const ENTER_FRACTION = 0.3;
export const EXIT_FRACTION = 0.15;

const ARABIC_NUMBERS = [
  'صفر',
  'واحد',
  'اثنان',
  'ثلاثة',
  'أربعة',
  'خمسة',
  'ستة',
  'سبعة',
  'ثمانية',
  'تسعة',
  'عشرة',
  'أحد عشر',
  'اثنا عشر',
  'ثلاثة عشر',
  'أربعة عشر',
  'خمسة عشر',
  'ستة عشر',
  'سبعة عشر',
  'ثمانية عشر',
  'تسعة عشر',
  'عشرون',
];

export function arabicNumberWord(n: number): string {
  return ARABIC_NUMBERS[n] ?? String(n);
}

export class LiveCoach {
  readonly referenceRangeDeg: number;
  private readonly frames: PoseFrame[] = [];
  private readonly raw: number[] = [];
  private readonly secondary: Record<string, (number | null)[]> = {};
  private readonly smoothed: number[] = [];
  private side: Side | null;
  private held = 0;
  private baseline: number | null = null;
  private lastLow: number | null = null;
  private start: number | null = null;
  private repBase = 0;
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
    this.referenceRangeDeg = Math.max(...reference.curve) - reference.baseDeg;
    if (this.referenceRangeDeg < 10) {
      throw new Error('reference rep has almost no movement');
    }
    // one-sided exercises: measure the limb the physio recorded
    this.side = pack.sides === 'both' ? null : reference.side;
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
    const points = frame.landmarks ? pixelPoints(frame) : null;
    const [primary, ...others] = resolveAngles(this.pack, side);
    const angle = points && primary ? packAngle(points, primary) : null;
    for (const other of others) {
      (this.secondary[other.name] ??= []).push(
        points ? packAngle(points, other) : null,
      );
    }

    let value: number | null = angle;
    if (value === null) {
      this.held += 1;
      const last = this.raw.at(-1);
      value =
        this.held <= MAX_HELD_FRAMES && last !== undefined && Number.isFinite(last)
          ? last
          : null;
    } else {
      this.held = 0;
    }
    if (value === null) {
      // long gap: drop any rep in progress
      this.start = null;
      this.lastLow = null;
      this.raw.push(Number.NaN);
      this.smoothed.push(Number.NaN);
      return {
        angleDeg: null,
        side,
        inRep: false,
        progress: null,
        baseDeg: this.baseline,
        newRep: null,
      };
    }
    this.raw.push(value);
    const window = this.raw.slice(-SMOOTHING).filter(Number.isFinite);
    const smooth = window.reduce((sum, v) => sum + v, 0) / window.length;
    this.smoothed.push(smooth);
    const i = this.smoothed.length - 1;

    if (this.start === null) {
      const recent = this.smoothed.slice(-BASELINE_WINDOW).filter(Number.isFinite);
      this.baseline = Math.min(...recent);
    }
    const base = this.start === null ? (this.baseline ?? smooth) : this.repBase;
    const enter = base + ENTER_FRACTION * this.referenceRangeDeg;
    const exit = base + EXIT_FRACTION * this.referenceRangeDeg;

    let newRep: LiveRepFeedback | null = null;
    if (this.start === null) {
      if (smooth <= exit) {
        this.lastLow = i;
      } else if (smooth >= enter && this.lastLow !== null) {
        this.start = this.lastLow;
        this.repBase = base;
      }
    } else if (smooth <= exit) {
      const seconds = this.durationSeconds(this.start, i);
      if (i - this.start + 1 >= MIN_REP_FRAMES && seconds >= MIN_REP_SECONDS) {
        newRep = this.judge(this.start, i, seconds);
        this.feedback.push(newRep);
      }
      this.start = null;
      this.lastLow = i;
    }
    return {
      angleDeg: angle,
      side,
      inRep: this.start !== null,
      progress: (smooth - base) / this.referenceRangeDeg,
      baseDeg: base,
      newRep,
    };
  }

  private durationSeconds(start: number, end: number): number {
    const a = this.frames[start]?.timeSeconds ?? 0;
    const b = this.frames[end]?.timeSeconds ?? 0;
    return b - a;
  }

  private judge(start: number, end: number, seconds: number): LiveRepFeedback {
    const index = this.feedback.length;
    const number = arabicNumberWord(index + 1);
    const frames = this.frames.slice(start, end + 1);
    const detected = frames.filter((frame) => frame.landmarks !== null);
    if (detected.length < frames.length * MIN_DETECTION_RATE) {
      return {
        index,
        assessed: false,
        reason: 'LOW_DETECTION',
        messageAr: 'لم أرك بوضوح في هذا التكرار، فلن أقيّمه.',
        spokenAr: `${number}، لم أرك جيدًا`,
      };
    }
    const view = checkView(detected, this.pack.view);
    if (view.verdict !== 'MATCHES') {
      return {
        index,
        assessed: false,
        reason: 'VIEW_MISMATCH',
        messageAr: `لم أقيّم هذا التكرار. ${viewAdviceAr(view)}`,
        spokenAr: `${number}، ${this.pack.view === 'side' ? 'استدر للجنب' : 'واجه الكاميرا'}`,
      };
    }
    const curve = this.smoothed.slice(start, end + 1);
    const comparison = compareRep(
      curve,
      this.reference.curve,
      this.repBase,
      this.reference.baseDeg,
    );
    const posture = postureCheck(
      curve,
      Object.fromEntries(
        Object.entries(this.secondary).map(([name, values]) => [
          name,
          sliceCurve(values, start, end),
        ]),
      ),
      this.reference.curve,
      this.reference.posture,
      this.toleranceDeg,
    );
    const cue = withPosture(cueFor(comparison, this.toleranceDeg), posture);
    const tempo =
      this.reference.durationSeconds > 0 ? seconds / this.reference.durationSeconds : 1;
    const tempoNoteAr =
      tempo < 0.5 ? 'كان هذا التكرار أسرع بكثير من المرجع. أبطئ.' : null;
    const spoken =
      cue === 'MATCHES_REFERENCE' && tempoNoteAr
        ? 'أبطئ قليلًا'
        : cue === 'POSTURE_DIFFERENT' && posture
          ? posture.spokenAr
          : spokenCue(this.pack, cue);
    return {
      index,
      assessed: true,
      cue,
      comparison,
      posture,
      messageAr: feedbackText(this.pack, cue, posture),
      spokenAr: `${number}، ${spoken}`,
      tempoNoteAr,
      curve,
    };
  }
}

export interface SessionSummary {
  reps: number;
  assessed: number;
  matches: number;
  meanRangeDiffDeg: number | null;
  textAr: string;
  spokenAr: string;
}

export function summarise(
  reps: readonly LiveRepFeedback[],
  pack: ExercisePack,
): SessionSummary {
  const assessed = reps.filter((rep) => rep.assessed);
  const matches = assessed.filter((rep) => rep.cue === 'MATCHES_REFERENCE').length;
  const less = assessed.filter((rep) => rep.cue === 'LESS_THAN_REFERENCE').length;
  const more = assessed.filter((rep) => rep.cue === 'MORE_THAN_REFERENCE').length;
  const mean = assessed.length
    ? assessed.reduce((sum, rep) => sum + rep.comparison.depthDiffDeg, 0) /
      assessed.length
    : null;
  if (reps.length === 0) {
    return {
      reps: 0,
      assessed: 0,
      matches: 0,
      meanRangeDiffDeg: null,
      textAr: 'لم أحسب أي تكرار. تأكد أنك تؤدي الحركة كاملة وأن الكاميرا تراك.',
      spokenAr: 'لم أحسب أي تكرار',
    };
  }
  const copy = packCopy(pack);
  const postureIssues = assessed.filter((rep) => rep.posture !== null);
  let advice = 'أداء قريب من المرجع، استمر هكذا.';
  if (postureIssues.length > matches && postureIssues.length >= Math.max(less, more)) {
    advice = postureIssues[0]!.posture!.messageAr;
  } else if (less > matches && less >= more) {
    advice = copy.moreAr;
  } else if (more > matches) {
    advice = copy.lessAr;
  } else if (assessed.length < reps.length / 2) {
    advice = 'لم أستطع تقييم معظم التكرارات. عدّل مكان الكاميرا قبل المرة القادمة.';
  }
  return {
    reps: reps.length,
    assessed: assessed.length,
    matches,
    meanRangeDiffDeg: mean,
    textAr: `أنهيت ${reps.length} تكرارات، قيّمت منها ${assessed.length}، و${matches} قريبة من المرجع. ${advice}`,
    spokenAr: `انتهى التمرين. عدد التكرارات ${reps.length}، والقريبة من المرجع ${matches}`,
  };
}

// ------------------------------------------------------------------ voice

/** Speak Arabic text if the browser can; silently does nothing otherwise. */
export function speakAr(text: string, interrupt = true): void {
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
    utterance.rate = 1.05;
    if (interrupt) {
      synth.cancel();
    }
    synth.speak(utterance);
  } catch {
    // voice is optional
  }
}

/** True when the browser has an Arabic voice installed. */
export function hasArabicVoice(): boolean {
  try {
    return (globalThis.speechSynthesis?.getVoices() ?? []).some((v) =>
      v.lang.toLowerCase().startsWith('ar'),
    );
  } catch {
    return false;
  }
}

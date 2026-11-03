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
import { getLang, tr } from '../i18n';
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

const PART_EN: Readonly<Record<string, string>> = {
  SHOULDER: 'your shoulders',
  ELBOW: 'your elbow',
  WRIST: 'your hand',
  HIP: 'your hip',
  KNEE: 'your knees',
  ANKLE: 'your feet',
};

function partName(part: string): string {
  return tr(PART_AR[part] ?? part, PART_EN[part] ?? part.toLowerCase());
}

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

/**
 * The joint of the measured (primary) angle that was seen least during a rep,
 * or null when every joint was seen in enough frames. "Seen" is the setup
 * check's rule (visibility and not cut off at the image edge), so no new
 * threshold is introduced. Returned as a body part, e.g. ANKLE.
 */
export function hiddenJoint(
  frames: readonly PoseFrame[],
  pack: ExercisePack,
  side: Side,
): string | null {
  const [primary] = resolveAngles(pack, side);
  if (!primary || frames.length === 0) {
    return null;
  }
  let worst: { name: string; seen: number } | null = null;
  for (const name of primary.landmarks) {
    const seen = frames.filter(
      (f) => f.landmarks !== null && landmarkSeen(f, name),
    ).length;
    if (worst === null || seen < worst.seen) {
      worst = { name, seen };
    }
  }
  return worst !== null && worst.seen < frames.length * MIN_DETECTION_RATE
    ? worst.name.replace(/^(LEFT|RIGHT)_/, '')
    : null;
}

function placementHint(parts: readonly string[]): string {
  if (parts.some((p) => p === 'ANKLE' || p === 'KNEE')) {
    return tr(
      'ابتعد عن الكاميرا أو اخفضها قليلًا حتى تظهر قدماك.',
      'Step back or lower the camera a little until your feet show.',
    );
  }
  if (parts.some((p) => p === 'WRIST' || p === 'ELBOW')) {
    return tr(
      'ابتعد عن الكاميرا حتى تظهر ذراعاك كاملتين.',
      'Step back until both arms show fully.',
    );
  }
  return tr(
    'ابتعد قليلًا حتى يظهر جسمك كاملًا.',
    'Step back a little until your whole body shows.',
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
      messageAr: tr(
        'لا أرى أحدًا أمام الكاميرا. قف في مكان مضاء أمامها.',
        'I cannot see anyone. Stand in a well-lit spot in front of the camera.',
      ),
      spokenAr: tr('قف أمام الكاميرا', 'Stand in front of the camera'),
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
    const names = parts.map(partName).join(tr(' و', ' and '));
    return {
      state: 'NOT_FULL_BODY',
      messageAr: tr(
        `لا أرى ${names || 'جسمك كاملًا'} بوضوح. ${placementHint(parts)}`,
        `I cannot see ${names || 'your whole body'} clearly. ${placementHint(parts)}`,
      ),
      spokenAr: tr(
        `لا أرى ${names || 'جسمك كاملًا'}`,
        `I cannot see ${names || 'your whole body'}`,
      ),
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
      spokenAr:
        pack.view === 'side'
          ? tr('استدر للجنب', 'Turn sideways')
          : tr('واجه الكاميرا', 'Face the camera'),
      frontalness: view.frontalness,
      missingParts: [],
    };
  }
  return {
    state: 'READY',
    messageAr: tr('ممتاز، أراك جيدًا.', 'Great, I can see you well.'),
    spokenAr: tr('ممتاز، أراك جيدًا', 'Great, I can see you well'),
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
      /**
       * LOW_DETECTION: no person in too many frames; JOINTS_HIDDEN: a joint of
       * the measured angle was hidden or cut off in too many frames (the view
       * can be right while the angle is still guessed); VIEW_MISMATCH: wrong
       * camera angle for this exercise; NOT_CERTIFIED: the pack counts reps
       * only (correctionCues false).
       */
      reason: 'VIEW_MISMATCH' | 'LOW_DETECTION' | 'JOINTS_HIDDEN' | 'NOT_CERTIFIED';
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

/** Rep number as spoken in the current language (English voices read digits). */
export function spokenNumber(n: number): string {
  return getLang() === 'en' ? String(n) : arabicNumberWord(n);
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
    const number = spokenNumber(index + 1);
    const frames = this.frames.slice(start, end + 1);
    const detected = frames.filter((frame) => frame.landmarks !== null);
    if (detected.length < frames.length * MIN_DETECTION_RATE) {
      return {
        index,
        assessed: false,
        reason: 'LOW_DETECTION',
        messageAr: tr(
          'لم أرك بوضوح في هذا التكرار، فلن أقيّمه.',
          'I did not see you clearly in this rep, so I will not judge it.',
        ),
        spokenAr: tr(`${number}، لم أرك جيدًا`, `${number}, I did not see you well`),
      };
    }
    const hidden = hiddenJoint(
      detected,
      this.pack,
      this.side ?? chooseSide(this.frames, this.pack),
    );
    if (hidden !== null) {
      const part = partName(hidden);
      return {
        index,
        assessed: false,
        reason: 'JOINTS_HIDDEN',
        messageAr: tr(
          `لم أرَ ${part} بوضوح في هذا التكرار، فلن أقيّمه.`,
          `I did not see ${part} clearly in this rep, so I will not judge it.`,
        ),
        spokenAr: tr(`${number}، لم أرَ ${part}`, `${number}, I did not see ${part}`),
      };
    }
    const view = checkView(detected, this.pack.view);
    if (view.verdict !== 'MATCHES') {
      return {
        index,
        assessed: false,
        reason: 'VIEW_MISMATCH',
        messageAr: tr(
          `لم أقيّم هذا التكرار. ${viewAdviceAr(view)}`,
          `I did not judge this rep. ${viewAdviceAr(view)}`,
        ),
        spokenAr: tr(
          `${number}، ${this.pack.view === 'side' ? 'استدر للجنب' : 'واجه الكاميرا'}`,
          `${number}, ${this.pack.view === 'side' ? 'turn sideways' : 'face the camera'}`,
        ),
      };
    }
    if (this.pack.correctionCues === false) {
      return {
        index,
        assessed: false,
        reason: 'NOT_CERTIFIED',
        messageAr: tr(
          'حسبت هذا التكرار. لا أصحّح هذا التمرين بعد.',
          'I counted this rep. I do not correct this exercise yet.',
        ),
        spokenAr: number,
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
      tempo < 0.5
        ? tr(
            'كان هذا التكرار أسرع بكثير من المرجع. أبطئ.',
            'This rep was much faster than the reference. Slow down.',
          )
        : null;
    const spoken =
      cue === 'MATCHES_REFERENCE' && tempoNoteAr
        ? tr('أبطئ قليلًا', 'Slow down a little')
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
      spokenAr: tr(`${number}، ${spoken}`, `${number}, ${spoken}`),
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
      textAr: tr(
        'لم أحسب أي تكرار. تأكد أنك تؤدي الحركة كاملة وأن الكاميرا تراك.',
        'I did not count any rep. Make sure you do the full movement and the camera can see you.',
      ),
      spokenAr: tr('لم أحسب أي تكرار', 'I did not count any rep'),
    };
  }
  const copy = packCopy(pack);
  const postureIssues = assessed.filter((rep) => rep.posture !== null);
  let advice = tr(
    'أداء قريب من المرجع، استمر هكذا.',
    'Close to your reference, keep it up.',
  );
  if (pack.correctionCues === false) {
    advice = copy.evidenceAr;
  } else if (
    postureIssues.length > matches &&
    postureIssues.length >= Math.max(less, more)
  ) {
    advice = postureIssues[0]!.posture!.messageAr;
  } else if (less > matches && less >= more) {
    advice = copy.moreAr;
  } else if (more > matches) {
    advice = copy.lessAr;
  } else if (assessed.length < reps.length / 2) {
    advice = tr(
      'لم أستطع تقييم معظم التكرارات. عدّل مكان الكاميرا قبل المرة القادمة.',
      'I could not judge most reps. Move the camera before next time.',
    );
  }
  return {
    reps: reps.length,
    assessed: assessed.length,
    matches,
    meanRangeDiffDeg: mean,
    textAr: tr(
      `أنهيت ${reps.length} تكرارات، قيّمت منها ${assessed.length}، و${matches} قريبة من المرجع. ${advice}`,
      `You did ${reps.length} reps; I judged ${assessed.length}, and ${matches} were close to the reference. ${advice}`,
    ),
    spokenAr: tr(
      `انتهى التمرين. عدد التكرارات ${reps.length}، والقريبة من المرجع ${matches}`,
      `Exercise finished. ${reps.length} reps, ${matches} close to the reference`,
    ),
  };
}

// ------------------------------------------------------------------ voice

/** Speak text in the current language if the browser can; silently does nothing otherwise. */
export function speakAr(text: string, interrupt = true): void {
  try {
    const synth = globalThis.speechSynthesis;
    if (!synth || typeof SpeechSynthesisUtterance === 'undefined') {
      return;
    }
    const lang = getLang();
    const utterance = new SpeechSynthesisUtterance(text);
    const voice = synth.getVoices().find((v) => v.lang.toLowerCase().startsWith(lang));
    utterance.lang = voice?.lang ?? (lang === 'en' ? 'en-US' : 'ar-EG');
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

/** True when the browser has a voice installed for the current language. */
export function hasVoiceForLanguage(): boolean {
  try {
    const lang = getLang();
    return (globalThis.speechSynthesis?.getVoices() ?? []).some((v) =>
      v.lang.toLowerCase().startsWith(lang),
    );
  } catch {
    return false;
  }
}

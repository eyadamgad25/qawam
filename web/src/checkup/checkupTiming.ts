/**
 * Check-up tests timed from body points: five-times sit-to-stand (sts5), 30-second sit-to-stand (sts30) and
 * Timed Up and Go (tug). Spec: docs/superpowers/specs/2026-11-26-checkup-test-mode-design.md.
 *
 * Pure function of the frames, run once when the test ends, so the app and the evaluation on public data use
 * exactly the same code (ml/eval/checkup_batch.ts). The signal is the hip's height above the ankle divided by
 * the leg's length: about 1 standing, about 0.5 seated, whatever the person's size or distance.
 */
import {
  percentile,
  pixelPoints,
  visibilityOf,
  type PoseFrame,
} from '../exercise/poseFrames';
import { movingAverage } from '../exercise/repSegmentation';

export type CheckupKind = 'sts5' | 'sts30' | 'tug';
export type NoResultReason =
  'person-missing' | 'no-movement' | 'too-few-stands' | 'not-seated' | 'no-walk';

export type CheckupResult =
  | {
      ok: true;
      kind: CheckupKind;
      /** sts5 and tug: seconds from start to seated again */
      seconds?: number;
      /** sts30: full stand-ups within 30 s */
      count?: number;
      startS: number;
      endS: number;
      standUps: number[];
      sitDowns: number[];
    }
  | { ok: false; kind: CheckupKind; reason: NoResultReason };

export const MIN_VISIBILITY = 0.35;
/** Share of frames that must show the hip, knee and ankle. */
export const MIN_SEEN = 0.7;
/** Smallest seated-to-standing change, in leg lengths, that counts as movement. */
export const MIN_RANGE = 0.15;
const UP = 0.65;
const DOWN = 0.35;
const SEATED = 0.2;
const FIRST_MOVE = 0.1;
const SMOOTH_SECONDS = 0.2;
const STS30_SECONDS = 30;
/** Hips "settled": dropping slower than this many leg lengths per second ... */
const SETTLE_RATE = 0.15;
/** ... for this long. */
const SETTLE_SECONDS = 0.2;
/** Timed Up and Go: the hip must travel at least this many leg lengths sideways (a 3 m walk is about 3-4). */
export const MIN_WALK = 1.5;

interface Leg {
  height: number;
  leg: number;
  hipX: number;
}

function sideLeg(frame: PoseFrame, side: 'LEFT' | 'RIGHT'): Leg | null {
  const names = [`${side}_HIP`, `${side}_KNEE`, `${side}_ANKLE`];
  if (names.some((name) => visibilityOf(frame, name) < MIN_VISIBILITY)) {
    return null;
  }
  const points = pixelPoints(frame);
  const [hip, knee, ankle] = names.map((name) => points[name]);
  if (!hip || !knee || !ankle) {
    return null;
  }
  const leg =
    Math.hypot(hip[0] - knee[0], hip[1] - knee[1]) +
    Math.hypot(knee[0] - ankle[0], knee[1] - ankle[1]);
  return leg > 0 ? { height: ankle[1] - hip[1], leg, hipX: hip[0] } : null;
}

function bestLeg(frame: PoseFrame): Leg | null {
  const sides = (['LEFT', 'RIGHT'] as const).map((side) => ({
    leg: sideLeg(frame, side),
    seen: Math.min(
      ...['HIP', 'KNEE', 'ANKLE'].map((part) => visibilityOf(frame, `${side}_${part}`)),
    ),
  }));
  const usable = sides.filter((s) => s.leg !== null).sort((a, b) => b.seen - a.seen);
  return usable[0]?.leg ?? null;
}

/** Hip height above the ankle in leg lengths per frame (null where the leg is not seen), and the hip's x in leg lengths. */
export function heightSignal(frames: readonly PoseFrame[]): {
  height: (number | null)[];
  hipX: (number | null)[];
} {
  const legs = frames.map(bestLeg);
  // the longest legs are seen standing straight; foreshortening only makes a leg look shorter
  const reference = percentile(
    legs.filter((leg): leg is Leg => leg !== null).map((leg) => leg.leg),
    0.9,
  );
  if (reference === null) {
    return { height: frames.map(() => null), hipX: frames.map(() => null) };
  }
  return {
    height: legs.map((leg) => (leg ? leg.height / reference : null)),
    hipX: legs.map((leg) => (leg ? leg.hipX / reference : null)),
  };
}

function crossing(t0: number, a: number, t1: number, b: number, level: number): number {
  return b === a ? t1 : t0 + ((level - a) / (b - a)) * (t1 - t0);
}

/** Times the test. `start` is "go" in the app (the recording starts at go) or the first movement on a recorded video. */
export function analyseCheckup(
  kind: CheckupKind,
  frames: readonly PoseFrame[],
  start: 'go' | 'first-movement' = 'go',
): CheckupResult {
  const fail = (reason: NoResultReason): CheckupResult => ({ ok: false, kind, reason });
  if (frames.length < 3) {
    return fail('person-missing');
  }
  const { height: raw, hipX } = heightSignal(frames);
  const seen = raw.filter((value) => value !== null).length;
  if (seen / frames.length < MIN_SEEN) {
    return fail('person-missing');
  }
  const duration = frames[frames.length - 1]!.timeSeconds - frames[0]!.timeSeconds;
  const window = Math.max(
    1,
    Math.round((SMOOTH_SECONDS * (frames.length - 1)) / Math.max(duration, 1e-6)),
  );
  const height = movingAverage(raw, window);
  const values = height.filter((value): value is number => value !== null);
  const low = percentile(values, 0.05)!;
  const high = percentile(values, 0.95)!;
  const range = high - low;
  if (range < MIN_RANGE) {
    return fail('no-movement');
  }
  const up = low + UP * range;
  const down = low + DOWN * range;
  const seated = low + SEATED * range;

  const standUps: number[] = [];
  const sitDowns: number[] = [];
  let standing = false;
  let previous: { t: number; v: number } | null = null;
  for (let i = 0; i < frames.length; i += 1) {
    const v = height[i];
    if (v === null || v === undefined) {
      continue;
    }
    const t = frames[i]!.timeSeconds;
    if (previous) {
      if (!standing && previous.v < up && v >= up) {
        standUps.push(crossing(previous.t, previous.v, t, v, up));
        standing = true;
      } else if (standing && previous.v > down && v <= down) {
        sitDowns.push(crossing(previous.t, previous.v, t, v, down));
        standing = false;
      }
    } else {
      standing = v >= up;
    }
    previous = { t, v };
  }

  /**
   * First time after the first sit-down at or after `after` that the person is seated: the hips reach the seated
   * level, or they have settled (below the sit-down line and no longer dropping). People often sit back a little
   * higher than their lowest point in the recording (found on Stanford tuning videos, 2026-11-27).
   */
  const seatedAt = (after: number): number | null => {
    const sit = sitDowns.find((t) => t >= after);
    if (sit === undefined) {
      return null;
    }
    let last: { t: number; v: number } | null = null;
    let flatSince: number | null = null;
    for (let i = 0; i < frames.length; i += 1) {
      const v = height[i];
      const t = frames[i]!.timeSeconds;
      if (v === null || v === undefined || t < sit) {
        continue;
      }
      if (v <= seated) {
        return last && last.v > seated ? crossing(last.t, last.v, t, v, seated) : t;
      }
      if (last && v < down) {
        const dropping = (last.v - v) / Math.max(t - last.t, 1e-6) > SETTLE_RATE;
        flatSince = dropping ? null : (flatSince ?? last.t);
        if (flatSince !== null && t - flatSince >= SETTLE_SECONDS) {
          return flatSince;
        }
      }
      last = { t, v };
    }
    return null;
  };

  let startS = frames[0]!.timeSeconds;
  if (start === 'first-movement' && standUps.length > 0) {
    const level = low + FIRST_MOVE * range;
    for (let i = frames.length - 1; i >= 0; i -= 1) {
      const v = height[i];
      const t = frames[i]!.timeSeconds;
      if (t >= standUps[0]! || v === null || v === undefined) {
        continue;
      }
      if (v <= level) {
        startS = t;
        break;
      }
    }
  }

  const done = (
    endS: number,
    extra: { seconds?: number; count?: number },
  ): CheckupResult => ({
    ok: true,
    kind,
    startS,
    endS,
    standUps,
    sitDowns,
    ...extra,
  });

  if (kind === 'sts30') {
    const count = standUps.filter((t) => t - startS <= STS30_SECONDS).length;
    return count === 0
      ? fail('too-few-stands')
      : done(startS + STS30_SECONDS, { count });
  }
  if (kind === 'sts5') {
    if (standUps.length < 5) {
      return fail('too-few-stands');
    }
    const end = seatedAt(standUps[4]!);
    return end === null ? fail('not-seated') : done(end, { seconds: end - startS });
  }
  // Timed Up and Go: stand up, walk away and back, sit down
  if (standUps.length === 0) {
    return fail('too-few-stands');
  }
  const xs = hipX.filter((x): x is number => x !== null);
  const startX = hipX.find((x) => x !== null) ?? 0;
  if (xs.length === 0 || Math.max(...xs.map((x) => Math.abs(x - startX))) < MIN_WALK) {
    return fail('no-walk');
  }
  const lastSit = sitDowns.filter((t) => t > standUps[0]!).pop();
  if (lastSit === undefined) {
    return fail('not-seated');
  }
  const end = seatedAt(lastSit);
  return end === null ? fail('not-seated') : done(end, { seconds: end - startS });
}

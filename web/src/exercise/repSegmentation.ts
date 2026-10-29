/**
 * Find repetitions in an angle curve, relative to the clip's own range.
 *
 * The thresholds are fractions of the clip's measured range (10th to 90th
 * percentile), not clinical angles: a rep starts when the angle rises past
 * the middle of the range and ends when it comes back near the bottom. This
 * is a segmentation heuristic for the prototype; rep counting accuracy is
 * measured separately.
 */
import { percentile } from './poseFrames';

export interface Rep {
  start: number;
  end: number;
  peakIndex: number;
  peakDeg: number;
  curve: number[];
}

export interface SegmentationOptions {
  enterFraction: number;
  exitFraction: number;
  /** below this range (deg) the clip has no clear movement */
  minRangeDeg: number;
  minFrames: number;
  smoothingWindow: number;
  /** longest gap of missing frames to bridge by interpolation */
  maxGapFrames: number;
}

export const DEFAULT_SEGMENTATION: SegmentationOptions = {
  enterFraction: 0.5,
  exitFraction: 0.2,
  minRangeDeg: 15,
  minFrames: 5,
  smoothingWindow: 3,
  maxGapFrames: 5,
};

/** Linear interpolation over short gaps; longer gaps stay null. */
export function fillGaps(
  values: readonly (number | null)[],
  maxGap: number,
): (number | null)[] {
  const out = [...values];
  let i = 0;
  while (i < out.length) {
    if (out[i] !== null) {
      i += 1;
      continue;
    }
    let j = i;
    while (j < out.length && out[j] === null) {
      j += 1;
    }
    const before = i > 0 ? out[i - 1] : null;
    const after = j < out.length ? out[j] : null;
    if (
      before !== null &&
      before !== undefined &&
      after !== null &&
      after !== undefined &&
      j - i <= maxGap
    ) {
      for (let k = i; k < j; k += 1) {
        out[k] = before + ((after - before) * (k - i + 1)) / (j - i + 1);
      }
    }
    i = j;
  }
  return out;
}

export function movingAverage(
  values: readonly (number | null)[],
  window: number,
): (number | null)[] {
  if (window <= 1) {
    return [...values];
  }
  const half = Math.floor(window / 2);
  return values.map((value, index) => {
    if (value === null) {
      return null;
    }
    const slice = values
      .slice(Math.max(0, index - half), index + half + 1)
      .filter((v): v is number => v !== null);
    return slice.reduce((sum, v) => sum + v, 0) / slice.length;
  });
}

export function segmentReps(
  rawCurve: readonly (number | null)[],
  options: SegmentationOptions = DEFAULT_SEGMENTATION,
): Rep[] {
  const curve = movingAverage(
    fillGaps(rawCurve, options.maxGapFrames),
    options.smoothingWindow,
  );
  const finite = curve.filter((v): v is number => v !== null);
  const low = percentile(finite, 0.1);
  const high = percentile(finite, 0.9);
  if (low === null || high === null || high - low < options.minRangeDeg) {
    return [];
  }
  const enter = low + options.enterFraction * (high - low);
  const exit = low + options.exitFraction * (high - low);
  return repsBetweenThresholds(curve, enter, exit, options.minFrames);
}

/**
 * Reps in an already smoothed curve: a rep starts at the last frame at or
 * below ``exit`` before the curve rises past ``enter``, and ends when it comes
 * back to ``exit``. Live mode passes thresholds taken from the reference rep.
 */
export function repsBetweenThresholds(
  curve: readonly (number | null)[],
  enter: number,
  exit: number,
  minFrames: number,
): Rep[] {
  if (!(enter > exit)) {
    throw new Error('enter must be above exit');
  }
  const reps: Rep[] = [];
  let lastLow: number | null = null;
  let start: number | null = null;
  for (let i = 0; i < curve.length; i += 1) {
    const value = curve[i];
    if (value === null || value === undefined) {
      start = null; // a long gap breaks the current rep
      lastLow = null;
      continue;
    }
    if (start === null) {
      if (value <= exit) {
        lastLow = i;
      } else if (value >= enter && lastLow !== null) {
        start = lastLow;
      }
    } else if (value <= exit) {
      const segment = curve.slice(start, i + 1) as number[];
      if (segment.length >= minFrames) {
        let peakOffset = 0;
        segment.forEach((v, k) => {
          if (v > segment[peakOffset]!) {
            peakOffset = k;
          }
        });
        reps.push({
          start,
          end: i,
          peakIndex: start + peakOffset,
          peakDeg: segment[peakOffset]!,
          curve: segment,
        });
      }
      start = null;
      lastLow = i;
    }
  }
  return reps;
}

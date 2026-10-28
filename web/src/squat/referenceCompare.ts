/**
 * Compare a home repetition with the clinic reference repetition.
 *
 * Port of ml/qawam_ml/reference.py (DTW with absolute-difference cost and a
 * Sakoe-Chiba band). Both curves come from the same phone pipeline, so the
 * steady angle offset found in the research (MediaPipe vs motion capture)
 * cancels in the comparison.
 */

export interface RepComparison {
  /** home peak minus reference peak; negative = not as deep */
  depthDiffDeg: number;
  /** mean absolute difference along the DTW path */
  dtwMeanAbsDeg: number;
  /** home rep frames / reference rep frames */
  tempoRatio: number;
}

export function dtwMeanAbs(
  a: readonly number[],
  b: readonly number[],
  window?: number,
): number {
  if (a.length < 2 || b.length < 2) {
    throw new Error('curves need at least 2 samples');
  }
  if (![...a, ...b].every(Number.isFinite)) {
    throw new Error('curves must be finite');
  }
  const n = a.length;
  const m = b.length;
  const band = Math.max(window ?? Math.max(n, m), Math.abs(n - m));
  const cost: Float64Array[] = Array.from({ length: n + 1 }, () =>
    new Float64Array(m + 1).fill(Infinity),
  );
  const steps: Int32Array[] = Array.from(
    { length: n + 1 },
    () => new Int32Array(m + 1),
  );
  cost[0]![0] = 0;
  for (let i = 1; i <= n; i += 1) {
    const lo = Math.max(1, i - band);
    const hi = Math.min(m, i + band);
    for (let j = lo; j <= hi; j += 1) {
      const diag = cost[i - 1]![j - 1]!;
      const up = cost[i - 1]![j]!;
      const left = cost[i]![j - 1]!;
      const best = Math.min(diag, up, left);
      cost[i]![j] = Math.abs(a[i - 1]! - b[j - 1]!) + best;
      steps[i]![j] = best === diag ? 0 : best === up ? 1 : 2;
    }
  }
  let i = n;
  let j = m;
  let length = 0;
  while (i > 0 && j > 0) {
    length += 1;
    const step = steps[i]![j];
    if (step === 0) {
      i -= 1;
      j -= 1;
    } else if (step === 1) {
      i -= 1;
    } else {
      j -= 1;
    }
  }
  return cost[n]![m]! / length;
}

export function compareRep(
  rep: readonly number[],
  reference: readonly number[],
): RepComparison {
  const window = Math.floor(Math.max(rep.length, reference.length) / 3);
  return {
    depthDiffDeg: Math.max(...rep) - Math.max(...reference),
    dtwMeanAbsDeg: dtwMeanAbs(rep, reference, window),
    tempoRatio: rep.length / reference.length,
  };
}

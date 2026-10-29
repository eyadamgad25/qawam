import { describe, expect, it } from 'vitest';
import {
  concreteLandmark,
  packAngle,
  resolvePrimaryAngle,
  SQUAT_PACK,
} from './exercisePack';
import { squatClip } from './testFrames';
import { compareRep, dtwMeanAbs } from './referenceCompare';
import { fillGaps, segmentReps } from './repSegmentation';
import {
  analyseClip,
  assessSession,
  chooseSide,
  cueFor,
  gateClip,
} from './squatSession';
import { checkView, frontalness, VIEW_RULE } from './viewGate';

describe('exercise pack', () => {
  it('resolves SIDE and OTHER tokens and measures knee flexion in pixels', () => {
    expect(concreteLandmark('SIDE_KNEE', 'left')).toBe('LEFT_KNEE');
    expect(concreteLandmark('OTHER_KNEE', 'left')).toBe('RIGHT_KNEE');
    expect(() => concreteLandmark('SIDE_TAIL', 'left')).toThrow(/unknown/);
    const angle = resolvePrimaryAngle(SQUAT_PACK, 'right');
    expect(angle.landmarks).toEqual(['RIGHT_HIP', 'RIGHT_KNEE', 'RIGHT_ANKLE']);
    expect(
      packAngle(
        { RIGHT_HIP: [0, 0], RIGHT_KNEE: [0, 100], RIGHT_ANKLE: [100, 100] },
        angle,
      ),
    ).toBeCloseTo(90);
    expect(
      packAngle(
        { RIGHT_HIP: [0, 0], RIGHT_KNEE: [0, 100], RIGHT_ANKLE: [0, 200] },
        angle,
      ),
    ).toBeCloseTo(0);
  });

  it('reads the squat pack as a side-view pack that still needs physio approval', () => {
    expect(SQUAT_PACK.view).toBe('side');
    expect(SQUAT_PACK.approvedBy).toBeNull();
  });
});

describe('view gate', () => {
  it('accepts side-on squats and refuses squats facing the camera', () => {
    const side = squatClip([90], { shoulderHalfWidth: 8 });
    const front = squatClip([90], { shoulderHalfWidth: 130 });
    expect(frontalness(side[0]!)).toBeLessThan(VIEW_RULE.side_pack_max_frontalness);
    expect(checkView(side, 'side').verdict).toBe('MATCHES');
    expect(checkView(front, 'side').verdict).toBe('TOO_FRONTAL');
    expect(checkView(front, 'front').verdict).toBe('MATCHES');
    expect(checkView([], 'side').verdict).toBe('UNKNOWN');
  });
});

describe('rep segmentation', () => {
  it('finds each rep and its depth, relative to the clip range', () => {
    const clip = analyseClip(squatClip([90, 60, 90]), SQUAT_PACK);
    expect(clip.reps).toHaveLength(3);
    expect(clip.reps[0]!.peakDeg).toBeGreaterThan(80);
    expect(clip.reps[1]!.peakDeg).toBeLessThan(clip.reps[0]!.peakDeg - 20);
  });

  it('bridges short detection gaps and ignores a still clip', () => {
    expect(fillGaps([0, null, null, 30], 5)).toEqual([0, 10, 20, 30]);
    expect(fillGaps([0, null, 30], 0)).toEqual([0, null, 30]);
    expect(segmentReps(Array(60).fill(5))).toEqual([]);
    const gappy = analyseClip(squatClip([90, 90], { dropEvery: 4 }), SQUAT_PACK);
    expect(gappy.reps).toHaveLength(2);
  });

  it('tracks the leg nearer the camera', () => {
    expect(chooseSide(squatClip([80], { nearSide: 'right' }), SQUAT_PACK)).toBe(
      'right',
    );
    expect(chooseSide(squatClip([80], { nearSide: 'left' }), SQUAT_PACK)).toBe('left');
  });
});

describe('reference comparison', () => {
  it('matches the Python DTW implementation', () => {
    const a = [0, 10, 30, 60, 80, 85, 70, 40, 15, 2];
    const b = [0, 20, 50, 75, 90, 88, 60, 30, 10, 0, 0, 1];
    const result = compareRep(a, b);
    expect(result.dtwMeanAbsDeg).toBeCloseTo(5.615384615384615, 10);
    expect(result.depthDiffDeg).toBe(-5);
    expect(result.tempoRatio).toBeCloseTo(10 / 12);
    expect(dtwMeanAbs([1, 2, 3], [1, 2, 3])).toBe(0);
    expect(() => dtwMeanAbs([1], [1, 2])).toThrow();
  });

  it('turns depth and path differences into cues using the physio tolerance', () => {
    const base = { tempoRatio: 1 };
    expect(cueFor({ ...base, depthDiffDeg: -25, dtwMeanAbsDeg: 12 }, 10)).toBe(
      'SHALLOWER_THAN_REFERENCE',
    );
    expect(cueFor({ ...base, depthDiffDeg: 25, dtwMeanAbsDeg: 12 }, 10)).toBe(
      'DEEPER_THAN_REFERENCE',
    );
    expect(cueFor({ ...base, depthDiffDeg: 2, dtwMeanAbsDeg: 12 }, 10)).toBe(
      'DIFFERENT_PATH',
    );
    expect(cueFor({ ...base, depthDiffDeg: 2, dtwMeanAbsDeg: 3 }, 10)).toBe(
      'MATCHES_REFERENCE',
    );
  });
});

describe('squat session', () => {
  const reference = analyseClip(squatClip([90]), SQUAT_PACK);

  it('gives per-rep feedback against the reference in the right view', () => {
    const home = analyseClip(squatClip([90, 55, 88]), SQUAT_PACK);
    const result = assessSession(reference, 0, home, 10);
    expect(result.status).toBe('ASSESSED');
    if (result.status !== 'ASSESSED') return;
    expect(result.reps.map((r) => r.cue)).toEqual([
      'MATCHES_REFERENCE',
      'SHALLOWER_THAN_REFERENCE',
      'MATCHES_REFERENCE',
    ]);
    expect(result.reps[1]!.messageAr).toContain('أعمق');
    expect(result.summaryAr).toContain('2 من 3');
    expect(result.reps[0]!.calibratedPeakDeg).toBeNull();
  });

  it('refuses to judge a clip filmed from the front and says how to fix it', () => {
    const home = analyseClip(
      squatClip([55, 55], { shoulderHalfWidth: 130 }),
      SQUAT_PACK,
    );
    const result = assessSession(reference, 0, home, 10);
    expect(result).toMatchObject({
      status: 'CANNOT_ASSESS',
      reasons: ['VIEW_MISMATCH'],
    });
    if (result.status === 'CANNOT_ASSESS') expect(result.messageAr).toContain('جانبك');
  });

  it('refuses when the person is mostly not detected', () => {
    const frames = squatClip([90, 90]).map((frame, i) =>
      i % 3 ? { ...frame, landmarks: null } : frame,
    );
    const gate = gateClip(analyseClip(frames, SQUAT_PACK));
    expect(gate.ok).toBe(false);
    expect(gate.reasons).toContain('LOW_DETECTION');
  });

  it('applies a goniometer reading taken on the reference rep as an offset', () => {
    const home = analyseClip(squatClip([70]), SQUAT_PACK);
    const result = assessSession(reference, 0, home, 10, 100);
    if (result.status !== 'ASSESSED') throw new Error('expected assessed');
    const refPeak = reference.reps[0]!.peakDeg;
    expect(result.reps[0]!.calibratedPeakDeg).toBeCloseTo(
      home.reps[0]!.peakDeg + (100 - refPeak),
    );
  });

  it('rejects an invalid tolerance or reference rep', () => {
    const home = analyseClip(squatClip([90]), SQUAT_PACK);
    expect(() => assessSession(reference, 0, home, 0)).toThrow(/positive/);
    expect(() => assessSession(reference, 5, home, 10)).toThrow(/reference rep/);
  });
});

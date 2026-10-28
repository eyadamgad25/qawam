import { describe, expect, it } from 'vitest';
import { assessCaptureQuality } from './captureQuality';

describe('assessCaptureQuality', () => {
  it('passes only when all caller-required landmarks meet the caller cutoff', () => {
    expect(
      assessCaptureQuality(
        ['joint-a', 'joint-b'],
        { 'joint-a': 0.8, 'joint-b': 0.5 },
        0.5,
      ),
    ).toEqual({
      status: 'READY_FOR_ANALYSIS',
      reasonCodes: [],
      failedLandmarks: [],
    });
  });

  it('reports missing and low-visibility landmarks without selecting a fallback', () => {
    expect(
      assessCaptureQuality(
        ['joint-a', 'joint-b', 'joint-c'],
        { 'joint-a': 0.4, 'joint-b': null },
        0.5,
      ),
    ).toEqual({
      status: 'CANNOT_ASSESS',
      reasonCodes: ['REQUIRED_LANDMARK_MISSING', 'LOW_REQUIRED_LANDMARK_VISIBILITY'],
      failedLandmarks: ['joint-b', 'joint-c', 'joint-a'],
    });
  });

  it('rejects an empty or duplicated requirement list and invalid cutoffs', () => {
    expect(() => assessCaptureQuality([], {}, 0.5)).toThrow(/unique, non-empty names/);
    expect(() => assessCaptureQuality(['joint-a', 'joint-a'], {}, 0.5)).toThrow(
      /unique, non-empty names/,
    );
    expect(() => assessCaptureQuality(['joint-a'], {}, 1.1)).toThrow(
      /finite number from 0 to 1/,
    );
  });

  it('rejects malformed visibility instead of treating it as a valid score', () => {
    expect(() =>
      assessCaptureQuality(['joint-a'], { 'joint-a': Number.NaN }, 0.5),
    ).toThrow(/finite number from 0 to 1/);
  });
});

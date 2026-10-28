import { describe, expect, it } from 'vitest';
import { AngleRepPipeline, angleDegrees } from './anglePipeline';

function frame(angle: number, visibility = 1) {
  const radians = (angle * Math.PI) / 180;
  return {
    coordinates: {
      a: [Math.cos(radians), Math.sin(radians)] as const,
      b: [0, 0] as const,
      c: [1, 0] as const,
    },
    visibility: { a: visibility, b: visibility, c: visibility },
  };
}

function pipeline(smoothingWindow = 1) {
  return new AngleRepPipeline({
    requiredLandmarks: ['a', 'b', 'c'],
    angleLandmarks: ['a', 'b', 'c'],
    minVisibility: 0.5,
    smoothingWindow,
    lowThreshold: 40,
    highThreshold: 70,
  });
}

describe('angleDegrees', () => {
  it('computes smaller 2D angles and refuses zero-length geometry', () => {
    expect(angleDegrees([0, 1], [0, 0], [1, 0])).toBeCloseTo(90);
    expect(angleDegrees([0, 0], [0, 0], [1, 0])).toBeNull();
    expect(() => angleDegrees([Number.NaN, 0], [0, 0], [1, 0])).toThrow(
      /finite coordinates/,
    );
  });
});

describe('AngleRepPipeline', () => {
  it('counts a complete low-high-low cycle using explicit configuration', () => {
    const instance = pipeline();
    const low = frame(30);
    const high = frame(80);

    expect(
      [low, high, low].map(
        ({ coordinates, visibility }) =>
          instance.update(coordinates, visibility).repetitionCount,
      ),
    ).toEqual([0, 0, 1]);
  });

  it('smooths causally and clears history after unusable capture', () => {
    const instance = pipeline(2);
    const first = instance.update(frame(20).coordinates, frame(20).visibility);
    const second = instance.update(frame(80).coordinates, frame(80).visibility);
    expect(first.smoothedAngleDegrees).toBeCloseTo(20);
    expect(second.smoothedAngleDegrees).toBeCloseTo(50);

    const refused = instance.update(frame(30).coordinates, { a: 1, b: 1, c: 0.1 });
    expect(refused).toMatchObject({
      status: 'CANNOT_ASSESS',
      reasonCodes: ['LOW_REQUIRED_LANDMARK_VISIBILITY'],
      angleDegrees: null,
      smoothedAngleDegrees: null,
    });

    const afterGap = instance.update(frame(80).coordinates, frame(80).visibility);
    expect(afterGap.smoothedAngleDegrees).toBeCloseTo(80);
  });

  it('breaks a partial rep cycle on an undefined angle but preserves completed count', () => {
    const instance = pipeline();
    const low = frame(30);
    const high = frame(80);
    instance.update(low.coordinates, low.visibility);
    instance.update(high.coordinates, high.visibility);
    instance.update({ a: [0, 0], b: [0, 0], c: [1, 0] }, { a: 1, b: 1, c: 1 });
    expect(instance.update(low.coordinates, low.visibility).repetitionCount).toBe(0);
    instance.update(high.coordinates, high.visibility);
    instance.update(low.coordinates, low.visibility);
    expect(instance.update(high.coordinates, high.visibility).repetitionCount).toBe(1);
  });

  it('resets count/history and rejects invalid configuration', () => {
    const instance = pipeline();
    instance.update(frame(30).coordinates, frame(30).visibility);
    instance.reset();
    expect(
      instance.update(frame(80).coordinates, frame(80).visibility).repetitionCount,
    ).toBe(0);
    expect(
      () =>
        new AngleRepPipeline({
          requiredLandmarks: ['a', 'b', 'c'],
          angleLandmarks: ['a', 'b', 'missing'],
          minVisibility: 0.5,
          smoothingWindow: 1,
          lowThreshold: 40,
          highThreshold: 70,
        }),
    ).toThrow(/three required landmarks/);
  });
});

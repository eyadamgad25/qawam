import { describe, expect, it } from 'vitest';
import type { PoseLandmark } from '../exercise/poseFrames';
import { faceBox } from './faceBlur';

function head(x: number, y: number, visibility = 0.9): PoseLandmark[] {
  return Array.from({ length: 33 }, (_, i) =>
    i <= 10
      ? { x: x + (i % 3) * 0.01, y: y + (i % 2) * 0.01, visibility }
      : { x: 0.5, y: 0.9, visibility: 0.9 },
  );
}

describe('faceBox', () => {
  it('covers every head point with padding', () => {
    const box = faceBox(head(0.5, 0.2), 640, 480)!;
    expect(box.x).toBeLessThan(0.5 * 640);
    expect(box.x + box.w).toBeGreaterThan(0.52 * 640);
    expect(box.y).toBeLessThan(0.2 * 480);
    expect(box.y + box.h).toBeGreaterThan(0.21 * 480);
  });

  it('stays inside the frame for a head at the edge', () => {
    const box = faceBox(head(0.0, 0.0), 640, 480)!;
    expect(box.x).toBe(0);
    expect(box.y).toBe(0);
  });

  it('is null when no head point is seen', () => {
    expect(faceBox(head(0.5, 0.2, 0.1), 640, 480)).toBeNull();
    expect(faceBox(null, 640, 480)).toBeNull();
  });
});

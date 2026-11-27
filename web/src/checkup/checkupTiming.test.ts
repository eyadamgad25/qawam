import { describe, expect, it } from 'vitest';
import type { PoseFrame, PoseLandmark } from '../exercise/poseFrames';
import { analyseCheckup } from './checkupTiming';

const W = 640;
const H = 480;
const FPS = 30;

/** A side-on person: shank and thigh 100 px each; h = hip height above the ankle in leg lengths (0.5 seated, 1 standing). */
function frame(t: number, h: number | null, walk = 0): PoseFrame {
  if (h === null) {
    return { timeSeconds: t, width: W, height: H, landmarks: null };
  }
  const ankle: [number, number] = [150 + walk, 420];
  const knee: [number, number] = [ankle[0], ankle[1] - 100];
  const hipY = ankle[1] - h * 200;
  const vertical = knee[1] - hipY;
  const hip: [number, number] = [
    knee[0] - Math.sqrt(Math.max(0, 100 ** 2 - vertical ** 2)),
    hipY,
  ];
  const marks: PoseLandmark[] = Array.from({ length: 33 }, () => ({
    x: 0,
    y: 0,
    visibility: 0,
  }));
  const put = (index: number, p: [number, number]) => {
    marks[index] = { x: p[0] / W, y: p[1] / H, visibility: 0.95 };
  };
  put(23, hip);
  put(25, knee);
  put(27, ankle);
  return { timeSeconds: t, width: W, height: H, landmarks: marks };
}

/** Smooth seated -> standing -> seated cycles; returns frames and the true times the hip reaches 0.6 on the way down. */
function cycles(n: number, lead = 0.5, tail = 1.0) {
  const rise = 0.6;
  const hold = 0.3;
  const fall = 0.6;
  const rest = 0.4;
  const period = rise + hold + fall + rest;
  const total = lead + n * period + tail;
  const heightAt = (t: number): number => {
    const s = t - lead;
    if (s < 0 || s >= n * period) {
      return 0.5;
    }
    const p = s % period;
    const ease = (x: number) => 0.5 - 0.5 * Math.cos(Math.PI * x);
    if (p < rise) return 0.5 + 0.5 * ease(p / rise);
    if (p < rise + hold) return 1;
    if (p < rise + hold + fall) return 1 - 0.5 * ease((p - rise - hold) / fall);
    return 0.5;
  };
  const frames: PoseFrame[] = [];
  for (let i = 0; i <= total * FPS; i += 1) {
    frames.push(frame(i / FPS, heightAt(i / FPS)));
  }
  // seated level = 0.5 + 0.2 * 0.5 = 0.6 -> reached when ease(x) = 0.8 on the fall
  const x = Math.acos(1 - 2 * 0.8) / Math.PI;
  const seatedAfter = (k: number) => lead + k * period + rise + hold + x * fall;
  return { frames, seatedAfter };
}

describe('five-times sit-to-stand', () => {
  it('times from go to seated after the fifth stand-up', () => {
    const { frames, seatedAfter } = cycles(5);
    const result = analyseCheckup('sts5', frames);
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.standUps).toHaveLength(5);
      expect(Math.abs(result.seconds! - seatedAfter(4))).toBeLessThan(0.1);
    }
  });

  it('ends when the hips settle, even if the last sit is a little higher than before', () => {
    const { frames } = cycles(5);
    const settleFrom = 0.5 + 4 * 1.9 + 0.6 + 0.3 + 0.45; // most of the 5th fall, then the person stays at 0.66
    const higher = frames.map((f) => {
      if (f.timeSeconds < settleFrom) {
        return f;
      }
      return frame(f.timeSeconds, 0.66);
    });
    const result = analyseCheckup('sts5', higher);
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(Math.abs(result.seconds! - settleFrom)).toBeLessThan(0.25);
    }
  });

  it('gives no result with four stand-ups', () => {
    expect(analyseCheckup('sts5', cycles(4).frames)).toMatchObject({
      ok: false,
      reason: 'too-few-stands',
    });
  });

  it('starts at the first movement on a recorded video', () => {
    const { frames } = cycles(5, 2.0);
    const result = analyseCheckup('sts5', frames, 'first-movement');
    expect(result.ok && result.startS).toBeGreaterThan(1.9);
    expect(result.ok && result.startS).toBeLessThan(2.25);
  });

  it('gives no result when the person is out of view for too long', () => {
    const frames = cycles(5).frames.map((f, i) =>
      i % 5 < 2 ? { ...f, landmarks: null } : f,
    );
    expect(analyseCheckup('sts5', frames)).toMatchObject({
      ok: false,
      reason: 'person-missing',
    });
  });

  it('keeps "go" as the start when the person walks into view after go', () => {
    const { frames } = cycles(5, 1.0);
    const late = frames.map((f) =>
      f.timeSeconds < 0.5 ? { ...f, landmarks: null } : f,
    );
    const result = analyseCheckup('sts5', late);
    expect(result.ok && result.startS).toBe(0);
  });

  it('says no movement for a person sitting still', () => {
    const still = Array.from({ length: 90 }, (_, i) => frame(i / FPS, 0.5));
    expect(analyseCheckup('sts5', still)).toMatchObject({
      ok: false,
      reason: 'no-movement',
    });
  });
});

describe('30-second sit-to-stand', () => {
  it('counts only stand-ups reached within 30 s', () => {
    const { frames } = cycles(20); // 1.9 s per cycle: stand-ups at 0.5 + 0.3 + 1.9 k
    const result = analyseCheckup('sts30', frames);
    expect(result.ok && result.count).toBe(16);
  });
});

describe('Timed Up and Go', () => {
  function tug(walkLegs: number) {
    const frames: PoseFrame[] = [];
    const legPx = 200;
    for (let i = 0; i <= 12 * FPS; i += 1) {
      const t = i / FPS;
      let h = 0.5;
      let walk = 0;
      if (t >= 1 && t < 1.8) h = 0.5 + 0.5 * ((t - 1) / 0.8);
      else if (t >= 1.8 && t < 9.2) {
        h = 1;
        const p = (t - 1.8) / 7.4; // out and back
        walk = walkLegs * legPx * (p < 0.5 ? p * 2 : 2 - p * 2);
      } else if (t >= 9.2 && t < 10) h = 1 - 0.5 * ((t - 9.2) / 0.8);
      frames.push(frame(t, h, walk));
    }
    return frames;
  }

  it('times stand, walk away and back, and sit', () => {
    const result = analyseCheckup('tug', tug(3));
    expect(result.ok).toBe(true);
    if (result.ok) {
      // seated level 0.6 is reached 0.8 * 0.8 s into the final sit-down
      expect(Math.abs(result.seconds! - (9.2 + 0.64))).toBeLessThan(0.15);
    }
  });

  it('gives no result when the person never walks away', () => {
    expect(analyseCheckup('tug', tug(0.5))).toMatchObject({
      ok: false,
      reason: 'no-walk',
    });
  });
});

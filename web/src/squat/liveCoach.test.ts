import { describe, expect, it } from 'vitest';
import { SQUAT_PACK } from './exercisePack';
import { fullBodyVisible, LiveSquatCoach, setupStatus, spokenText } from './liveCoach';
import { analyseClip } from './squatSession';
import { squatClip } from './testFrames';

const reference = analyseClip(squatClip([90]), SQUAT_PACK);
const referenceCurve = reference.reps[0]!.curve;

function runLive(frames: ReturnType<typeof squatClip>, tolerance = 10) {
  const coach = new LiveSquatCoach(SQUAT_PACK, { curve: referenceCurve }, tolerance);
  const events = frames.map((frame) => coach.push(frame));
  return { coach, events };
}

describe('live setup check', () => {
  it('is ready only for a full body filmed side-on', () => {
    expect(setupStatus(squatClip([90]).slice(0, 20), SQUAT_PACK).state).toBe('READY');
    const front = setupStatus(
      squatClip([90], { shoulderHalfWidth: 130 }).slice(0, 20),
      SQUAT_PACK,
    );
    expect(front.state).toBe('WRONG_VIEW');
    expect(front.messageAr).toContain('جانبك');
  });

  it('asks the person to step into view or step back', () => {
    const empty = squatClip([90])
      .slice(0, 20)
      .map((f) => ({ ...f, landmarks: null }));
    expect(setupStatus(empty, SQUAT_PACK).state).toBe('NO_PERSON');
    expect(setupStatus([], SQUAT_PACK).state).toBe('NO_PERSON');
    const cut = squatClip([90])
      .slice(0, 20)
      .map((f) => ({
        ...f,
        landmarks: f.landmarks!.map((m, i) =>
          i >= 25 ? { ...m, visibility: 0.1 } : m,
        ),
      }));
    expect(fullBodyVisible(cut[0]!)).toBe(false);
    expect(setupStatus(cut, SQUAT_PACK).state).toBe('NOT_FULL_BODY');
  });
});

describe('live squat coach', () => {
  it('reports each rep as it ends, compared with the reference', () => {
    const { coach, events } = runLive(squatClip([90, 55, 88]));
    const reps = events.flatMap((e) => (e.newRep ? [e.newRep] : []));
    expect(reps).toHaveLength(3);
    expect(coach.reps).toHaveLength(3);
    const cues = reps.map((r) => (r.assessed ? r.cue : r.reason));
    expect(cues).toEqual([
      'MATCHES_REFERENCE',
      'SHALLOWER_THAN_REFERENCE',
      'MATCHES_REFERENCE',
    ]);
    expect(spokenText(reps[1]!)).toContain('أعمق');
    expect(events.some((e) => e.inRep)).toBe(true);
  });

  it('does not judge reps filmed from the front', () => {
    const { coach } = runLive(squatClip([90, 90], { shoulderHalfWidth: 130 }));
    expect(coach.reps.length).toBeGreaterThan(0);
    for (const rep of coach.reps) {
      expect(rep.assessed).toBe(false);
      if (!rep.assessed) expect(rep.reason).toBe('VIEW_MISMATCH');
    }
    expect(spokenText(coach.reps[0]!)).toBe('لم أرك جيدًا');
  });

  it('bridges a few missed frames but not a long gap', () => {
    const frames = squatClip([90]);
    const short = frames.map((f, i) =>
      i === 20 || i === 21 ? { ...f, landmarks: null } : f,
    );
    expect(runLive(short).coach.reps).toHaveLength(1);
    const long = frames.map((f, i) =>
      i >= 15 && i < 30 ? { ...f, landmarks: null } : f,
    );
    expect(runLive(long).coach.reps).toHaveLength(0);
  });

  it('rejects a reference without movement or a bad tolerance', () => {
    expect(() => new LiveSquatCoach(SQUAT_PACK, { curve: [5, 6, 7] }, 10)).toThrow(
      /no movement/,
    );
    expect(() => new LiveSquatCoach(SQUAT_PACK, { curve: referenceCurve }, 0)).toThrow(
      /positive/,
    );
  });
});

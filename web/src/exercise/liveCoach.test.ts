import { describe, expect, it } from 'vitest';
import {
  LEG_ABDUCTION_PACK,
  LUNGE_PACK,
  SHOULDER_ABDUCTION_PACK,
  SQUAT_PACK,
  type ExercisePack,
} from './exercisePack';
import {
  arabicNumberWord,
  LiveCoach,
  missingParts,
  setupStatus,
  summarise,
  type LiveReference,
} from './liveCoach';
import type { PoseFrame } from './poseFrames';
import { analyseClip, chooseSide, repPosture } from './session';
import { abductionClip, squatClip } from './testFrames';

function referenceFrom(frames: PoseFrame[], pack: ExercisePack): LiveReference {
  const clip = analyseClip(frames, pack);
  const rep = clip.reps[0]!;
  return {
    curve: rep.curve,
    baseDeg: clip.baseDeg,
    durationSeconds: (clip.times[rep.end] ?? 0) - (clip.times[rep.start] ?? 0),
    side: clip.side,
    posture: repPosture(clip, rep.start, rep.end),
  };
}

function runLive(
  pack: ExercisePack,
  reference: LiveReference,
  frames: PoseFrame[],
  tolerance = 10,
) {
  const coach = new LiveCoach(pack, reference, tolerance);
  const events = frames.map((frame) => coach.push(frame));
  return { coach, events };
}

const cues = (coach: LiveCoach) =>
  coach.reps.map((r) => (r.assessed ? r.cue : r.reason));

describe('live setup check', () => {
  it('is ready only for a full body filmed from the pack view', () => {
    expect(setupStatus(squatClip([90]).slice(0, 20), SQUAT_PACK).state).toBe('READY');
    const front = setupStatus(
      squatClip([90], { shoulderHalfWidth: 130 }).slice(0, 20),
      SQUAT_PACK,
    );
    expect(front.state).toBe('WRONG_VIEW');
    expect(front.spokenAr).toBe('استدر للجنب');
    const abduction = abductionClip('leg', [30]).slice(0, 20);
    expect(setupStatus(abduction, LEG_ABDUCTION_PACK).state).toBe('READY');
    expect(setupStatus(abduction, SQUAT_PACK).state).toBe('WRONG_VIEW');
  });

  it('names the body parts it cannot see', () => {
    const empty = squatClip([90])
      .slice(0, 20)
      .map((f) => ({ ...f, landmarks: null }));
    expect(setupStatus(empty, SQUAT_PACK).state).toBe('NO_PERSON');
    expect(setupStatus([], SQUAT_PACK).state).toBe('NO_PERSON');
    const noFeet = squatClip([90])
      .slice(0, 20)
      .map((f) => ({
        ...f,
        landmarks: f.landmarks!.map((m, i) =>
          i === 27 || i === 28 ? { ...m, visibility: 0.1 } : m,
        ),
      }));
    expect(missingParts(noFeet[0]!, SQUAT_PACK)).toEqual(['ANKLE']);
    const status = setupStatus(noFeet, SQUAT_PACK);
    expect(status.state).toBe('NOT_FULL_BODY');
    expect(status.messageAr).toContain('قدميك');
    expect(status.messageAr).toContain('اخفضها');
  });
});

describe('live coach', () => {
  const squatRef = referenceFrom(squatClip([90]), SQUAT_PACK);

  it('counts and judges each squat as it ends, with a spoken count', () => {
    const { coach, events } = runLive(SQUAT_PACK, squatRef, squatClip([90, 55, 88]));
    expect(cues(coach)).toEqual([
      'MATCHES_REFERENCE',
      'LESS_THAN_REFERENCE',
      'MATCHES_REFERENCE',
    ]);
    expect(coach.reps[1]!.spokenAr).toBe('اثنان، انزل أعمق قليلًا');
    expect(coach.reps[0]!.spokenAr).toBe('واحد، ممتاز');
    const progress = events.map((e) => e.progress ?? 0);
    expect(Math.max(...progress)).toBeGreaterThan(0.9);
  });

  it('still counts when the home camera reads every angle differently', () => {
    // Home angles read 10-20 deg higher than in the clinic (camera height,
    // distance); counting and comparison use each session's own resting angle.
    const ref = referenceFrom(squatClip([60]), SQUAT_PACK);
    const home = squatClip([70, 50, 70], { restDeg: 12 });
    expect(analyseClip(home, SQUAT_PACK).baseDeg - ref.baseDeg).toBeGreaterThan(15);
    const { coach } = runLive(SQUAT_PACK, ref, home);
    expect(cues(coach)).toEqual([
      'MATCHES_REFERENCE',
      'LESS_THAN_REFERENCE',
      'MATCHES_REFERENCE',
    ]);
  });

  it('does not judge reps filmed from the wrong view', () => {
    const { coach } = runLive(
      SQUAT_PACK,
      squatRef,
      squatClip([90, 90], { shoulderHalfWidth: 130 }),
    );
    expect(coach.reps.length).toBeGreaterThan(0);
    expect(coach.reps.every((rep) => !rep.assessed)).toBe(true);
    expect(coach.reps[0]!.spokenAr).toContain('استدر للجنب');
  });

  it('works for the lunge, measured on the side view', () => {
    const ref = referenceFrom(squatClip([80]), LUNGE_PACK);
    const { coach } = runLive(LUNGE_PACK, ref, squatClip([80, 45]));
    expect(cues(coach)).toEqual(['MATCHES_REFERENCE', 'LESS_THAN_REFERENCE']);
    expect(coach.reps[1]!.spokenAr).toContain('انزل أعمق');
  });

  it('works for leg abduction filmed from the front, on the moving leg', () => {
    const refFrames = abductionClip('leg', [35], { movingSide: 'right' });
    expect(chooseSide(refFrames, LEG_ABDUCTION_PACK)).toBe('right');
    const ref = referenceFrom(refFrames, LEG_ABDUCTION_PACK);
    expect(ref.side).toBe('right');
    const { coach } = runLive(
      LEG_ABDUCTION_PACK,
      ref,
      abductionClip('leg', [35, 15, 55], { movingSide: 'right' }),
    );
    expect(cues(coach)).toEqual([
      'MATCHES_REFERENCE',
      'LESS_THAN_REFERENCE',
      'MORE_THAN_REFERENCE',
    ]);
    expect(coach.reps[1]!.spokenAr).toContain('ارفع رجلك');
  });

  it('works for shoulder abduction filmed from the front', () => {
    const ref = referenceFrom(
      abductionClip('arm', [80], { movingSide: 'left' }),
      SHOULDER_ABDUCTION_PACK,
    );
    expect(ref.side).toBe('left');
    const { coach } = runLive(
      SHOULDER_ABDUCTION_PACK,
      ref,
      abductionClip('arm', [80, 50], { movingSide: 'left' }),
    );
    expect(cues(coach)).toEqual(['MATCHES_REFERENCE', 'LESS_THAN_REFERENCE']);
    expect(coach.reps[1]!.messageAr).toContain('ذراعك');
  });

  it('flags a bent elbow during arm abduction even when the height is right', () => {
    const ref = referenceFrom(
      abductionClip('arm', [80], { movingSide: 'left' }),
      SHOULDER_ABDUCTION_PACK,
    );
    const { coach } = runLive(
      SHOULDER_ABDUCTION_PACK,
      ref,
      abductionClip('arm', [80, 80], { movingSide: 'left', elbowBendDeg: [0, 60] }),
    );
    expect(cues(coach)).toEqual(['MATCHES_REFERENCE', 'POSTURE_DIFFERENT']);
    const bent = coach.reps[1]!;
    expect(bent.spokenAr).toBe('اثنان، افرد ذراعك');
    expect(bent.messageAr).toContain('كوعك');
  });

  it('bridges a few missed frames but not a long gap', () => {
    const frames = squatClip([90]);
    const short = frames.map((f, i) =>
      i === 20 || i === 21 ? { ...f, landmarks: null } : f,
    );
    expect(runLive(SQUAT_PACK, squatRef, short).coach.reps).toHaveLength(1);
    const long = frames.map((f, i) =>
      i >= 15 && i < 30 ? { ...f, landmarks: null } : f,
    );
    expect(runLive(SQUAT_PACK, squatRef, long).coach.reps).toHaveLength(0);
  });

  it('rejects a reference without movement or a bad tolerance', () => {
    expect(
      () =>
        new LiveCoach(SQUAT_PACK, { ...squatRef, curve: [5, 6, 7], baseDeg: 5 }, 10),
    ).toThrow(/no movement/);
    expect(() => new LiveCoach(SQUAT_PACK, squatRef, 0)).toThrow(/positive/);
  });
});

describe('session summary', () => {
  it('sums up the set in text and speech', () => {
    const { coach } = runLive(
      SQUAT_PACK,
      referenceFrom(squatClip([90]), SQUAT_PACK),
      squatClip([90, 50, 52, 90]),
    );
    const summary = summarise(coach.reps, SQUAT_PACK);
    expect(summary.reps).toBe(4);
    expect(summary.matches).toBe(2);
    expect(summary.spokenAr).toBe(
      'انتهى التمرين. عدد التكرارات 4، والقريبة من المرجع 2',
    );
    expect(summarise([], SQUAT_PACK).textAr).toContain('لم أحسب');
    expect(arabicNumberWord(25)).toBe('25');
  });
});

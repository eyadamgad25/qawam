import { describe, expect, it } from 'vitest';
import {
  advanceArmRaiseCounter,
  ARM_RAISE_DEMO,
  getArmElevationAngle,
  INITIAL_ARM_RAISE_STATE,
  type PosePoint,
} from './armRaiseCounter';

function poseWithLeftArm(wristX: number, wristY: number): PosePoint[] {
  const landmarks = Array.from({ length: 33 }, () => ({
    x: 0.5,
    y: 0.5,
    visibility: 0.1,
  }));
  landmarks[11] = { x: 0.5, y: 0.4, visibility: 0.9 };
  landmarks[15] = { x: wristX, y: wristY, visibility: 0.9 };
  landmarks[23] = { x: 0.5, y: 0.8, visibility: 0.9 };
  return landmarks;
}

describe('experimental arm-raise counter', () => {
  it('calculates the shoulder-to-hip versus shoulder-to-wrist angle', () => {
    expect(getArmElevationAngle(poseWithLeftArm(0.5, 0.6), 'left')).toBeCloseTo(0);
    expect(getArmElevationAngle(poseWithLeftArm(0.7, 0.4), 'left')).toBeCloseTo(90);
    expect(getArmElevationAngle(poseWithLeftArm(0.5, 0.2), 'left')).toBeCloseTo(180);
  });

  it('counts only a complete lowered-raised-lowered cycle', () => {
    let state = advanceArmRaiseCounter(
      INITIAL_ARM_RAISE_STATE,
      poseWithLeftArm(0.5, 0.6),
    );
    expect(state.repetitions).toBe(0);
    state = advanceArmRaiseCounter(state, poseWithLeftArm(0.5, 0.2));
    expect(state.repetitions).toBe(0);
    state = advanceArmRaiseCounter(state, poseWithLeftArm(0.5, 0.6));
    expect(state.repetitions).toBe(1);
  });

  it('keeps the selected side stable and exposes its angle and visibility', () => {
    const firstPose = poseWithLeftArm(0.5, 0.6);
    firstPose[12] = { x: 0.7, y: 0.4, visibility: 0.95 };
    firstPose[16] = { x: 0.7, y: 0.6, visibility: 0.95 };
    firstPose[24] = { x: 0.7, y: 0.8, visibility: 0.95 };
    let state = advanceArmRaiseCounter(INITIAL_ARM_RAISE_STATE, firstPose);
    expect(state.side).toBe('right');
    expect(state.angleDegrees).toBeCloseTo(0);
    expect(state.visibility).toBeCloseTo(0.95);

    const nextPose = poseWithLeftArm(0.5, 0.6);
    nextPose[11] = { x: 0.5, y: 0.4, visibility: 0.99 };
    nextPose[15] = { x: 0.5, y: 0.2, visibility: 0.99 };
    nextPose[23] = { x: 0.5, y: 0.8, visibility: 0.99 };
    nextPose[12] = { x: 0.7, y: 0.4, visibility: 0.6 };
    nextPose[16] = { x: 0.7, y: 0.2, visibility: 0.6 };
    nextPose[24] = { x: 0.7, y: 0.8, visibility: 0.6 };
    state = advanceArmRaiseCounter(state, nextPose);
    expect(state.side).toBe('right');
    expect(state.phase).toBe('raised');
    expect(state.angleDegrees).toBeCloseTo(180);
    expect(state.visibility).toBeCloseTo(0.6);
  });

  it('uses the manually selected side even when the other side is more visible', () => {
    const pose = poseWithLeftArm(0.5, 0.6);
    pose[12] = { x: 0.7, y: 0.4, visibility: 0.99 };
    pose[16] = { x: 0.7, y: 0.2, visibility: 0.99 };
    pose[24] = { x: 0.7, y: 0.8, visibility: 0.99 };

    const state = advanceArmRaiseCounter(INITIAL_ARM_RAISE_STATE, pose, 'left');

    expect(state.side).toBe('left');
    expect(state.angleDegrees).toBeCloseTo(0);
  });

  it('does not fall back to the opposite side if the manually selected side is unclear', () => {
    const pose = poseWithLeftArm(0.5, 0.6);
    pose[15] = { x: 0.5, y: 0.6, visibility: 0.2 };
    pose[12] = { x: 0.7, y: 0.4, visibility: 0.99 };
    pose[16] = { x: 0.7, y: 0.2, visibility: 0.99 };
    pose[24] = { x: 0.7, y: 0.8, visibility: 0.99 };

    const state = advanceArmRaiseCounter(INITIAL_ARM_RAISE_STATE, pose, 'left');

    expect(state.side).toBeNull();
    expect(state.angleDegrees).toBeNull();
    expect(state.repetitions).toBe(0);
  });

  it('does not count a cycle when mapped landmarks fail visibility', () => {
    let state = advanceArmRaiseCounter(
      INITIAL_ARM_RAISE_STATE,
      poseWithLeftArm(0.5, 0.6),
    );
    const unclearPose = poseWithLeftArm(0.5, 0.2);
    unclearPose[15] = {
      x: 0.5,
      y: 0.2,
      visibility: ARM_RAISE_DEMO.minimumVisibility - 0.01,
    };
    state = advanceArmRaiseCounter(state, unclearPose);
    state = advanceArmRaiseCounter(state, poseWithLeftArm(0.5, 0.6));
    expect(state.repetitions).toBe(0);
    expect(state.phase).toBe('lowered');
  });

  it('does not count when the recording begins with the arm already raised', () => {
    let state = advanceArmRaiseCounter(
      INITIAL_ARM_RAISE_STATE,
      poseWithLeftArm(0.5, 0.2),
    );
    state = advanceArmRaiseCounter(state, poseWithLeftArm(0.5, 0.6));
    expect(state.repetitions).toBe(0);
  });
});

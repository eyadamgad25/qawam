import { assessCaptureQuality, type CaptureReasonCode } from './captureQuality';

export type Point2D = readonly [number, number];
export type LandmarkCoordinates = Readonly<Record<string, Point2D | undefined>>;
export type LandmarkVisibility = Readonly<Record<string, number | null | undefined>>;

export interface AngleRepPipelineConfig {
  requiredLandmarks: readonly string[];
  angleLandmarks: readonly [string, string, string];
  minVisibility: number;
  smoothingWindow: number;
  lowThreshold: number;
  highThreshold: number;
}

export interface AngleRepResult {
  status: 'READY_FOR_ANALYSIS' | 'CANNOT_ASSESS';
  reasonCodes: readonly (CaptureReasonCode | 'ANGLE_UNDEFINED')[];
  failedLandmarks: readonly string[];
  angleDegrees: number | null;
  smoothedAngleDegrees: number | null;
  repetitionCount: number;
}

export class AngleRepPipeline {
  private readonly requiredLandmarks: readonly string[];
  private readonly angleLandmarks: readonly [string, string, string];
  private readonly minVisibility: number;
  private readonly smoothingWindow: number;
  private readonly lowThreshold: number;
  private readonly highThreshold: number;
  private angleHistory: number[] = [];
  private phase: 'seek-low' | 'ready' | 'seek-return' = 'seek-low';
  private count = 0;

  constructor(config: AngleRepPipelineConfig) {
    const { requiredLandmarks, angleLandmarks } = config;
    if (
      requiredLandmarks.length === 0 ||
      requiredLandmarks.some((name) => !name.trim()) ||
      new Set(requiredLandmarks).size !== requiredLandmarks.length
    ) {
      throw new Error('requiredLandmarks must contain unique, non-empty names');
    }
    if (
      new Set(angleLandmarks).size !== 3 ||
      angleLandmarks.some((name) => !requiredLandmarks.includes(name))
    ) {
      throw new Error('angleLandmarks must be three required landmarks');
    }
    validateFinite(config.minVisibility, 'minVisibility');
    if (config.minVisibility < 0 || config.minVisibility > 1) {
      throw new Error('minVisibility must be from 0 to 1');
    }
    if (!Number.isInteger(config.smoothingWindow) || config.smoothingWindow <= 0) {
      throw new Error('smoothingWindow must be a positive integer');
    }
    validateFinite(config.lowThreshold, 'lowThreshold');
    validateFinite(config.highThreshold, 'highThreshold');
    if (config.lowThreshold >= config.highThreshold) {
      throw new Error('lowThreshold must be less than highThreshold');
    }

    this.requiredLandmarks = [...requiredLandmarks];
    this.angleLandmarks = [angleLandmarks[0], angleLandmarks[1], angleLandmarks[2]];
    this.minVisibility = config.minVisibility;
    this.smoothingWindow = config.smoothingWindow;
    this.lowThreshold = config.lowThreshold;
    this.highThreshold = config.highThreshold;
  }

  update(
    coordinates: LandmarkCoordinates,
    visibilityByLandmark: LandmarkVisibility,
  ): AngleRepResult {
    const requiredVisibility: Record<string, number | null | undefined> = {};
    for (const name of this.requiredLandmarks) {
      requiredVisibility[name] = Object.hasOwn(coordinates, name)
        ? visibilityByLandmark[name]
        : undefined;
      if (Object.hasOwn(coordinates, name)) {
        validatePoint(coordinates[name], name);
      }
    }

    const quality = assessCaptureQuality(
      this.requiredLandmarks,
      requiredVisibility,
      this.minVisibility,
    );
    if (quality.status === 'CANNOT_ASSESS') {
      this.breakPartialCycle();
      return this.refused(quality.reasonCodes, quality.failedLandmarks);
    }

    const pointA = coordinates[this.angleLandmarks[0]];
    const vertex = coordinates[this.angleLandmarks[1]];
    const pointC = coordinates[this.angleLandmarks[2]];
    if (!pointA || !vertex || !pointC) {
      this.breakPartialCycle();
      return this.refused(
        ['REQUIRED_LANDMARK_MISSING'],
        this.angleLandmarks.filter((name) => !coordinates[name]),
      );
    }
    const angle = angleDegrees(pointA, vertex, pointC);
    if (angle === null) {
      this.breakPartialCycle();
      return this.refused(['ANGLE_UNDEFINED'], this.angleLandmarks);
    }

    this.angleHistory.push(angle);
    if (this.angleHistory.length > this.smoothingWindow) {
      this.angleHistory.shift();
    }
    const smoothedAngle =
      this.angleHistory.reduce((sum, value) => sum + value, 0) /
      this.angleHistory.length;
    this.updateRepCounter(smoothedAngle);

    return {
      status: 'READY_FOR_ANALYSIS',
      reasonCodes: [],
      failedLandmarks: [],
      angleDegrees: angle,
      smoothedAngleDegrees: smoothedAngle,
      repetitionCount: this.count,
    };
  }

  reset(): void {
    this.angleHistory = [];
    this.count = 0;
    this.phase = 'seek-low';
  }

  private updateRepCounter(angle: number): void {
    if (this.phase === 'seek-low') {
      if (angle <= this.lowThreshold) {
        this.phase = 'ready';
      }
    } else if (this.phase === 'ready') {
      if (angle >= this.highThreshold) {
        this.phase = 'seek-return';
      }
    } else if (angle <= this.lowThreshold) {
      this.count += 1;
      this.phase = 'ready';
    }
  }

  private breakPartialCycle(): void {
    this.angleHistory = [];
    this.phase = 'seek-low';
  }

  private refused(
    reasonCodes: readonly (CaptureReasonCode | 'ANGLE_UNDEFINED')[],
    failedLandmarks: readonly string[],
  ): AngleRepResult {
    return {
      status: 'CANNOT_ASSESS',
      reasonCodes,
      failedLandmarks,
      angleDegrees: null,
      smoothedAngleDegrees: null,
      repetitionCount: this.count,
    };
  }
}

export function angleDegrees(
  pointA: Point2D,
  vertex: Point2D,
  pointC: Point2D,
): number | null {
  validatePoint(pointA, 'pointA');
  validatePoint(vertex, 'vertex');
  validatePoint(pointC, 'pointC');

  const armAX = pointA[0] - vertex[0];
  const armAY = pointA[1] - vertex[1];
  const armCX = pointC[0] - vertex[0];
  const armCY = pointC[1] - vertex[1];
  if (![armAX, armAY, armCX, armCY].every(Number.isFinite)) {
    throw new Error('coordinate differences must be finite');
  }
  const lengthA = Math.hypot(armAX, armAY);
  const lengthC = Math.hypot(armCX, armCY);
  if (!Number.isFinite(lengthA) || !Number.isFinite(lengthC)) {
    throw new Error('arm lengths must be finite');
  }
  if (lengthA === 0 || lengthC === 0) {
    return null;
  }

  const cross =
    (armAX / lengthA) * (armCY / lengthC) - (armAY / lengthA) * (armCX / lengthC);
  const dot =
    (armAX / lengthA) * (armCX / lengthC) + (armAY / lengthA) * (armCY / lengthC);
  return (Math.atan2(Math.abs(cross), dot) * 180) / Math.PI;
}

function validatePoint(point: Point2D | undefined, name: string): void {
  if (
    !point ||
    point.length !== 2 ||
    !Number.isFinite(point[0]) ||
    !Number.isFinite(point[1])
  ) {
    throw new Error(`${name} must contain exactly two finite coordinates`);
  }
}

function validateFinite(value: number, name: string): void {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw new Error(`${name} must be finite`);
  }
}

export type CaptureStatus = 'READY_FOR_ANALYSIS' | 'CANNOT_ASSESS';
export type CaptureReasonCode =
  'REQUIRED_LANDMARK_MISSING' | 'LOW_REQUIRED_LANDMARK_VISIBILITY';

export interface CaptureQualityResult {
  status: CaptureStatus;
  reasonCodes: readonly CaptureReasonCode[];
  failedLandmarks: readonly string[];
}

export function assessCaptureQuality(
  requiredLandmarks: readonly string[],
  visibilityByLandmark: Readonly<Record<string, number | null | undefined>>,
  minVisibility: number,
): CaptureQualityResult {
  if (
    typeof requiredLandmarks === 'string' ||
    requiredLandmarks.length === 0 ||
    requiredLandmarks.some((name) => typeof name !== 'string' || !name.trim()) ||
    new Set(requiredLandmarks).size !== requiredLandmarks.length
  ) {
    throw new Error('requiredLandmarks must contain unique, non-empty names');
  }
  validateVisibility(minVisibility, 'minVisibility');

  const missing: string[] = [];
  const lowVisibility: string[] = [];
  for (const landmark of requiredLandmarks) {
    if (!Object.hasOwn(visibilityByLandmark, landmark)) {
      missing.push(landmark);
      continue;
    }

    const visibility = visibilityByLandmark[landmark];
    if (visibility === null || visibility === undefined) {
      missing.push(landmark);
      continue;
    }
    validateVisibility(visibility, landmark);
    if (visibility < minVisibility) {
      lowVisibility.push(landmark);
    }
  }

  const reasonCodes: CaptureReasonCode[] = [];
  const failedLandmarks: string[] = [];
  if (missing.length > 0) {
    reasonCodes.push('REQUIRED_LANDMARK_MISSING');
    failedLandmarks.push(...missing);
  }
  if (lowVisibility.length > 0) {
    reasonCodes.push('LOW_REQUIRED_LANDMARK_VISIBILITY');
    failedLandmarks.push(...lowVisibility);
  }

  return {
    status: reasonCodes.length > 0 ? 'CANNOT_ASSESS' : 'READY_FOR_ANALYSIS',
    reasonCodes,
    failedLandmarks,
  };
}

function validateVisibility(value: number, name: string): void {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > 1) {
    throw new Error(`${name} visibility must be a finite number from 0 to 1`);
  }
}

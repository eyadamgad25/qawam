import { AngleRepPipeline } from './anglePipeline';

export interface SyntheticFrameResult {
  frame: number;
  status: 'READY_FOR_ANALYSIS' | 'CANNOT_ASSESS';
  angleDegrees: number | null;
  repetitionCount: number;
  reasonCodes: readonly string[];
}

function createFrame(angleDegrees: number, visibility = 1) {
  const radians = (angleDegrees * Math.PI) / 180;
  return {
    coordinates: {
      proximal: [Math.cos(radians), Math.sin(radians)] as const,
      joint: [0, 0] as const,
      distal: [1, 0] as const,
    },
    visibility: {
      proximal: visibility,
      joint: visibility,
      distal: visibility,
    },
  };
}

export function runSyntheticAnglePipelineDemo(): SyntheticFrameResult[] {
  const pipeline = new AngleRepPipeline({
    requiredLandmarks: ['proximal', 'joint', 'distal'],
    angleLandmarks: ['proximal', 'joint', 'distal'],
    minVisibility: 0.5,
    smoothingWindow: 1,
    lowThreshold: 40,
    highThreshold: 70,
  });
  const frames = [
    createFrame(30),
    createFrame(80),
    createFrame(30),
    createFrame(80),
    createFrame(30, 0.1),
    createFrame(30),
    createFrame(80),
    createFrame(30),
  ];

  return frames.map(({ coordinates, visibility }, index) => {
    const result = pipeline.update(coordinates, visibility);
    return {
      frame: index + 1,
      status: result.status,
      angleDegrees: result.angleDegrees,
      repetitionCount: result.repetitionCount,
      reasonCodes: result.reasonCodes,
    };
  });
}

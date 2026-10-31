/**
 * Exercise packs (rules/packs/*.json) for the browser.
 *
 * The same JSON drives the Python research code (ml/qawam_ml/packs.py) and
 * the app, so the angle the app measures is the angle the evaluation
 * measured. SIDE_* tokens resolve to the chosen leg, OTHER_* to the other.
 */
import legAbductionPackJson from '../../../rules/packs/lower-limb.leg-abduction.json';
import lungePackJson from '../../../rules/packs/lower-limb.lunge.json';
import squatPackJson from '../../../rules/packs/lower-limb.squat.json';
import shoulderAbductionPackJson from '../../../rules/packs/upper-limb.shoulder-abduction.json';
import shoulderFlexionPackJson from '../../../rules/packs/upper-limb.shoulder-flexion.json';
import { angleDegrees, type Point2D } from '../anglePipeline';

export type Side = 'left' | 'right';
export type AngleTransform = 'interior' | 'flexion' | 'abduction';

export interface PackAngle {
  name: string;
  triplet: [string, string, string];
  transform: AngleTransform;
}

export interface ExercisePack {
  packId: string;
  version: number;
  names: { ar: string; en: string };
  view: string;
  sides: string;
  requiredLandmarks: string[];
  angles: PackAngle[];
  primaryAngle: string;
  status: string;
  provenance: string;
  approvedBy: string | null;
}

export interface ResolvedAngle {
  name: string;
  landmarks: [string, string, string];
  transform: AngleTransform;
}

/** MediaPipe Pose landmark indices used by the packs. */
export const MEDIAPIPE_INDEX: Readonly<Record<string, number>> = {
  NOSE: 0,
  LEFT_SHOULDER: 11,
  RIGHT_SHOULDER: 12,
  LEFT_ELBOW: 13,
  RIGHT_ELBOW: 14,
  LEFT_WRIST: 15,
  RIGHT_WRIST: 16,
  LEFT_HIP: 23,
  RIGHT_HIP: 24,
  LEFT_KNEE: 25,
  RIGHT_KNEE: 26,
  LEFT_ANKLE: 27,
  RIGHT_ANKLE: 28,
  LEFT_HEEL: 29,
  RIGHT_HEEL: 30,
  LEFT_FOOT_INDEX: 31,
  RIGHT_FOOT_INDEX: 32,
};

export const SQUAT_PACK = squatPackJson as unknown as ExercisePack;
export const LUNGE_PACK = lungePackJson as unknown as ExercisePack;
export const LEG_ABDUCTION_PACK = legAbductionPackJson as unknown as ExercisePack;
export const SHOULDER_ABDUCTION_PACK =
  shoulderAbductionPackJson as unknown as ExercisePack;
export const SHOULDER_FLEXION_PACK = shoulderFlexionPackJson as unknown as ExercisePack;

/** Exercises available in the app, in menu order. */
export const EXERCISE_PACKS: readonly ExercisePack[] = [
  SQUAT_PACK,
  LUNGE_PACK,
  LEG_ABDUCTION_PACK,
  SHOULDER_ABDUCTION_PACK,
  SHOULDER_FLEXION_PACK,
];

/** Arabic wording per exercise. Coaching text only; no clinical thresholds. */
export interface PackCopy {
  /** what the measured angle means to the patient */
  measureAr: string;
  /** how to stand for the camera */
  setupAr: string;
  /** cue when the rep did less than the reference (not deep / not high enough) */
  moreAr: string;
  /** cue when the rep went past the reference */
  lessAr: string;
  spokenMoreAr: string;
  spokenLessAr: string;
  /** what the research found for this exercise, shown to the user */
  evidenceAr: string;
}

export const PACK_COPY: Readonly<Record<string, PackCopy>> = {
  'lower-limb.squat': {
    measureAr: 'ثني الركبة',
    setupAr: 'قف بجانبك للكاميرا، وجسمك ظاهر من الكتفين إلى القدمين.',
    moreAr: 'نزولك أقل من التكرار المرجعي. انزل قليلًا أعمق إن لم تشعر بألم.',
    lessAr: 'نزلت أعمق من التكرار المرجعي. التزم بالعمق الذي حدده أخصائيك.',
    spokenMoreAr: 'انزل أعمق قليلًا',
    spokenLessAr: 'لا تنزل أعمق من المرجع',
    evidenceAr:
      'في التجربة البحثية على 5 أشخاص، أخطأ القياس في 3 من 88 تكرار سكوات صُوّر من الجنب.',
  },
  'lower-limb.lunge': {
    measureAr: 'ثني الركبة الأمامية',
    setupAr: 'قف بجانبك للكاميرا، والقدمان ظاهرتان.',
    moreAr: 'نزولك في الطعنة أقل من المرجع. انزل قليلًا أعمق إن لم تشعر بألم.',
    lessAr: 'نزلت في الطعنة أعمق من المرجع. التزم بالعمق الذي حدده أخصائيك.',
    spokenMoreAr: 'انزل أعمق قليلًا',
    spokenLessAr: 'لا تنزل أعمق من المرجع',
    evidenceAr:
      'في التجربة البحثية على 5 أشخاص، أخطأ القياس في 3 من 52 تكرار طعن صُوّر من الجنب.',
  },
  'lower-limb.leg-abduction': {
    measureAr: 'رفع الرجل للجنب',
    setupAr: 'واجه الكاميرا مباشرة، وجسمك ظاهر من الكتفين إلى القدمين.',
    moreAr: 'رفعت رجلك أقل من المرجع. ارفعها قليلًا أعلى إن لم تشعر بألم.',
    lessAr: 'رفعت رجلك أعلى من المرجع. التزم بالارتفاع الذي حدده أخصائيك.',
    spokenMoreAr: 'ارفع رجلك أعلى قليلًا',
    spokenLessAr: 'لا ترفع رجلك أعلى من المرجع',
    evidenceAr:
      'في التجربة البحثية، أخطأ القياس في 1 من 26 تكرارًا صُوّر من الأمام، ولا يمكن قياسه من الجنب.',
  },
  'upper-limb.shoulder-abduction': {
    measureAr: 'رفع الذراع للجنب',
    setupAr: 'واجه الكاميرا مباشرة، والذراعان والوركان ظاهرة.',
    moreAr: 'رفعت ذراعك أقل من المرجع. ارفعها قليلًا أعلى إن لم تشعر بألم.',
    lessAr: 'رفعت ذراعك أعلى من المرجع. التزم بالارتفاع الذي حدده أخصائيك.',
    spokenMoreAr: 'ارفع ذراعك أعلى قليلًا',
    spokenLessAr: 'لا ترفع ذراعك أعلى من المرجع',
    evidenceAr:
      'لم نقِس بعد دقة البوابة لهذا التمرين؛ المقارنة بالمرجع الشخصي ميّزت الأخطاء جيدًا في بيانات REHAB26 (AUC 0.76).',
  },
  'upper-limb.shoulder-flexion': {
    measureAr: 'رفع الذراع للأمام',
    setupAr: 'قف بجانبك للكاميرا، والذراع المقاسة ناحية الكاميرا، والورك ظاهر.',
    moreAr: 'رفعت ذراعك أقل من المرجع. ارفعها قليلًا أعلى إن لم تشعر بألم.',
    lessAr: 'رفعت ذراعك أعلى من المرجع. التزم بالارتفاع الذي حدده أخصائيك.',
    spokenMoreAr: 'ارفع ذراعك أعلى قليلًا',
    spokenLessAr: 'لا ترفع ذراعك أعلى من المرجع',
    evidenceAr:
      'على هياكل 34 مريضًا من بيانات KIMORE، كان خطأ مدى الحركة من الجنب أقل من درجة واحدة، واتفق التوجيه مع القياس المرجعي في 99% من التكرارات (هندسة الكاميرا فقط، دون فيديو حقيقي).',
  },
};

export function packCopy(pack: ExercisePack): PackCopy {
  const copy = PACK_COPY[pack.packId];
  if (!copy) {
    throw new Error(`no Arabic wording for ${pack.packId}`);
  }
  return copy;
}

export function packById(packId: string): ExercisePack {
  const pack = EXERCISE_PACKS.find((item) => item.packId === packId);
  if (!pack) {
    throw new Error(`unknown exercise ${packId}`);
  }
  return pack;
}

/** Every angle of the pack for one side, primary first. */
export function resolveAngles(pack: ExercisePack, side: Side): ResolvedAngle[] {
  const primary = resolvePrimaryAngle(pack, side);
  const others = pack.angles
    .filter((angle) => angle.name !== pack.primaryAngle)
    .map((angle) => ({
      name: angle.name,
      landmarks: [
        concreteLandmark(angle.triplet[0], side),
        concreteLandmark(angle.triplet[1], side),
        concreteLandmark(angle.triplet[2], side),
      ] as [string, string, string],
      transform: angle.transform,
    }));
  return [primary, ...others];
}

/** Wording when a secondary (posture) angle differs from the reference. */
export const POSTURE_COPY: Readonly<
  Record<string, { textAr: string; spokenAr: string }>
> = {
  hip_flexion: {
    textAr: 'ميل جذعك مختلف عن المرجع. حافظ على صدرك مرفوعًا كما في المرجع.',
    spokenAr: 'ارفع صدرك',
  },
  trunk_hip_flexion: {
    textAr: 'ميل جذعك مختلف عن المرجع. حافظ على جذعك مستقيمًا كما في المرجع.',
    spokenAr: 'جذعك مستقيم',
  },
  trunk_lean: {
    textAr: 'جذعك يميل للجنب أكثر من المرجع. حافظ على جذعك مستقيمًا.',
    spokenAr: 'لا تمل بجذعك',
  },
  elbow_flexion: {
    textAr: 'وضع كوعك مختلف عن المرجع. حافظ على ذراعك مفرودة كما في المرجع.',
    spokenAr: 'افرد ذراعك',
  },
};

/** Landmark names the pack needs for one side. */
export function requiredLandmarks(pack: ExercisePack, side: Side): string[] {
  return pack.requiredLandmarks.map((token) => concreteLandmark(token, side));
}

export function concreteLandmark(token: string, side: Side): string {
  const own = side === 'left' ? 'LEFT' : 'RIGHT';
  const other = side === 'left' ? 'RIGHT' : 'LEFT';
  const name = token.startsWith('SIDE_')
    ? `${own}_${token.slice(5)}`
    : token.startsWith('OTHER_')
      ? `${other}_${token.slice(6)}`
      : token;
  if (!(name in MEDIAPIPE_INDEX)) {
    throw new Error(`unknown landmark ${name}`);
  }
  return name;
}

export function resolvePrimaryAngle(pack: ExercisePack, side: Side): ResolvedAngle {
  const angle = pack.angles.find((item) => item.name === pack.primaryAngle);
  if (!angle) {
    throw new Error(`pack ${pack.packId} has no angle ${pack.primaryAngle}`);
  }
  const [a, b, c] = angle.triplet;
  return {
    name: angle.name,
    landmarks: [
      concreteLandmark(a, side),
      concreteLandmark(b, side),
      concreteLandmark(c, side),
    ],
    transform: angle.transform,
  };
}

export function transformAngle(
  interior: number | null,
  transform: AngleTransform,
): number | null {
  if (interior === null) {
    return null;
  }
  if (transform === 'interior') {
    return interior;
  }
  if (transform === 'flexion') {
    return 180 - interior;
  }
  return interior - 90;
}

/** Pack angle from pixel coordinates keyed by landmark name. */
export function packAngle(
  points: Readonly<Record<string, Point2D | undefined>>,
  angle: ResolvedAngle,
): number | null {
  const [a, b, c] = angle.landmarks.map((name) => points[name]);
  if (!a || !b || !c) {
    return null;
  }
  return transformAngle(angleDegrees(a, b, c), angle.transform);
}

/**
 * Camera-view gate (docs/decisions.md, 2026-10-29).
 *
 * Frontalness = horizontal shoulder width / torso length in pixels: near 0
 * when the person stands side-on to the camera, about 0.6-0.8 facing it.
 * A pack declares the view it needs; the coach measures only when the clip's
 * median frontalness matches. Cut-offs come from rules/gate/view-rule.json,
 * fitted on REHAB24-6 view labels only (research value, not clinical).
 */
import viewRuleJson from '../../../rules/gate/view-rule.json';
import { median, pixelPoints, type PoseFrame } from './poseFrames';

export interface ViewRule {
  side_pack_max_frontalness: number;
  front_pack_min_frontalness: number;
}

export const VIEW_RULE: ViewRule = viewRuleJson;

export type ViewVerdict = 'MATCHES' | 'TOO_FRONTAL' | 'TOO_SIDEWAYS' | 'UNKNOWN';

export interface ViewCheck {
  verdict: ViewVerdict;
  expectedView: string;
  frontalness: number | null;
  cutoff: number;
}

export function frontalness(frame: PoseFrame): number | null {
  const p = pixelPoints(frame);
  const ls = p.LEFT_SHOULDER;
  const rs = p.RIGHT_SHOULDER;
  const lh = p.LEFT_HIP;
  const rh = p.RIGHT_HIP;
  if (!ls || !rs || !lh || !rh) {
    return null;
  }
  const midShoulder = [(ls[0] + rs[0]) / 2, (ls[1] + rs[1]) / 2] as const;
  const midHip = [(lh[0] + rh[0]) / 2, (lh[1] + rh[1]) / 2] as const;
  const torso = Math.hypot(midShoulder[0] - midHip[0], midShoulder[1] - midHip[1]);
  if (torso < 1e-6) {
    return null;
  }
  return Math.abs(ls[0] - rs[0]) / torso;
}

export function checkView(
  frames: readonly PoseFrame[],
  packView: string,
  rule: ViewRule = VIEW_RULE,
): ViewCheck {
  const values = frames.map(frontalness).filter((v): v is number => v !== null);
  const value = median(values);
  const isSidePack = packView === 'side';
  const cutoff = isSidePack
    ? rule.side_pack_max_frontalness
    : rule.front_pack_min_frontalness;
  if (value === null) {
    return { verdict: 'UNKNOWN', expectedView: packView, frontalness: null, cutoff };
  }
  let verdict: ViewVerdict;
  if (isSidePack) {
    verdict = value <= cutoff ? 'MATCHES' : 'TOO_FRONTAL';
  } else {
    verdict = value >= cutoff ? 'MATCHES' : 'TOO_SIDEWAYS';
  }
  return { verdict, expectedView: packView, frontalness: value, cutoff };
}

export function viewAdviceAr(check: ViewCheck): string {
  switch (check.verdict) {
    case 'MATCHES':
      return 'زاوية التصوير مناسبة لهذا التمرين.';
    case 'TOO_FRONTAL':
      return 'لا أراك جيدًا من هذه الزاوية: ضع الهاتف على جانبك بحيث يظهر جسمك من الجنب.';
    case 'TOO_SIDEWAYS':
      return 'لا أراك جيدًا من هذه الزاوية: واجه الهاتف مباشرة.';
    default:
      return 'لا أرى جسمك بوضوح: ابتعد قليلًا حتى يظهر جسمك كاملًا من الكتفين إلى القدمين.';
  }
}

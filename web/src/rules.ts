import type { CaptureQualityResult } from './captureQuality';

export type RuleOperator = 'lt' | 'lte' | 'eq' | 'gte' | 'gt';
export type RuleStatus = 'provisional' | 'approved';
export type RuleProvenance = 'default' | 'dataset-derived' | 'clinician';

export interface ExerciseRule {
  ruleId: string;
  version: number;
  exercise: string;
  view: string;
  metric: string;
  operator: RuleOperator;
  value: number;
  cue: {
    ar: string;
    en: string;
  };
  status: RuleStatus;
  provenance: RuleProvenance;
  approvedBy: string | null;
  approvedAt: string | null;
}

export interface RuleEvaluationInput {
  exercise: string;
  view: string;
  captureQuality: CaptureQualityResult;
  metrics: Readonly<Record<string, number | undefined>>;
}

export type RuleEvaluation =
  | {
      status: 'CANNOT_ASSESS';
      reasonCodes: readonly string[];
      matchedRules: readonly [];
      showPrototypeWarning: false;
    }
  | {
      status: 'NO_RULES_CONFIGURED';
      reasonCodes: readonly ['NO_RULES_CONFIGURED'];
      matchedRules: readonly [];
      showPrototypeWarning: false;
    }
  | {
      status: 'ASSESSED';
      reasonCodes: readonly [];
      matchedRules: readonly {
        ruleId: string;
        version: number;
        cue: ExerciseRule['cue'];
        status: RuleStatus;
        provenance: RuleProvenance;
      }[];
      showPrototypeWarning: boolean;
    };

const APPROVAL_PLACEHOLDERS = new Set([
  'demo physio',
  'not a real clinician',
  'tbd',
  'unknown',
]);

function validateRule(rule: ExerciseRule): void {
  if (
    !rule.ruleId.trim() ||
    !Number.isInteger(rule.version) ||
    rule.version < 1 ||
    !rule.exercise.trim() ||
    !rule.view.trim() ||
    !rule.metric.trim() ||
    !Number.isFinite(rule.value) ||
    !rule.cue.ar.trim() ||
    !rule.cue.en.trim()
  ) {
    throw new Error(`Invalid rule configuration: ${rule.ruleId || '(missing ruleId)'}`);
  }

  if (
    !['lt', 'lte', 'eq', 'gte', 'gt'].includes(rule.operator) ||
    !['provisional', 'approved'].includes(rule.status) ||
    !['default', 'dataset-derived', 'clinician'].includes(rule.provenance)
  ) {
    throw new Error(`Invalid rule metadata: ${rule.ruleId}`);
  }

  if (rule.status === 'approved') {
    const approver = rule.approvedBy?.trim();
    const approvedAt = rule.approvedAt;
    if (
      rule.provenance !== 'clinician' ||
      !approver ||
      [...APPROVAL_PLACEHOLDERS].some((placeholder) =>
        approver.toLowerCase().includes(placeholder),
      ) ||
      !approvedAt ||
      !Number.isFinite(Date.parse(approvedAt))
    ) {
      throw new Error(
        `Approved rule requires a named clinician and timestamp: ${rule.ruleId}`,
      );
    }
  } else if (rule.approvedBy !== null || rule.approvedAt !== null) {
    throw new Error(
      `Provisional rule cannot include approval metadata: ${rule.ruleId}`,
    );
  }
}

function matches(value: number, operator: RuleOperator, threshold: number): boolean {
  switch (operator) {
    case 'lt':
      return value < threshold;
    case 'lte':
      return value <= threshold;
    case 'eq':
      return value === threshold;
    case 'gte':
      return value >= threshold;
    case 'gt':
      return value > threshold;
  }
}

export function evaluateRules(
  rules: readonly ExerciseRule[],
  input: RuleEvaluationInput,
): RuleEvaluation {
  const seenRuleIds = new Set<string>();
  for (const rule of rules) {
    validateRule(rule);
    if (seenRuleIds.has(rule.ruleId)) {
      throw new Error(`Multiple active versions for rule: ${rule.ruleId}`);
    }
    seenRuleIds.add(rule.ruleId);
  }

  if (input.captureQuality.status === 'CANNOT_ASSESS') {
    return {
      status: 'CANNOT_ASSESS',
      reasonCodes: input.captureQuality.reasonCodes,
      matchedRules: [],
      showPrototypeWarning: false,
    };
  }

  const applicableRules = rules.filter(
    (rule) => rule.exercise === input.exercise && rule.view === input.view,
  );
  if (applicableRules.length === 0) {
    return {
      status: 'NO_RULES_CONFIGURED',
      reasonCodes: ['NO_RULES_CONFIGURED'],
      matchedRules: [],
      showPrototypeWarning: false,
    };
  }

  const hasMissingMetric = applicableRules.some((rule) => {
    const value = input.metrics[rule.metric];
    return value === undefined || !Number.isFinite(value);
  });
  if (hasMissingMetric) {
    return {
      status: 'CANNOT_ASSESS',
      reasonCodes: ['RULE_METRIC_MISSING'],
      matchedRules: [],
      showPrototypeWarning: false,
    };
  }

  const matchedRules = applicableRules.flatMap((rule) => {
    const value = input.metrics[rule.metric];
    if (value === undefined) {
      return [];
    }
    return matches(value, rule.operator, rule.value)
      ? [
          {
            ruleId: rule.ruleId,
            version: rule.version,
            cue: rule.cue,
            status: rule.status,
            provenance: rule.provenance,
          },
        ]
      : [];
  });

  return {
    status: 'ASSESSED',
    reasonCodes: [],
    matchedRules,
    showPrototypeWarning: matchedRules.some((rule) => rule.status === 'provisional'),
  };
}

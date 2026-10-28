import { describe, expect, it } from 'vitest';
import { assessCaptureQuality } from './captureQuality';
import { evaluateRules, type ExerciseRule } from './rules';

const provisionalRule: ExerciseRule = {
  ruleId: 'DEMO-RANGE',
  version: 1,
  exercise: 'synthetic-exercise',
  view: 'synthetic-view',
  metric: 'synthetic-angle',
  operator: 'lt',
  value: 45,
  cue: { ar: 'مثال توضيحي', en: 'Illustrative example' },
  status: 'provisional',
  provenance: 'default',
  approvedBy: null,
  approvedAt: null,
};

const readyInput = {
  exercise: 'synthetic-exercise',
  view: 'synthetic-view',
  captureQuality: assessCaptureQuality(
    ['synthetic-joint'],
    { 'synthetic-joint': 1 },
    0.5,
  ),
  metrics: { 'synthetic-angle': 40 },
};

describe('evaluateRules', () => {
  it('returns matched rule provenance and requests the provisional warning', () => {
    expect(evaluateRules([provisionalRule], readyInput)).toEqual({
      status: 'ASSESSED',
      reasonCodes: [],
      matchedRules: [
        {
          ruleId: 'DEMO-RANGE',
          version: 1,
          cue: provisionalRule.cue,
          status: 'provisional',
          provenance: 'default',
        },
      ],
      showPrototypeWarning: true,
    });
  });

  it('never evaluates cues when capture quality cannot be assessed', () => {
    expect(
      evaluateRules([provisionalRule], {
        ...readyInput,
        captureQuality: assessCaptureQuality(['synthetic-joint'], {}, 0.5),
      }),
    ).toMatchObject({
      status: 'CANNOT_ASSESS',
      reasonCodes: ['REQUIRED_LANDMARK_MISSING'],
      matchedRules: [],
    });
  });

  it('abstains if an applicable rule metric is missing', () => {
    expect(
      evaluateRules([provisionalRule], {
        ...readyInput,
        metrics: {},
      }),
    ).toMatchObject({
      status: 'CANNOT_ASSESS',
      reasonCodes: ['RULE_METRIC_MISSING'],
      matchedRules: [],
    });
  });

  it('reports when no rule exists for the requested exercise and view', () => {
    expect(
      evaluateRules([provisionalRule], {
        ...readyInput,
        view: 'other-view',
      }),
    ).toMatchObject({
      status: 'NO_RULES_CONFIGURED',
      reasonCodes: ['NO_RULES_CONFIGURED'],
      matchedRules: [],
    });
  });

  it('rejects approval attributed to the demo physio', () => {
    expect(() =>
      evaluateRules(
        [
          {
            ...provisionalRule,
            status: 'approved',
            provenance: 'clinician',
            approvedBy: 'Demo Physio (not a real clinician)',
            approvedAt: '2026-10-24T00:00:00Z',
          },
        ],
        readyInput,
      ),
    ).toThrow(/named clinician and timestamp/);
  });

  it('rejects duplicate active versions of a rule', () => {
    expect(() =>
      evaluateRules([provisionalRule, { ...provisionalRule, version: 2 }], readyInput),
    ).toThrow(/Multiple active versions/);
  });
});

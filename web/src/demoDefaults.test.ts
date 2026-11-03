import { describe, expect, it } from 'vitest';
import { DEMO_DEFAULTS, PAIN_RED_FLAGS, sourceOf } from './demoDefaults';
import { EXERCISE_PACKS } from './exercise/exercisePack';
import { evaluatePainTriage } from './painTriage';

describe('literature demo defaults', () => {
  it('stays unreviewed and cites an https source for every value', () => {
    expect(DEMO_DEFAULTS.reviewedBy).toBeNull();
    const used = [
      DEMO_DEFAULTS.toleranceDeg.source,
      DEMO_DEFAULTS.homeReps.source,
      DEMO_DEFAULTS.feverTempC.source,
      DEMO_DEFAULTS.emergencyNumber.source,
      ...DEMO_DEFAULTS.painRedFlags.map((term) => term.source),
    ];
    for (const id of used) {
      expect(sourceOf(id).url).toMatch(/^https:\/\//);
      expect(sourceOf(id).citation.length).toBeGreaterThan(20);
    }
    for (const goal of EXERCISE_PACKS.flatMap((pack) => pack.literatureGoals ?? [])) {
      expect(goal.url).toMatch(/^https:\/\//);
    }
  });

  it('flags every red-flag phrase on its own', () => {
    for (const term of PAIN_RED_FLAGS) {
      const result = evaluatePainTriage({ text: term.phrase, lexicon: PAIN_RED_FLAGS });
      expect(result.matchedRuleIds).toContain(term.ruleId);
    }
  });

  it('does not flag an ordinary sentence', () => {
    const result = evaluatePainTriage({
      text: 'عملت التمرين النهارده وركبتي كويسة',
      lexicon: PAIN_RED_FLAGS,
    });
    expect(result.status).toBe('NO_CONFIGURED_FLAG_DETECTED');
  });
});

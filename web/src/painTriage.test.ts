import { describe, expect, it } from 'vitest';
import { evaluatePainTriage, normalizeArabicText } from './painTriage';

const lexicon = [{ ruleId: 'FLAG-1', phrase: 'تنميل' }];

describe('normalizeArabicText', () => {
  it('normalizes Arabic letter variants, diacritics, tatweel, and Arabic digits', () => {
    expect(normalizeArabicText('إِحْسَاسٌ بِالتَّنْمِيل ١٢٣')).toBe(
      'احساس بالتنميل 123',
    );
    expect(normalizeArabicText('على')).toBe('علي');
  });
});

describe('evaluatePainTriage', () => {
  it('always escalates a whole-phrase lexicon hit even when the model is negative', () => {
    expect(
      evaluatePainTriage({
        text: 'أشعر بتنميل في اليد',
        lexicon,
        modelFlag: false,
      }),
    ).toEqual({
      status: 'ESCALATE_FOR_REVIEW',
      reasonCodes: ['LEXICON_FLAG'],
      matchedRuleIds: ['FLAG-1'],
    });
  });

  it('allows a positive model signal to add a flag when the lexicon has no match', () => {
    expect(
      evaluatePainTriage({
        text: 'ألم بعد التمرين',
        lexicon,
        modelFlag: true,
      }),
    ).toEqual({
      status: 'ESCALATE_FOR_REVIEW',
      reasonCodes: ['MODEL_FLAG'],
      matchedRuleIds: [],
    });
  });

  it('does not match a phrase embedded inside a longer token', () => {
    expect(
      evaluatePainTriage({
        text: 'تنميلية',
        lexicon,
        modelFlag: false,
      }),
    ).toEqual({
      status: 'NO_CONFIGURED_FLAG_DETECTED',
      reasonCodes: [],
      matchedRuleIds: [],
    });
  });

  it('matches an Arabic flag term with a common attached one-letter clitic', () => {
    expect(
      evaluatePainTriage({
        text: 'أشعر بتنميل في اليد',
        lexicon,
        modelFlag: false,
      }),
    ).toMatchObject({
      status: 'ESCALATE_FOR_REVIEW',
      reasonCodes: ['LEXICON_FLAG'],
      matchedRuleIds: ['FLAG-1'],
    });
  });

  it('abstains on empty text or when no lexicon is configured', () => {
    expect(evaluatePainTriage({ text: '   ', lexicon })).toMatchObject({
      status: 'CANNOT_ASSESS',
      reasonCodes: ['PAIN_TEXT_EMPTY'],
    });
    expect(evaluatePainTriage({ text: 'أشعر بألم', lexicon: [] })).toMatchObject({
      status: 'CANNOT_ASSESS',
      reasonCodes: ['NO_LEXICON_CONFIGURED'],
    });
  });

  it('rejects duplicate or incomplete lexicon entries', () => {
    expect(() =>
      evaluatePainTriage({
        text: 'أشعر بتنميل',
        lexicon: [
          { ruleId: 'FLAG-1', phrase: 'تنميل' },
          { ruleId: 'FLAG-1', phrase: 'دوخة' },
        ],
      }),
    ).toThrow(/Duplicate pain flag rule ID/);
    expect(() =>
      evaluatePainTriage({
        text: 'أشعر بألم',
        lexicon: [{ ruleId: '', phrase: 'ألم' }],
      }),
    ).toThrow(/requires a rule ID and phrase/);
  });
});

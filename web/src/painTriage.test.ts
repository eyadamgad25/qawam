import { describe, expect, it } from 'vitest';
import {
  assertedText,
  evaluatePainTriage,
  normalizeArabicText,
  statesFever,
} from './painTriage';

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

  it('skips a clause that only says the symptom is absent, and keeps the rest', () => {
    const dizzy = [
      { ruleId: 'DIZZY', phrase: 'دوخة' },
      { ruleId: 'NUMB', phrase: 'تنميل' },
    ];
    const flags = (text: string) =>
      evaluatePainTriage({ text, lexicon: dizzy }).matchedRuleIds;
    expect(flags('مفيش دوخة الحمد لله')).toEqual([]);
    expect(flags('الجرح ناشف ومفيش دوخة')).toEqual([]);
    expect(flags('مفيش دوخة بس عندي تنميل')).toEqual(['NUMB']);
    expect(flags('مفيش دوخة، وعندي تنميل في رجلي')).toEqual(['NUMB']);
    expect(flags('جاتلي دوخة')).toEqual(['DIZZY']);
  });

  it('never treats inability, lost feeling, or a symptom not getting better as absent', () => {
    for (const text of [
      'مش قادر أتنفس',
      'مش حاسس برجلي',
      'مفيش نفس خالص',
      'مفيش إحساس في رجلي',
      'الورم مش بيخف',
      'وجع مش طبيعي',
    ]) {
      expect(assertedText(text), text).not.toBe('');
    }
    expect(assertedText('ركبتي مش وارمة النهارده')).toBe('');
    expect(assertedText('ولا دوخة ولا حاجة')).toBe('');
  });

  it('escalates a stated temperature at or above the threshold, only when asked to', () => {
    const fever = (text: string) =>
      evaluatePainTriage({ text, lexicon, feverThresholdC: 38 }).reasonCodes;
    expect(fever('قست الحرارة طلعت ٣٩')).toEqual(['TEMPERATURE_FLAG']);
    expect(fever('حرارتي 38.5')).toEqual(['TEMPERATURE_FLAG']);
    expect(fever('my temp is 38')).toEqual(['TEMPERATURE_FLAG']);
    expect(fever('الحرارة ٣٧ ونص')).toEqual([]);
    expect(fever('عملت 40 تكرار')).toEqual([]);
    expect(fever('مفيش حرارة 39')).toEqual([]);
    expect(
      evaluatePainTriage({ text: 'قست الحرارة طلعت ٣٩', lexicon }).reasonCodes,
    ).toEqual([]);
    expect(statesFever('حرارتي 385', 38)).toBe(false);
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

export interface PainFlagTerm {
  ruleId: string;
  phrase: string;
}

export type PainTriageReasonCode =
  'LEXICON_FLAG' | 'MODEL_FLAG' | 'PAIN_TEXT_EMPTY' | 'NO_LEXICON_CONFIGURED';

export type PainTriageResult =
  | {
      status: 'ESCALATE_FOR_REVIEW';
      reasonCodes: readonly ('LEXICON_FLAG' | 'MODEL_FLAG')[];
      matchedRuleIds: readonly string[];
    }
  | {
      status: 'NO_CONFIGURED_FLAG_DETECTED';
      reasonCodes: readonly [];
      matchedRuleIds: readonly [];
    }
  | {
      status: 'CANNOT_ASSESS';
      reasonCodes: readonly ('PAIN_TEXT_EMPTY' | 'NO_LEXICON_CONFIGURED')[];
      matchedRuleIds: readonly [];
    };

export interface PainTriageInput {
  text: string;
  lexicon: readonly PainFlagTerm[];
  modelFlag?: boolean;
}

export function normalizeArabicText(text: string): string {
  return text
    .normalize('NFKC')
    .replace(/[\u064B-\u065F\u0670\u06D6-\u06ED]/gu, '')
    .replace(/\u0640/gu, '')
    .replace(/[أإآٱ]/gu, 'ا')
    .replace(/[ىئ]/gu, 'ي')
    .replace(/[٠-٩]/gu, (digit) => String(digit.charCodeAt(0) - 0x0660))
    .replace(/[۰-۹]/gu, (digit) => String(digit.charCodeAt(0) - 0x06f0))
    .replace(/\s+/gu, ' ')
    .trim()
    .toLowerCase();
}

export function evaluatePainTriage(input: PainTriageInput): PainTriageResult {
  if (typeof input.text !== 'string' || !input.text.trim()) {
    return {
      status: 'CANNOT_ASSESS',
      reasonCodes: ['PAIN_TEXT_EMPTY'],
      matchedRuleIds: [],
    };
  }
  if (input.lexicon.length === 0) {
    return {
      status: 'CANNOT_ASSESS',
      reasonCodes: ['NO_LEXICON_CONFIGURED'],
      matchedRuleIds: [],
    };
  }

  validateLexicon(input.lexicon);
  if (typeof input.modelFlag !== 'undefined' && typeof input.modelFlag !== 'boolean') {
    throw new Error('modelFlag must be a boolean when supplied');
  }

  const normalizedText = normalizeArabicText(input.text);
  const matchedRuleIds = input.lexicon
    .filter(({ phrase }) =>
      containsWholePhrase(normalizedText, normalizeArabicText(phrase)),
    )
    .map(({ ruleId }) => ruleId);
  const reasonCodes: ('LEXICON_FLAG' | 'MODEL_FLAG')[] = [];

  if (matchedRuleIds.length > 0) {
    reasonCodes.push('LEXICON_FLAG');
  }
  if (input.modelFlag === true) {
    reasonCodes.push('MODEL_FLAG');
  }

  if (reasonCodes.length > 0) {
    return {
      status: 'ESCALATE_FOR_REVIEW',
      reasonCodes,
      matchedRuleIds,
    };
  }
  return {
    status: 'NO_CONFIGURED_FLAG_DETECTED',
    reasonCodes: [],
    matchedRuleIds: [],
  };
}

function validateLexicon(lexicon: readonly PainFlagTerm[]): void {
  const seenIds = new Set<string>();
  for (const term of lexicon) {
    if (!term.ruleId.trim() || !normalizeArabicText(term.phrase)) {
      throw new Error('Each pain flag term requires a rule ID and phrase');
    }
    if (seenIds.has(term.ruleId)) {
      throw new Error(`Duplicate pain flag rule ID: ${term.ruleId}`);
    }
    seenIds.add(term.ruleId);
  }
}

function containsWholePhrase(text: string, phrase: string): boolean {
  const escapedPhrase = phrase.replace(/[.*+?^${}()|[\]\\]/gu, '\\$&');
  const optionalArabicClitic = /^\p{Script=Arabic}/u.test(phrase)
    ? '(?:[وفبكلس])?'
    : '';
  return new RegExp(
    `(^|[^\\p{L}\\p{N}])${optionalArabicClitic}${escapedPhrase}(?=$|[^\\p{L}\\p{N}])`,
    'u',
  ).test(text);
}

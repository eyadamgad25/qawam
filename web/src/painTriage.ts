export interface PainFlagTerm {
  ruleId: string;
  phrase: string;
}

export type PainFlagReason = 'LEXICON_FLAG' | 'TEMPERATURE_FLAG' | 'MODEL_FLAG';

export type PainTriageReasonCode =
  PainFlagReason | 'PAIN_TEXT_EMPTY' | 'NO_LEXICON_CONFIGURED';

/** matchedRuleIds entry for the stated-temperature rule */
export const TEMPERATURE_RULE_ID = 'NHS-FEVER-TEMP';

export type PainTriageResult =
  | {
      status: 'ESCALATE_FOR_REVIEW';
      reasonCodes: readonly PainFlagReason[];
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
  /** escalate a note that names a temperature at or above this (deg C); off when absent */
  feverThresholdC?: number;
}

// "there is no ..." words; a clause starting with one (or with one as its second word,
// "ركبتي مش وارمة") says the symptom is absent
const NEGATORS = new Set([
  'مفيش',
  'مافيش',
  'مفيهوش',
  'مفيهاش',
  'مش',
  'مبقاش',
  'بدون',
  'ولا',
]);
// never treated as "absent", because these are red flags themselves: not being able to
// ("مش قادر اتنفس"), not feeling ("مش حاسس برجلي"), no breath / feeling ("مفيش نفس"),
// not getting better ("الورم مش بيخف") and abnormal ("وجع مش طبيعي")
const NEGATION_EXCEPTIONS = new Set([
  'قادر',
  'قادرة',
  'بقدر',
  'عارف',
  'عارفة',
  'لاقي',
  'لاقية',
  'حاسس',
  'حاسة',
  'حاسه',
  'مستحمل',
  'مستحملة',
  'متحمل',
  'نفس',
  'نفسي',
  'احساس',
  'حس',
  'قوة',
  'حركة',
  'بيخف',
  'بتخف',
  'بيروح',
  'بتروح',
  'بيقل',
  'بتقل',
  'بيهدي',
  'بتهدي',
  'طبيعي',
  'طبيعية',
]);
const CLAUSE_BREAKS = new Set(['بس', 'لكن', 'بعدين']);

function isNegator(token: string): boolean {
  return NEGATORS.has(token) || (token.startsWith('و') && NEGATORS.has(token.slice(1)));
}

function clauseIsNegated(clause: readonly string[]): boolean {
  const at = isNegator(clause[0] ?? '') ? 0 : isNegator(clause[1] ?? '') ? 1 : -1;
  return at >= 0 && !NEGATION_EXCEPTIONS.has(clause[at + 1] ?? '');
}

/**
 * The normalised note without clauses that only say a symptom is absent ("مفيش دوخة").
 * Clauses split at punctuation, "بس" / "لكن", and a "و" joined to a negator ("ومفيش").
 */
export function assertedText(text: string): string {
  const tokens = normalizeArabicText(text.replace(/[،,.;!؟?\n]/gu, ' | ')).split(' ');
  const clauses: string[][] = [[]];
  for (const token of tokens) {
    if (token === '|' || CLAUSE_BREAKS.has(token)) {
      clauses.push([]);
    } else if (
      token.startsWith('و') &&
      isNegator(token) &&
      clauses.at(-1)!.length > 0
    ) {
      clauses.push([NEGATORS.has(token) ? token : token.slice(1)]);
    } else {
      clauses.at(-1)!.push(token);
    }
  }
  return clauses
    .filter((clause) => clause.length > 0 && !clauseIsNegated(clause))
    .map((clause) => clause.join(' '))
    .join(' | ');
}

const TEMPERATURE_WORD = /حرار|سخون|سخن|حمي|درج|temp|fever/u;
const NUMBER = /(?<![\d.,])(\d{2})(?:[.,](\d))?(?![\d])/gu;

/** True if an asserted clause names a body temperature at or above the threshold. */
export function statesFever(asserted: string, thresholdC: number): boolean {
  return asserted.split(' | ').some(
    (clause) =>
      TEMPERATURE_WORD.test(clause) &&
      [...clause.matchAll(NUMBER)].some((m) => {
        const value = Number(`${m[1]}.${m[2] ?? '0'}`);
        return value >= thresholdC && value <= 43;
      }),
  );
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

  const asserted = assertedText(input.text);
  const matchedRuleIds = input.lexicon
    .filter(({ phrase }) => containsWholePhrase(asserted, normalizeArabicText(phrase)))
    .map(({ ruleId }) => ruleId);
  const reasonCodes: PainFlagReason[] = [];

  if (matchedRuleIds.length > 0) {
    reasonCodes.push('LEXICON_FLAG');
  }
  if (
    typeof input.feverThresholdC === 'number' &&
    statesFever(asserted, input.feverThresholdC)
  ) {
    reasonCodes.push('TEMPERATURE_FLAG');
    matchedRuleIds.push(TEMPERATURE_RULE_ID);
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

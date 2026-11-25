/**
 * On-device pain red-flag model (painModel.json, written by ml/pain/train_shifaa_model.py --export).
 *
 * Logistic regression on character n-grams of the normalised note. It only ever adds
 * flags: the app escalates when the word list OR the model flags (evaluatePainTriage's
 * modelFlag), so the model can never hide a word-list match. Trained on titles of published
 * Arabic consultations (Shifaa) and synthetic notes; not reviewed by a clinician.
 */
import modelJson from './painModel.json';
import { assertedText, normalizeArabicText } from './painTriage';

interface PainModel {
  ngram: [number, number];
  bias: number;
  threshold: number;
  weights: Record<string, number>;
  checks: { text: string; score: number }[];
}

export const PAIN_MODEL = modelJson as unknown as PainModel;

/**
 * The whole check on 250 real consultation titles labelled blind by a non-clinician
 * (docs/experiments.md, 2026-11-25). Shown to the user before the check can be used;
 * change it only together with a new test.
 */
export const PAIN_TEST = {
  signs: 94,
  missed: 8,
  targetSigns: 26,
  targetMissed: 6,
  ordinary: 156,
  falseAlarms: 29,
} as const;

/** Same n-grams as ml/pain/pain_text.py char_ngrams (code points, one space of padding). */
export function charNgrams(text: string): Set<string> {
  const chars = Array.from(` ${normalizeArabicText(text)} `);
  const [min, max] = PAIN_MODEL.ngram;
  const grams = new Set<string>();
  for (let n = min; n <= max; n += 1) {
    for (let i = 0; i + n <= chars.length; i += 1) {
      grams.add(chars.slice(i, i + n).join(''));
    }
  }
  return grams;
}

/** Log-odds that the note is a red flag. */
export function painModelScore(text: string): number {
  const grams = charNgrams(text);
  let sum = 0;
  for (const gram of grams) {
    sum += PAIN_MODEL.weights[gram] ?? 0;
  }
  return PAIN_MODEL.bias + sum / Math.sqrt(grams.size);
}

/**
 * Flags only if both the whole note and its asserted clauses score as a red flag, so
 * "مفيش دوخة" alone is not flagged, and dropping "مش أكتر" cannot turn a mild note into one.
 */
export function painModelFlags(text: string): boolean {
  const asserted = assertedText(text).replaceAll(' | ', ' ');
  return (
    asserted !== '' &&
    painModelScore(text) > PAIN_MODEL.threshold &&
    painModelScore(asserted) > PAIN_MODEL.threshold
  );
}

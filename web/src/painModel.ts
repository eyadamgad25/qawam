/**
 * On-device pain red-flag model (painModel.json, trained by ml/pain/train_flag_model.py).
 *
 * Logistic regression on character n-grams of the normalised note. It only ever adds
 * flags: the app escalates when the word list OR the model flags (evaluatePainTriage's
 * modelFlag), so the model can never hide a word-list match. Trained on synthetic notes.
 */
import modelJson from './painModel.json';
import { normalizeArabicText } from './painTriage';

interface PainModel {
  ngram: [number, number];
  bias: number;
  threshold: number;
  weights: Record<string, number>;
  checks: { text: string; score: number }[];
}

export const PAIN_MODEL = modelJson as unknown as PainModel;

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

export function painModelFlags(text: string): boolean {
  return text.trim() !== '' && painModelScore(text) > PAIN_MODEL.threshold;
}

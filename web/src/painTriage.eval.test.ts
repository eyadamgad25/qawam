/**
 * Red-flag check scored on the synthetic Egyptian-Arabic notes (ml/pain/synthetic-notes.jsonl).
 * Prints recall / false alarms for the word list alone and for word list OR model (what the
 * app ships), per split, symptom and style; results go in docs/experiments.md.
 * The notes are synthetic and unreviewed: this measures coverage, not clinical safety.
 */
import { describe, expect, it } from 'vitest';
import notesJsonl from '../../ml/pain/synthetic-notes.jsonl?raw';
import { DEMO_DEFAULTS, PAIN_RED_FLAGS } from './demoDefaults';
import { PAIN_MODEL, painModelFlags, painModelScore } from './painModel';
import { evaluatePainTriage } from './painTriage';

interface Note {
  id: string;
  split: 'dev' | 'test';
  text: string;
  red_flag: boolean;
  symptom: string | null;
  style: string;
}

const NOTES: Note[] = notesJsonl
  .split('\n')
  .filter((line) => line.trim())
  .map((line) => JSON.parse(line) as Note);

const escalates = (note: Note, withModel: boolean) =>
  evaluatePainTriage({
    text: note.text,
    lexicon: PAIN_RED_FLAGS,
    modelFlag: withModel && painModelFlags(note.text),
    ...(withModel ? { feverThresholdC: DEMO_DEFAULTS.feverTempC.value } : {}),
  }).status === 'ESCALATE_FOR_REVIEW';

describe('red-flag check on synthetic notes', () => {
  it('reports recall and false alarms, word list vs word list OR model', () => {
    const lines: string[] = [];
    for (const withModel of [false, true]) {
      const rate = (notes: Note[]) =>
        `${notes.filter((n) => escalates(n, withModel)).length} / ${notes.length}`;
      const groups = (key: 'symptom' | 'style', notes: Note[]) =>
        [...new Set(notes.map((n) => n[key] ?? '-'))].map(
          (value) =>
            `  ${value}: ${rate(notes.filter((n) => (n[key] ?? '-') === value))}`,
        );
      lines.push(withModel ? '== word list OR model' : '== word list only');
      for (const split of ['dev', 'test', 'all'] as const) {
        const part = NOTES.filter((n) => split === 'all' || n.split === split);
        lines.push(
          `${split}: red flags caught ${rate(part.filter((n) => n.red_flag))}, ` +
            `false alarms ${rate(part.filter((n) => !n.red_flag))}`,
        );
      }
      lines.push(
        'caught by symptom:',
        ...groups(
          'symptom',
          NOTES.filter((n) => n.red_flag),
        ),
      );
      lines.push(
        'caught by style:',
        ...groups(
          'style',
          NOTES.filter((n) => n.red_flag),
        ),
      );
      lines.push(
        'flagged non-flags by style:',
        ...groups(
          'style',
          NOTES.filter((n) => !n.red_flag),
        ),
      );
    }
    lines.push(
      'still missed (dev only):',
      ...NOTES.filter(
        (n) => n.split === 'dev' && n.red_flag && !escalates(n, true),
      ).map((n) => `  ${n.id} ${n.style} ${n.text}`),
      'false alarms (dev only):',
      ...NOTES.filter(
        (n) => n.split === 'dev' && !n.red_flag && escalates(n, true),
      ).map((n) => `  ${n.id} ${n.style} ${n.text}`),
    );
    console.log(lines.join('\n'));
    expect(NOTES.length).toBeGreaterThan(100);
  });

  it('catches every note written in the word list’s own wording', () => {
    for (const note of NOTES.filter((n) => n.style === 'lexicon')) {
      expect(escalates(note, false), note.text).toBe(true);
    }
  });

  it('never hides a word-list flag', () => {
    for (const note of NOTES.filter((n) => escalates(n, false))) {
      expect(escalates(note, true), note.text).toBe(true);
    }
  });

  it('scores exactly like the Python trainer', () => {
    for (const check of PAIN_MODEL.checks) {
      expect(painModelScore(check.text)).toBeCloseTo(check.score, 4);
    }
  });
});

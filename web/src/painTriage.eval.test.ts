/**
 * Red-flag check scored on the synthetic Egyptian-Arabic notes (ml/pain/synthetic-notes.jsonl).
 * Prints recall / false alarms per split, symptom and style; results go in docs/experiments.md.
 * The notes are synthetic and unreviewed: this measures coverage, not clinical safety.
 */
import { describe, expect, it } from 'vitest';
import notesJsonl from '../../ml/pain/synthetic-notes.jsonl?raw';
import { PAIN_RED_FLAGS } from './demoDefaults';
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

const flagged = (note: Note) =>
  evaluatePainTriage({ text: note.text, lexicon: PAIN_RED_FLAGS }).status ===
  'ESCALATE_FOR_REVIEW';

function rate(notes: Note[]): string {
  const hits = notes.filter(flagged).length;
  return `${hits} / ${notes.length}`;
}

describe('red-flag check on synthetic notes', () => {
  it('reports recall and false alarms', () => {
    const lines: string[] = [];
    for (const split of ['dev', 'test', 'all'] as const) {
      const part = NOTES.filter((n) => split === 'all' || n.split === split);
      lines.push(
        `${split}: red flags caught ${rate(part.filter((n) => n.red_flag))}, ` +
          `false alarms ${rate(part.filter((n) => !n.red_flag))}`,
      );
    }
    const groups = (key: 'symptom' | 'style', notes: Note[]) =>
      [...new Set(notes.map((n) => n[key] ?? '-'))].map(
        (value) => `  ${value}: ${rate(notes.filter((n) => (n[key] ?? '-') === value))}`,
      );
    lines.push('red flags caught by symptom:', ...groups('symptom', NOTES.filter((n) => n.red_flag)));
    lines.push('red flags caught by style:', ...groups('style', NOTES.filter((n) => n.red_flag)));
    lines.push('flagged among non-flags by style:', ...groups('style', NOTES.filter((n) => !n.red_flag)));
    lines.push(
      'missed (dev only):',
      ...NOTES.filter((n) => n.split === 'dev' && n.red_flag && !flagged(n)).map(
        (n) => `  ${n.id} ${n.style} ${n.text}`,
      ),
    );
    console.log(lines.join('\n'));
    expect(NOTES.length).toBeGreaterThan(100);
  });

  it('catches every note written in the lexicon’s own wording', () => {
    for (const note of NOTES.filter((n) => n.style === 'lexicon')) {
      expect(flagged(note), note.text).toBe(true);
    }
  });
});

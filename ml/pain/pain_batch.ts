// Runs the app's own pain check on a JSON list of texts (used by shifaa_eval.py).
import { readFileSync, writeFileSync } from 'node:fs';
import { DEMO_DEFAULTS, PAIN_RED_FLAGS } from '../../web/src/demoDefaults';
import { PAIN_MODEL, painModelFlags, painModelScore } from '../../web/src/painModel';
import { evaluatePainTriage } from '../../web/src/painTriage';

const [, , source, result, model] = process.argv;
if (model) {
  Object.assign(PAIN_MODEL, JSON.parse(readFileSync(model, 'utf8')));
}
const texts = JSON.parse(readFileSync(source!, 'utf8')) as string[];
const rows = texts.map((text) => {
  const { reasonCodes } = evaluatePainTriage({
    text,
    lexicon: PAIN_RED_FLAGS,
    feverThresholdC: DEMO_DEFAULTS.feverTempC.value,
  });
  const codes: readonly string[] = reasonCodes;
  return {
    list: codes.includes('LEXICON_FLAG'),
    temp: codes.includes('TEMPERATURE_FLAG'),
    model: painModelFlags(text),
    score: painModelScore(text),
  };
});
writeFileSync(result!, JSON.stringify(rows));

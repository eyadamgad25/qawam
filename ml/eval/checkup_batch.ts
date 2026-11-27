/**
 * Runs the app's check-up timing on recorded body points, for ml/eval/checkup_eval.py.
 *   node checkupBatch.cjs <input.json: {kind, files}> <output.json>
 * Start = first movement, because recorded videos have no "go".
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { analyseCheckup, type CheckupKind } from '../../web/src/checkup/checkupTiming';
import type { PoseFrame } from '../../web/src/exercise/poseFrames';

const [input, output] = process.argv.slice(2);
const job = JSON.parse(readFileSync(input!, 'utf-8')) as { kind: CheckupKind; files: string[] };
const results = job.files.map((file) => {
  const frames = JSON.parse(readFileSync(file, 'utf-8')) as PoseFrame[];
  return analyseCheckup(job.kind, frames, 'first-movement');
});
writeFileSync(output!, JSON.stringify(results));

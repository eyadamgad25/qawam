/**
 * Demo defaults taken from published sources (rules/literature/demo-defaults.json).
 *
 * No physiotherapist has reviewed them; every place that shows one must say so
 * (see LiteratureNote) and link its source.
 */
import demoDefaultsJson from '../../rules/literature/demo-defaults.json';
import type { PainFlagTerm } from './painTriage';

export interface LiteratureSource {
  citation: string;
  url: string;
}

interface SourcedValue<T> {
  value: T;
  source: string;
  finding: string;
}

interface DemoDefaults {
  reviewedBy: string | null;
  sources: Record<string, LiteratureSource>;
  toleranceDeg: SourcedValue<number>;
  homeReps: SourcedValue<number>;
  emergencyNumber: SourcedValue<string>;
  painRedFlags: (PainFlagTerm & { source: string; symptom: string })[];
}

export const DEMO_DEFAULTS = demoDefaultsJson as DemoDefaults;

export const PAIN_RED_FLAGS: readonly PainFlagTerm[] = DEMO_DEFAULTS.painRedFlags;

/** Shown next to every literature value in the demo. */
export const LITERATURE_LABEL_AR =
  'مأخوذة من مصدر منشور، ولم يراجعها أخصائي علاج طبيعي بعد';

export function sourceOf(id: string): LiteratureSource {
  const source = DEMO_DEFAULTS.sources[id];
  if (!source) {
    throw new Error(`unknown literature source ${id}`);
  }
  return source;
}

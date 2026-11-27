// @vitest-environment jsdom

import { beforeEach, describe, expect, it } from 'vitest';
import { checkupsFor, saveCheckup, type StoredCheckup } from './checkupStore';
import { checkupBundle } from './fhir';

const NONE = { sts5: false, sts30: false, tug: false };

function item(id: string, kind: StoredCheckup['kind'], value: number): StoredCheckup {
  return {
    id,
    patient: 'P1',
    kind,
    dateIso: `2026-11-2${id.length}T10:00:00.000Z`,
    ...(kind === 'sts30' ? { count: value } : { seconds: value }),
    engine: 'checkup-test',
  };
}

describe('check-up store', () => {
  beforeEach(() => localStorage.clear());

  it('keeps results per patient in date order', () => {
    saveCheckup(item('bb', 'sts5', 12.34));
    saveCheckup(item('a', 'tug', 9.1));
    saveCheckup({ ...item('c', 'sts5', 10), patient: 'P2' });
    expect(checkupsFor('P1').map((c) => c.id)).toEqual(['a', 'bb']);
  });
});

describe('FHIR export', () => {
  it('makes one Observation per result with a UCUM quantity', () => {
    const bundle = checkupBundle(
      [item('a', 'sts5', 12.34), item('b', 'sts30', 11)],
      NONE,
    );
    expect(bundle.resourceType).toBe('Bundle');
    expect(bundle.entry).toHaveLength(2);
    const [time, count] = bundle.entry.map((e) => e.resource);
    expect(time!.valueQuantity).toEqual({
      value: 12.3,
      unit: 's',
      system: 'http://unitsofmeasure.org',
      code: 's',
    });
    expect(count!.valueQuantity.code).toBe('{#}');
    expect(time!.note[0]!.text).toContain('not yet validated');
  });

  it('gives an empty bundle for a patient with no results', () => {
    expect(checkupBundle([], NONE).entry).toEqual([]);
  });
});

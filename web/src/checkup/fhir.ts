/**
 * HL7 FHIR R4 export of check-up results: one Observation per test, in a collection Bundle.
 * Codes are a local code system until LOINC codes are checked (spec: "codes from LOINC where a code exists").
 */
import type { CheckupKind } from './checkupTiming';
import type { StoredCheckup } from './checkupStore';

export const CHECKUP_CODE_SYSTEM =
  'https://eyadamgad25.github.io/qawam/fhir/CodeSystem/checkup';

export const CHECKUP_DISPLAY: Readonly<Record<CheckupKind, string>> = {
  sts5: 'Five times sit to stand test, time',
  sts30: '30 second sit to stand test, repetitions',
  tug: 'Timed Up and Go test, time',
};

export interface FhirObservation {
  resourceType: 'Observation';
  id: string;
  status: 'final';
  category: { coding: { system: string; code: string; display: string }[] }[];
  code: { coding: { system: string; code: string; display: string }[]; text: string };
  subject: { display: string };
  effectiveDateTime: string;
  valueQuantity: { value: number; unit: string; system: string; code: string };
  device: { display: string };
  method: { text: string };
  note: { text: string }[];
}

export interface FhirBundle {
  resourceType: 'Bundle';
  type: 'collection';
  timestamp: string;
  entry: { fullUrl: string; resource: FhirObservation }[];
}

function quantity(item: StoredCheckup): FhirObservation['valueQuantity'] | null {
  if (item.kind === 'sts30') {
    return item.count === undefined
      ? null
      : {
          value: item.count,
          unit: 'repetitions',
          system: 'http://unitsofmeasure.org',
          code: '{#}',
        };
  }
  return item.seconds === undefined
    ? null
    : {
        value: Math.round(item.seconds * 10) / 10,
        unit: 's',
        system: 'http://unitsofmeasure.org',
        code: 's',
      };
}

export function checkupObservation(
  item: StoredCheckup,
  validated: boolean,
): FhirObservation | null {
  const value = quantity(item);
  if (!value) {
    return null;
  }
  return {
    resourceType: 'Observation',
    id: item.id,
    status: 'final',
    category: [
      {
        coding: [
          {
            system: 'http://terminology.hl7.org/CodeSystem/observation-category',
            code: 'exam',
            display: 'Exam',
          },
        ],
      },
    ],
    code: {
      coding: [
        {
          system: CHECKUP_CODE_SYSTEM,
          code: item.kind,
          display: CHECKUP_DISPLAY[item.kind],
        },
      ],
      text: CHECKUP_DISPLAY[item.kind],
    },
    subject: { display: item.patient },
    effectiveDateTime: item.dateIso,
    valueQuantity: value,
    device: { display: `HomeRehab AI phone camera (${item.engine})` },
    method: {
      text: 'Phone camera, side view, body points only; timed by the app from start to seated',
    },
    note: [
      {
        text: validated
          ? 'Camera timing validated against a reference (see project docs). Not a diagnosis.'
          : 'Camera timing not yet validated. Not a diagnosis.',
      },
    ],
  };
}

export function checkupBundle(
  items: readonly StoredCheckup[],
  validated: Readonly<Record<CheckupKind, boolean>>,
  now = new Date(),
): FhirBundle {
  return {
    resourceType: 'Bundle',
    type: 'collection',
    timestamp: now.toISOString(),
    entry: items
      .map((item) => checkupObservation(item, validated[item.kind]))
      .filter((o): o is FhirObservation => o !== null)
      .map((resource) => ({ fullUrl: `urn:uuid:${resource.id}`, resource })),
  };
}

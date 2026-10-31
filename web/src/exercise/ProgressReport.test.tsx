// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import ProgressReport from './ProgressReport';
import { deletePatient, saveSession } from './sessionStore';

afterEach(() => {
  cleanup();
  deletePatient('Test');
});

describe('progress report', () => {
  it('shows an empty state, then sessions, a chart and a WhatsApp link', () => {
    const { rerender } = render(
      <ProgressReport patient="Test" packId="lower-limb.squat" refreshKey={0} />,
    );
    expect(screen.getByText(/لا توجد جلسات محفوظة/)).toBeTruthy();
    saveSession({
      id: 's1',
      patient: 'Test',
      packId: 'lower-limb.squat',
      dateIso: new Date().toISOString(),
      mode: 'live',
      side: 'left',
      toleranceDeg: 10,
      referenceRangeDeg: 80,
      goniometerDeg: null,
      reps: [
        {
          index: 0,
          assessed: true,
          cue: 'MATCHES_REFERENCE',
          rangeDeg: 78,
          peakAngleDeg: 82,
          depthDiffDeg: -2,
          pathDiffDeg: 4,
          posture: null,
          startSeconds: null,
          endSeconds: null,
        },
      ],
    });
    rerender(
      <ProgressReport patient="Test" packId="lower-limb.squat" refreshKey={1} />,
    );
    expect(screen.getByRole('img', { name: /مدى الحركة في كل جلسة/ })).toBeTruthy();
    const link = screen.getByRole('link', { name: /واتساب/ }) as HTMLAnchorElement;
    expect(link.href).toContain('https://wa.me/');
    expect(decodeURIComponent(link.href)).toContain('Test');
  });
});

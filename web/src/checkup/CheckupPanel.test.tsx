// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import CheckupPanel, { resultText } from './CheckupPanel';

afterEach(cleanup);

describe('CheckupPanel', () => {
  it('shows the chosen test and its instructions, marked not validated', () => {
    render(<CheckupPanel />);
    fireEvent.click(
      screen.getByRole('radio', { name: /Timed Up and Go|القيام والمشي/ }),
    );
    expect(screen.getByText(/3 m|٣ أمتار/, { selector: 'p' })).toBeTruthy();
    expect(screen.getByRole('note').textContent).toMatch(
      /not been validated|لم يُتحقق/,
    );
  });

  it('says why there is no result', () => {
    expect(resultText({ ok: false, kind: 'sts5', reason: 'too-few-stands' })).toMatch(
      /enough stand-ups|عدد الوقفات/,
    );
    expect(
      resultText({
        ok: true,
        kind: 'sts5',
        seconds: 12.34,
        startS: 0,
        endS: 12.34,
        standUps: [],
        sitDowns: [],
      }),
    ).toMatch(/12\.3/);
  });
});

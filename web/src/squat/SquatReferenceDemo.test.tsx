// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import SquatReferenceDemo, {
  CurveChart,
  formatDegrees,
  parseOptionalDegrees,
} from './SquatReferenceDemo';

afterEach(cleanup);

describe('squat reference screen', () => {
  it('starts with the camera and keeps the home step locked until a reference exists', () => {
    render(<SquatReferenceDemo />);
    expect(
      screen.getByRole('heading', { name: /سكوات مقارنةً بتكرارك المرجعي/ }),
    ).toBeTruthy();
    expect(screen.getAllByRole('button', { name: 'شغّل الكاميرا' })).toHaveLength(1);
    expect(screen.getByText(/سجّل فيديو مرجعيًا مناسبًا أولًا/)).toBeTruthy();
    expect(screen.getByText(/غير معتمد سريريًا/)).toBeTruthy();
    const [referenceFile, homeFile] = screen.getAllByRole('button', {
      name: 'من ملف فيديو',
    });
    fireEvent.click(referenceFile!);
    fireEvent.click(homeFile!);
    const reference = screen.getByLabelText('ملف فيديو المرجع') as HTMLInputElement;
    const home = screen.getByLabelText('ملف فيديو التمرين') as HTMLInputElement;
    expect(reference.disabled).toBe(false);
    expect(home.disabled).toBe(true);
  });

  it('parses physio-entered degrees and formats signed differences', () => {
    expect(parseOptionalDegrees('')).toBeNull();
    expect(parseOptionalDegrees(' 12.5 ')).toBe(12.5);
    expect(() => parseOptionalDegrees('0')).toThrow(/بين 0 و180/);
    expect(() => parseOptionalDegrees('abc')).toThrow();
    expect(formatDegrees(-12.4, true)).toBe('-12°');
    expect(formatDegrees(7.6, true)).toBe('+8°');
    expect(formatDegrees(7.6)).toBe('8°');
  });

  it('draws the reference and the rep as two curves', () => {
    const { container } = render(
      <CurveChart reference={[0, 50, 90, 40, 0]} rep={[0, 30, 60, 20]} />,
    );
    expect(container.querySelectorAll('path')).toHaveLength(2);
  });
});

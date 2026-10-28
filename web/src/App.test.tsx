// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, describe, expect, it } from 'vitest';
import App, { SAFETY_NOTICE, SIMULATED_CANNOT_ASSESS, SIMULATED_SESSION } from './App';
import {
  formatClipDuration,
  parseManualRepCount,
  validateVideoDuration,
} from './LocalVideoPoseDemo';

afterEach(cleanup);

describe('local video pose demo boundaries', () => {
  it('accepts only readable videos up to two minutes', () => {
    expect(validateVideoDuration(120)).toBeNull();
    expect(validateVideoDuration(120.1)).toContain('دقيقتان');
    expect(validateVideoDuration(Number.NaN)).toContain('تعذّر');
  });

  it('formats the clip duration in a compact minutes:seconds form', () => {
    expect(formatClipDuration(0)).toBe('0:00');
    expect(formatClipDuration(9.9)).toBe('0:09');
    expect(formatClipDuration(82)).toBe('1:22');
    expect(() => formatClipDuration(Number.NaN)).toThrow(/finite/);
  });

  it('parses an optional non-negative integer manual rep count', () => {
    expect(parseManualRepCount('')).toBeNull();
    expect(parseManualRepCount('0')).toBe(0);
    expect(parseManualRepCount('8')).toBe(8);
    expect(() => parseManualRepCount('-1')).toThrow(/غير سالب/);
    expect(() => parseManualRepCount('1.5')).toThrow(/صحيح/);
  });

  it('discloses the experimental mapping and thresholds beside the live counter', () => {
    render(<App />);

    expect(screen.getByText(/خريطة النقاط والحدود التجريبية/)).toBeTruthy();
    expect(
      screen.getByText(/لم تُراجع طبيًا أو تُتحقق مقابل مجموعة بيانات/),
    ).toBeTruthy();
    expect(screen.getByText(/11\/15\/23/)).toBeTruthy();
    expect(screen.getByText(/45°/)).toBeTruthy();
    expect(screen.getByText(/120°/)).toBeTruthy();
    expect(screen.getByText(/0\.5/)).toBeTruthy();
    expect(screen.getByText(/هدف العرض 8 تكرارات للتجربة فقط/)).toBeTruthy();
    expect(screen.getByLabelText('جهة الذراع المراد تتبعها')).toBeTruthy();
    expect(
      screen.getByLabelText('عدد التكرارات الذي لاحظته يدويًا (اختياري للمقارنة)'),
    ).toBeTruthy();
  });

  it('offers automatic and explicit left/right arm selection', () => {
    render(<App />);

    const sideSelect = screen.getByLabelText('جهة الذراع المراد تتبعها');
    expect(sideSelect.querySelectorAll('option')).toHaveLength(3);
    fireEvent.change(sideSelect, { target: { value: 'left' } });
    expect((sideSelect as HTMLSelectElement).value).toBe('left');
  });
});

describe('prototype safety notice', () => {
  it('renders the warning on the first screen in Arabic and English', () => {
    const markup = renderToStaticMarkup(<App />);

    expect(markup).toContain('role="alert"');
    expect(markup).toContain(SAFETY_NOTICE.arabic);
    expect(markup).toContain(SAFETY_NOTICE.english);
    expect(markup).toContain('lang="ar"');
    expect(markup).toContain('lang="en"');
  });

  it('clearly labels demo outputs as simulated and not clinician-approved', () => {
    expect(SAFETY_NOTICE.arabic).toContain('محاكاة');
    expect(SAFETY_NOTICE.arabic).toContain('غير معتمد سريريًا');
    expect(SAFETY_NOTICE.arabic).toContain('قد يكون العدد خاطئًا');
    expect(SAFETY_NOTICE.english).toContain('simulated');
    expect(SAFETY_NOTICE.english).toContain('not clinically approved');
    expect(SAFETY_NOTICE.english).toContain('may be wrong');
  });
});

describe('simulated session scenarios', () => {
  it('defaults to cannot-assess and does not show a repetition count', () => {
    render(<App />);

    expect(screen.getByText(SIMULATED_CANNOT_ASSESS.arabic)).toBeTruthy();
    expect(screen.getByText('REQUIRED_LANDMARK_MISSING')).toBeTruthy();
    expect(screen.queryByText(String(SIMULATED_SESSION.repetitions))).toBeNull();
    expect(screen.getByText(/لم يتم رفع أو تحليل أي فيديو/)).toBeTruthy();
  });

  it('shows the simulated summary only after selecting the completed scenario', () => {
    render(<App />);

    fireEvent.click(screen.getByRole('button', { name: 'مثال: جلسة مكتملة' }));

    expect(screen.getByText(String(SIMULATED_SESSION.repetitions))).toBeTruthy();
    expect(screen.getByText(SIMULATED_SESSION.movementSummary)).toBeTruthy();
    expect(screen.getByText(SIMULATED_SESSION.englishMovementSummary)).toBeTruthy();
    expect(
      screen
        .getByRole('button', { name: 'مثال: جلسة مكتملة' })
        .getAttribute('aria-pressed'),
    ).toBe('true');
  });

  it('switches back to cannot-assess and removes the repetition count', () => {
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: 'مثال: جلسة مكتملة' }));
    fireEvent.click(screen.getByRole('button', { name: 'مثال: تعذّر التقييم' }));

    expect(screen.getByText(SIMULATED_CANNOT_ASSESS.english)).toBeTruthy();
    expect(screen.queryByText(String(SIMULATED_SESSION.repetitions))).toBeNull();
  });

  it('runs the synthetic angle pipeline demo and abstains on its low-visibility frame', () => {
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: 'شغّل المثال المصطنع' }));

    expect(screen.getByText(/اكتمل المثال:/).textContent).toContain('2 دورات مصطنعة');
    expect(screen.getByText('LOW_REQUIRED_LANDMARK_VISIBILITY')).toBeTruthy();
    expect(screen.getByText('CANNOT_ASSESS')).toBeTruthy();
    expect(screen.getByText('لا يستخدم الكاميرا')).toBeTruthy();
  });

  it('demonstrates Arabic lexicon matching with a test-only phrase', () => {
    render(<App />);
    fireEvent.change(screen.getByLabelText('عبارة الاختبار'), {
      target: { value: 'كلمة اختبَار' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'اختبر العبارة المصطنعة' }));

    expect(screen.getByText('ESCALATE_FOR_REVIEW')).toBeTruthy();
    expect(screen.getByText(/LEXICON_FLAG/)).toBeTruthy();
    expect(screen.getByText(/لا توجد قائمة طبية/)).toBeTruthy();
  });

  it('demonstrates that a simulated model flag cannot be suppressed', () => {
    render(<App />);
    fireEvent.change(screen.getByLabelText('عبارة الاختبار'), {
      target: { value: 'عبارة لا تطابق' },
    });
    fireEvent.click(screen.getByLabelText('محاكاة إشارة نموذج إيجابية (للاختبار فقط)'));
    fireEvent.click(screen.getByRole('button', { name: 'اختبر العبارة المصطنعة' }));

    expect(screen.getByText('ESCALATE_FOR_REVIEW')).toBeTruthy();
    expect(screen.getByText(/MODEL_FLAG/)).toBeTruthy();
    expect(screen.getByText(/عدم وجود إشارة لا يعني/)).toBeTruthy();
  });
});

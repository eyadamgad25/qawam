import { useState, type ReactNode } from 'react';
import {
  runSyntheticAnglePipelineDemo,
  type SyntheticFrameResult,
} from './anglePipelineDemo';
import { evaluatePainTriage, type PainTriageResult } from './painTriage';
import { painModelFlags } from './painModel';
import LocalVideoPoseDemo from './LocalVideoPoseDemo';
import ExerciseCoach from './exercise/ExerciseCoach';
import { DEMO_DEFAULTS, PAIN_RED_FLAGS, sourceOf } from './demoDefaults';
import LiteratureNote from './LiteratureNote';
import { setLang, tr, useLang } from './i18n';

export const SAFETY_NOTICE = {
  arabic:
    'هذا نموذج تعليمي أولي غير معتمد سريريًا. أمثلة الجلسات محاكاة، وعدّاد الفيديو نتيجة خوارزمية تجريبية غير متحقق منها وليست صادرة عن طبيب أو أخصائي علاج طبيعي. قد يكون العدد خاطئًا؛ لا تستخدمه لاتخاذ قرارات صحية أو لتغيير خطة علاجك. القيم الافتراضية (هامش السماح، عدد التكرارات، الأهداف، علامات الخطر) مأخوذة من دراسات وإرشادات منشورة، والمصدر مكتوب بجانب كل قيمة، ولم يراجعها أخصائي علاج طبيعي بعد.',
  english:
    'This is an educational prototype and is not clinically approved. Session examples are simulated; the video counter is an unvalidated experimental algorithm, not a result from a doctor or physiotherapist, and may be wrong. Do not use it to make health decisions or change a care plan. Default values (tolerance, rep count, goals, red-flag words) come from published studies and guidelines, cited next to each value, and have not yet been reviewed by a physiotherapist.',
} as const;

export type DemoScenario = 'completed' | 'cannot-assess';

export const SIMULATED_SESSION = {
  repetitions: 8,
  duration: '00:42',
  movementSummary:
    'مثال محاكاة: تسلسل زوايا افتراضي أكمل ٨ دورات حركة. لم يتم تقييم صحة الأداء.',
  englishMovementSummary:
    'Simulated example: a synthetic angle sequence completed 8 movement cycles. Form was not assessed.',
} as const;

export const SIMULATED_CANNOT_ASSESS = {
  arabic:
    'محاكاة: بعض النقاط المطلوبة غير متاحة، لذلك لم نحلل الحركة ولم نحتسب تكرارات.',
  english:
    'Simulated: some required landmarks are unavailable, so movement was not analyzed and no repetitions were counted.',
} as const;

export type Tab = 'exercise' | 'pain' | 'about' | 'lab';

/** Outline icons (24px grid, stroke = currentColor); decorative, so hidden from screen readers. */
const ICONS: Record<Tab | 'shield' | 'globe', ReactNode> = {
  exercise: <path d="M6 8v8M3 10v4M18 8v8M21 10v4M6 12h12" />,
  pain: (
    <path d="M19 14c1.5-1.5 3-3.2 3-5.5A5.5 5.5 0 0 0 12 5a5.5 5.5 0 0 0-10 3.5c0 2.3 1.5 4 3 5.5l7 7Z M3.2 12H8l2-3 3 6 2-3h5.8" />
  ),
  about: <path d="M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20Z M12 16v-4 M12 8h.01" />,
  lab: (
    <path d="M10 2v7.5L4.5 19A2 2 0 0 0 6.2 22h11.6a2 2 0 0 0 1.7-3L14 9.5V2 M8.5 2h7 M7 16h10" />
  ),
  shield: <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z M12 8v4 M12 16h.01" />,
  globe: (
    <path d="M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20Z M2 12h20 M12 2a15 15 0 0 1 0 20 M12 2a15 15 0 0 0 0 20" />
  ),
};

function Icon({ name }: { name: keyof typeof ICONS }) {
  return (
    <svg
      className="icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {ICONS[name]}
    </svg>
  );
}

export default function App() {
  const lang = useLang();
  const [tab, setTab] = useState<Tab>('exercise');
  const [scenario, setScenario] = useState<DemoScenario>('cannot-assess');
  const [pipelineResults, setPipelineResults] = useState<SyntheticFrameResult[] | null>(
    null,
  );
  const [painDemoText, setPainDemoText] = useState('');
  const [painDemoResult, setPainDemoResult] = useState<PainTriageResult | null>(null);

  const tabs: { id: Tab; label: string }[] = [
    { id: 'exercise', label: tr('التمرين', 'Exercise') },
    { id: 'pain', label: tr('فحص الألم', 'Pain check') },
    { id: 'about', label: tr('عن التطبيق', 'About') },
    { id: 'lab', label: tr('تجارب تقنية', 'Lab') },
  ];

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-brand">
          <span className="app-logo" aria-hidden="true">
            H
          </span>
          <div>
            <h1>HomeRehab AI</h1>
            <p className="brand-kicker">
              {tr('مدرّب تمارين العلاج الطبيعي في البيت', 'Home physiotherapy coach')}
            </p>
          </div>
        </div>
        <button
          type="button"
          className="lang-toggle"
          onClick={() => setLang(lang === 'ar' ? 'en' : 'ar')}
          aria-label={lang === 'ar' ? 'Switch to English' : 'التبديل إلى العربية'}
        >
          <Icon name="globe" />
          <span lang={lang === 'ar' ? 'en' : 'ar'}>
            {lang === 'ar' ? 'English' : 'العربية'}
          </span>
        </button>
      </header>

      <section className="safety-notice" role="alert" aria-labelledby="notice-title">
        <Icon name="shield" />
        <div>
          <h2 id="notice-title">
            {tr(
              'نموذج تعليمي غير معتمد سريريًا. قد تكون النتائج خاطئة.',
              'Educational prototype, not clinically approved. Results may be wrong.',
            )}
          </h2>
          <details>
            <summary>{tr('اقرأ التنبيه كاملًا', 'Read the full notice')}</summary>
            <p lang={lang}>
              {lang === 'ar' ? SAFETY_NOTICE.arabic : SAFETY_NOTICE.english}
            </p>
          </details>
        </div>
      </section>

      <nav className="tab-bar" aria-label={tr('أقسام التطبيق', 'App sections')}>
        {tabs.map((item) => (
          <button
            key={item.id}
            type="button"
            className="tab-button"
            aria-current={tab === item.id ? 'page' : undefined}
            onClick={() => setTab(item.id)}
          >
            <Icon name={item.id} />
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      {/* Panels stay mounted so a recorded reference or camera session survives a tab switch. */}
      <main className="page-shell">
        <div hidden={tab !== 'exercise'}>
          <ExerciseCoach />
        </div>

        <div hidden={tab !== 'pain'}>
          <section className="session-summary" aria-labelledby="pain-demo-title">
            <div className="summary-heading">
              <div>
                <p className="summary-kicker">
                  {tr(
                    'تجربة · قائمة من مصادر منشورة',
                    'Prototype · list from published sources',
                  )}
                </p>
                <h2 id="pain-demo-title">
                  {tr(
                    'فحص علامات الخطر في وصف الألم',
                    'Red-flag check in your pain note',
                  )}
                </h2>
              </div>
              <span className="simulation-badge">
                {tr('لم يراجعها أخصائي', 'Not reviewed by a physio')}
              </span>
            </div>
            <p>
              {tr(
                `اكتب بالعامية كيف تشعر. نبحث عن ${PAIN_RED_FLAGS.length} عبارة خطر مأخوذة من إرشادات NHS بعد تغيير مفصل الركبة ومن قائمة المشروع. عدم وجود إشارة لا يعني أنك بخير. النص يبقى داخل الصفحة ولا يُحفظ أو يُرسل.`,
                `Write how you feel in Egyptian Arabic: the ${PAIN_RED_FLAGS.length} warning phrases come from NHS advice after knee replacement and the project list, and they are in Arabic only. No flag does not mean you are fine. The text stays on this page and is never saved or sent.`,
              )}{' '}
              <LiteratureNote source={sourceOf('nhsKnee')} />
            </p>
            <label className="pain-demo-label" htmlFor="pain-demo-text">
              {tr('صف ما تشعر به', 'Describe how you feel')}
            </label>
            <textarea
              id="pain-demo-text"
              value={painDemoText}
              onChange={(event) => setPainDemoText(event.target.value)}
              dir="rtl"
              rows={3}
              placeholder="مثال: عندي سخونية والجرح بينز"
            />
            <p className="pain-model-note">
              {tr(
                'يعمل معها نموذج صغير على جهازك يلتقط الصياغات الأخرى والفرانكو. يضيف تنبيهات فقط ولا يلغي أي عبارة من القائمة. دُرّب على عبارات مصطنعة، ولم يراجعه أخصائي.',
                'A small model on your device also catches other wordings, including Franco-Arabic. It only adds alerts and never cancels a phrase from the list. It was trained on synthetic notes and no physio has reviewed it.',
              )}
            </p>
            <button
              className="demo-run-button"
              type="button"
              onClick={() =>
                setPainDemoResult(
                  evaluatePainTriage({
                    text: painDemoText,
                    lexicon: PAIN_RED_FLAGS,
                    modelFlag: painModelFlags(painDemoText),
                    feverThresholdC: DEMO_DEFAULTS.feverTempC.value,
                  }),
                )
              }
            >
              {tr('افحص العبارة', 'Check the note')}
            </button>
            {painDemoResult && (
              <div className="pipeline-demo-result" aria-live="polite">
                <p role="status" dir="ltr">
                  {painDemoResult.status}
                </p>
                {painDemoResult.status === 'ESCALATE_FOR_REVIEW' && (
                  <p role="alert" className="stop-prompt">
                    <strong>
                      {tr(
                        `توقف عن التمرين الآن وتواصل مع أخصائيك. إذا كان عندك ألم في الصدر أو صعوبة في التنفس فاتصل بالإسعاف ${DEMO_DEFAULTS.emergencyNumber.value}.`,
                        `Stop exercising now and contact your physio. If you have chest pain or trouble breathing, call an ambulance on ${DEMO_DEFAULTS.emergencyNumber.value}.`,
                      )}
                    </strong>{' '}
                    {tr(
                      'التطبيق لا يتصل بأحد تلقائيًا.',
                      'The app never calls anyone by itself.',
                    )}
                  </p>
                )}
                <p>
                  {tr('رموز النتيجة', 'Result codes')}:{' '}
                  {painDemoResult.reasonCodes.length > 0
                    ? [
                        ...painDemoResult.reasonCodes,
                        ...painDemoResult.matchedRuleIds,
                      ].join(', ')
                    : tr(
                        'لا توجد عبارة خطر من القائمة',
                        'No warning phrase from the list',
                      )}
                </p>
                <p>
                  {tr(
                    'هذه نتيجة تجريبية من قائمة ونموذج لم يراجعهما أخصائي. عدم وجود إشارة لا يعني أنك بخير؛ إذا قلقت فتواصل مع أخصائيك.',
                    'This is a prototype result from a list and a model no physio has reviewed. No flag does not mean you are fine; if you are worried, contact your physio.',
                  )}
                </p>
              </div>
            )}
          </section>
        </div>

        <div hidden={tab !== 'about'}>
          <section className="session-summary" aria-labelledby="about-title">
            <h2 id="about-title">{tr('عن HomeRehab AI', 'About HomeRehab AI')}</h2>
            <p lang={lang}>
              {lang === 'ar' ? SAFETY_NOTICE.arabic : SAFETY_NOTICE.english}
            </p>
            <ul className="about-list">
              <li>
                {tr(
                  'يسجّل أخصائيك معك تكرارًا صحيحًا، ثم يقارن التطبيق كل تكرار في البيت به.',
                  'Your physio records one correct rep with you; the app compares every rep at home with it.',
                )}
              </li>
              <li>
                {tr(
                  'إذا لم يرك جيدًا، يصمت ويطلب تعديل الكاميرا بدل أن يخمّن.',
                  'If it cannot see you well, it stays silent and asks you to move the camera instead of guessing.',
                )}
              </li>
              <li>
                {tr(
                  'الفيديو يبقى على جهازك ولا يُرفع. يعمل بدون إنترنت بعد أول زيارة.',
                  'Video stays on your device and is never uploaded. It works offline after the first visit.',
                )}
              </li>
            </ul>
          </section>
        </div>

        <div hidden={tab !== 'lab'}>
          <p className="lab-intro">
            {tr(
              'تجارب تقنية للفريق والمشرفين: محاكاة وأدوات اختبار، وليست جزءًا من التمرين.',
              'Technical demos for the team and examiners: simulations and test tools, not part of the exercise.',
            )}
          </p>
          <LocalVideoPoseDemo />

          <section
            className="session-summary"
            aria-labelledby="session-summary-title"
            aria-describedby="simulation-label no-video-note"
          >
            <div className="summary-heading">
              <div>
                <p className="summary-kicker">
                  {tr('مثال توضيحي فقط', 'Illustration only')}
                </p>
                <h2 id="session-summary-title">
                  {tr('ملخص جلسة تجريبية', 'Sample session summary')}
                </h2>
              </div>
              <span className="simulation-badge" id="simulation-label">
                {tr('محاكاة · بيانات مصطنعة', 'Simulated · synthetic data')}
              </span>
            </div>

            <div
              className="scenario-picker"
              role="group"
              aria-label={tr('اختيار مثال المحاكاة', 'Choose a simulated example')}
            >
              <button
                type="button"
                aria-pressed={scenario === 'cannot-assess'}
                onClick={() => setScenario('cannot-assess')}
              >
                {tr('مثال: تعذّر التقييم', 'Example: cannot assess')}
              </button>
              <button
                type="button"
                aria-pressed={scenario === 'completed'}
                onClick={() => setScenario('completed')}
              >
                {tr('مثال: جلسة مكتملة', 'Example: completed session')}
              </button>
            </div>

            <div className="scenario-result" aria-live="polite">
              {scenario === 'cannot-assess' ? (
                <div className="cannot-assess-result" role="status">
                  <h3>{tr('تعذّر التقييم', 'Cannot assess')}</h3>
                  <p lang="ar">{SIMULATED_CANNOT_ASSESS.arabic}</p>
                  <p className="english-copy" lang="en" dir="ltr">
                    {SIMULATED_CANNOT_ASSESS.english}
                  </p>
                  <span className="reason-code" dir="ltr">
                    REQUIRED_LANDMARK_MISSING
                  </span>
                </div>
              ) : (
                <>
                  <div className="summary-metrics">
                    <div className="summary-metric">
                      <span className="metric-value" dir="ltr">
                        {SIMULATED_SESSION.repetitions}
                      </span>
                      <span>{tr('تكرارات تجريبية', 'Sample reps')}</span>
                    </div>
                    <div className="summary-metric">
                      <span className="metric-value" dir="ltr">
                        {SIMULATED_SESSION.duration}
                      </span>
                      <span>{tr('مدة افتراضية', 'Sample duration')}</span>
                    </div>
                  </div>
                  <p lang="ar">{SIMULATED_SESSION.movementSummary}</p>
                  <p className="english-copy" lang="en" dir="ltr">
                    {SIMULATED_SESSION.englishMovementSummary}
                  </p>
                </>
              )}
            </div>
            <p className="no-video-note" id="no-video-note">
              {tr(
                'لم يتم رفع أو تحليل أي فيديو. لا توجد نصيحة أو نتيجة سريرية في هذا المثال.',
                'No video was uploaded or analysed. There is no advice or clinical result in this example.',
              )}
            </p>
          </section>

          <section className="session-summary" aria-labelledby="pipeline-demo-title">
            <div className="summary-heading">
              <div>
                <p className="summary-kicker">
                  {tr('اختبار برمجي توضيحي', 'Illustrative software test')}
                </p>
                <h2 id="pipeline-demo-title">
                  {tr('تجربة خط التحليل المصطنع', 'Synthetic analysis pipeline')}
                </h2>
              </div>
              <span className="simulation-badge">
                {tr('لا يستخدم الكاميرا', 'Does not use the camera')}
              </span>
            </div>
            <p>
              {tr(
                'شغّل تسلسلًا هندسيًا مصطنعًا للتحقق من حساب الزاوية والعدّ ورفض إطار منخفض الوضوح. القيم للتجربة البرمجية فقط وليست أهدافًا علاجية.',
                'Run a synthetic geometric sequence to check the angle maths, the counting and the refusal of a low-visibility frame. The values are for software testing only, not treatment targets.',
              )}
            </p>
            <button
              className="demo-run-button"
              type="button"
              onClick={() => setPipelineResults(runSyntheticAnglePipelineDemo())}
            >
              {tr('شغّل المثال المصطنع', 'Run the synthetic example')}
            </button>
            {pipelineResults && (
              <div className="pipeline-demo-result" aria-live="polite">
                <p role="status">
                  {tr(
                    `اكتمل المثال: ${pipelineResults.at(-1)?.repetitionCount ?? 0} دورات مصطنعة؛ الإطار منخفض الوضوح لم يُحلّل ولم يزد العدّاد.`,
                    `Example done: ${pipelineResults.at(-1)?.repetitionCount ?? 0} synthetic cycles; the low-visibility frame was not analysed and did not add to the count.`,
                  )}
                </p>
                <div className="pipeline-frame-list">
                  {pipelineResults.map((result) => (
                    <div
                      className="pipeline-frame"
                      key={result.frame}
                      data-status={result.status}
                    >
                      <span>
                        {tr('إطار', 'Frame')} {result.frame}
                      </span>
                      <span dir="ltr">{result.status}</span>
                      <span dir="ltr">
                        {result.angleDegrees === null
                          ? '—'
                          : `${result.angleDegrees.toFixed(0)}°`}
                      </span>
                      <span>
                        {tr('العدّ', 'Count')}: {result.repetitionCount}
                      </span>
                      {result.reasonCodes.length > 0 && (
                        <code dir="ltr">{result.reasonCodes.join(', ')}</code>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>
        </div>

        <p className="prototype-label">
          {tr(
            'نموذج أولي تعليمي · غير مخصص للاستخدام السريري',
            'Educational prototype · not for clinical use',
          )}
        </p>
      </main>
    </div>
  );
}

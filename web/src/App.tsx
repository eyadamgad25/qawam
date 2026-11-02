import { useState } from 'react';
import {
  runSyntheticAnglePipelineDemo,
  type SyntheticFrameResult,
} from './anglePipelineDemo';
import { evaluatePainTriage, type PainTriageResult } from './painTriage';
import LocalVideoPoseDemo from './LocalVideoPoseDemo';
import ExerciseCoach from './exercise/ExerciseCoach';
import { DEMO_DEFAULTS, PAIN_RED_FLAGS, sourceOf } from './demoDefaults';
import LiteratureNote from './LiteratureNote';

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

export default function App() {
  const [scenario, setScenario] = useState<DemoScenario>('cannot-assess');
  const [pipelineResults, setPipelineResults] = useState<SyntheticFrameResult[] | null>(
    null,
  );
  const [painDemoText, setPainDemoText] = useState('');
  const [painModelFlag, setPainModelFlag] = useState(false);
  const [painDemoResult, setPainDemoResult] = useState<PainTriageResult | null>(null);

  return (
    <main className="page-shell">
      <header className="brand">
        <p className="brand-kicker">دعم التمارين المنزلية</p>
        <h1>قوام</h1>
        <p className="brand-english">Qawam</p>
      </header>

      <section className="safety-notice" role="alert" aria-labelledby="notice-title">
        <div className="notice-icon" aria-hidden="true">
          !
        </div>
        <div>
          <h2 id="notice-title">تنبيه مهم</h2>
          <p lang="ar">{SAFETY_NOTICE.arabic}</p>
          <p className="english-copy" lang="en" dir="ltr">
            {SAFETY_NOTICE.english}
          </p>
        </div>
      </section>

      <ExerciseCoach />

      <LocalVideoPoseDemo />

      <section
        className="session-summary"
        aria-labelledby="session-summary-title"
        aria-describedby="simulation-label no-video-note"
      >
        <div className="summary-heading">
          <div>
            <p className="summary-kicker">مثال توضيحي فقط</p>
            <h2 id="session-summary-title">ملخص جلسة تجريبية</h2>
          </div>
          <span className="simulation-badge" id="simulation-label">
            محاكاة · بيانات مصطنعة
          </span>
        </div>

        <div className="scenario-picker" role="group" aria-label="اختيار مثال المحاكاة">
          <button
            type="button"
            aria-pressed={scenario === 'cannot-assess'}
            onClick={() => setScenario('cannot-assess')}
          >
            مثال: تعذّر التقييم
          </button>
          <button
            type="button"
            aria-pressed={scenario === 'completed'}
            onClick={() => setScenario('completed')}
          >
            مثال: جلسة مكتملة
          </button>
        </div>

        <div className="scenario-result" aria-live="polite">
          {scenario === 'cannot-assess' ? (
            <div className="cannot-assess-result" role="status">
              <h3>تعذّر التقييم</h3>
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
                  <span>تكرارات تجريبية</span>
                </div>
                <div className="summary-metric">
                  <span className="metric-value" dir="ltr">
                    {SIMULATED_SESSION.duration}
                  </span>
                  <span>مدة افتراضية</span>
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
          لم يتم رفع أو تحليل أي فيديو. لا توجد نصيحة أو نتيجة سريرية في هذا المثال.
        </p>
      </section>

      <section className="session-summary" aria-labelledby="pipeline-demo-title">
        <div className="summary-heading">
          <div>
            <p className="summary-kicker">اختبار برمجي توضيحي</p>
            <h2 id="pipeline-demo-title">تجربة خط التحليل المصطنع</h2>
          </div>
          <span className="simulation-badge">لا يستخدم الكاميرا</span>
        </div>
        <p>
          شغّل تسلسلًا هندسيًا مصطنعًا للتحقق من حساب الزاوية والعدّ ورفض إطار منخفض
          الوضوح. القيم للتجربة البرمجية فقط وليست أهدافًا علاجية.
        </p>
        <button
          className="demo-run-button"
          type="button"
          onClick={() => setPipelineResults(runSyntheticAnglePipelineDemo())}
        >
          شغّل المثال المصطنع
        </button>
        {pipelineResults && (
          <div className="pipeline-demo-result" aria-live="polite">
            <p role="status">
              اكتمل المثال: {pipelineResults.at(-1)?.repetitionCount ?? 0} دورات مصطنعة؛
              الإطار منخفض الوضوح لم يُحلّل ولم يزد العدّاد.
            </p>
            <div className="pipeline-frame-list">
              {pipelineResults.map((result) => (
                <div
                  className="pipeline-frame"
                  key={result.frame}
                  data-status={result.status}
                >
                  <span>إطار {result.frame}</span>
                  <span dir="ltr">{result.status}</span>
                  <span dir="ltr">
                    {result.angleDegrees === null
                      ? '—'
                      : `${result.angleDegrees.toFixed(0)}°`}
                  </span>
                  <span>العدّ: {result.repetitionCount}</span>
                  {result.reasonCodes.length > 0 && (
                    <code dir="ltr">{result.reasonCodes.join(', ')}</code>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      <section className="session-summary" aria-labelledby="pain-demo-title">
        <div className="summary-heading">
          <div>
            <p className="summary-kicker">تجربة · قائمة من مصادر منشورة</p>
            <h2 id="pain-demo-title">فحص علامات الخطر في وصف الألم</h2>
          </div>
          <span className="simulation-badge">لم يراجعها أخصائي</span>
        </div>
        <p>
          اكتب بالعامية كيف تشعر. نبحث عن {PAIN_RED_FLAGS.length} عبارة خطر مأخوذة من
          إرشادات NHS بعد تغيير مفصل الركبة ومن قائمة المشروع. عدم وجود إشارة لا يعني
          أنك بخير. النص يبقى داخل الصفحة ولا يُحفظ أو يُرسل.{' '}
          <LiteratureNote source={sourceOf('nhsKnee')} />
        </p>
        <label className="pain-demo-label" htmlFor="pain-demo-text">
          صف ما تشعر به
        </label>
        <textarea
          id="pain-demo-text"
          value={painDemoText}
          onChange={(event) => setPainDemoText(event.target.value)}
          dir="rtl"
          rows={3}
          placeholder="مثال: عندي سخونية والجرح بينز"
        />
        <label className="pain-model-toggle">
          <input
            type="checkbox"
            checked={painModelFlag}
            onChange={(event) => setPainModelFlag(event.target.checked)}
          />
          <span>محاكاة إشارة نموذج إيجابية (للاختبار فقط)</span>
        </label>
        <button
          className="demo-run-button"
          type="button"
          onClick={() =>
            setPainDemoResult(
              evaluatePainTriage({
                text: painDemoText,
                lexicon: PAIN_RED_FLAGS,
                modelFlag: painModelFlag,
              }),
            )
          }
        >
          افحص العبارة
        </button>
        {painDemoResult && (
          <div className="pipeline-demo-result" aria-live="polite">
            <p role="status" dir="ltr">
              {painDemoResult.status}
            </p>
            {painDemoResult.status === 'ESCALATE_FOR_REVIEW' && (
              <p role="alert">
                <strong>
                  توقف عن التمرين الآن وتواصل مع أخصائيك. إذا كان عندك ألم في الصدر أو
                  صعوبة في التنفس فاتصل بالإسعاف {DEMO_DEFAULTS.emergencyNumber.value}.
                </strong>{' '}
                التطبيق لا يتصل بأحد تلقائيًا.
              </p>
            )}
            <p>
              رموز النتيجة:{' '}
              {painDemoResult.reasonCodes.length > 0
                ? [
                    ...painDemoResult.reasonCodes,
                    ...painDemoResult.matchedRuleIds,
                  ].join(', ')
                : 'لا توجد عبارة خطر من القائمة'}
            </p>
            <p>
              هذه نتيجة تجريبية من قائمة لم يراجعها أخصائي. عدم وجود إشارة لا يعني أنك
              بخير؛ إذا قلقت فتواصل مع أخصائيك.
            </p>
          </div>
        )}
      </section>

      <p className="prototype-label">نموذج أولي تعليمي · غير مخصص للاستخدام السريري</p>
    </main>
  );
}

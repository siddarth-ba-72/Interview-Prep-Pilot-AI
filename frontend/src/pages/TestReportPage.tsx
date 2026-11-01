import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Check, X } from 'lucide-react'
import { useAppSelector } from '../hooks'
import * as testAPI from '../api/tests'
import AppHeader from '../components/AppHeader'
import TopicHeader from '../components/TopicHeader'
import PageContainer, { WIDTH } from '../components/PageContainer'
import { buttonClass } from '../components/ui/Button'
import Notice from '../components/ui/Notice'
import ScoreBar from '../components/ui/ScoreBar'
import StatusPill from '../components/ui/StatusPill'
import type { RootState } from '../store'

/** "+5", "−1", "0": a sign on every change, with a real minus. */
function signed(points: number): string {
  if (points > 0) return `+${points}`
  if (points < 0) return `−${Math.abs(points)}`
  return '0'
}

export default function TestReportPage() {
  const { topicId = '', testId = '' } = useParams<{ topicId: string; testId: string }>()

  const [report, setReport] = useState<testAPI.TestReportResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [wrongOnly, setWrongOnly] = useState(false)

  // The report the test page just stored, or the server's copy after a reload
  const cachedReport = useAppSelector((state: RootState) => state.tests.reportsBySessionId[testId])

  useEffect(() => {
    if (!topicId || !testId) {
      setError('Topic ID or Test ID is missing')
      setLoading(false)
      return
    }
    let cancelled = false
    async function loadReport() {
      try {
        const data = cachedReport ?? (await testAPI.getTestReport(topicId, testId))
        if (!cancelled) setReport(data)
      } catch (err) {
        if (!cancelled) setError((err as Error).message || 'Failed to load report')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    loadReport()
    return () => {
      cancelled = true
    }
  }, [topicId, testId, cachedReport])

  return (
    <div className="min-h-screen">
      <AppHeader />
      <TopicHeader topicId={topicId} active="test" />

      <PageContainer mask maxWidth={WIDTH.topic} className="flex flex-col gap-10">
        {loading && <ReportSkeleton />}
        {!loading && (error || !report) && <Notice>{error ?? 'This report could not be found.'}</Notice>}
        {report && (
          <ReportBody topicId={topicId} report={report} wrongOnly={wrongOnly} onWrongOnly={setWrongOnly} />
        )}
      </PageContainer>
    </div>
  )
}

function ReportBody({
  topicId,
  report,
  wrongOnly,
  onWrongOnly,
}: {
  topicId: string
  report: testAPI.TestReportResponse
  wrongOnly: boolean
  onWrongOnly: (value: boolean) => void
}) {
  const results = report.questionSummary
  const mcq = results.filter((q) => q.section === 'MCQ')
  const written = results.filter((q) => q.section === 'SUBJECTIVE')
  const right = (rows: testAPI.QuestionResult[]) => rows.filter((q) => q.isCorrect).length
  const wrongCount = results.length - right(results)
  const percent = report.maxScore > 0 ? (report.rawScore / report.maxScore) * 100 : 0
  const date = report.createdAt
    ? new Date(report.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    : null

  const sections = [
    { key: 'MCQ', label: 'Multiple choice', rows: mcq, offset: 0, answerLabel: 'Correct answer' },
    { key: 'SUBJECTIVE', label: 'Written answers', rows: written, offset: mcq.length, answerLabel: 'Model answer' },
  ]

  return (
    <>
      <section aria-labelledby="summary-title">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 id="summary-title" className="type-section text-lg">
            Score summary
          </h2>
          <p className="type-meta">
            Attempt #{report.attemptNumber ?? 1}
            {date && ` · ${date}`}
          </p>
        </div>

        <div className="mt-3 grid gap-6 rounded-lg border border-line bg-sheet p-5 sm:grid-cols-[minmax(0,1fr)_240px] sm:p-6">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <p className="figures text-3xl font-semibold tracking-[-0.01em] text-ink">
                {report.rawScore}
                <span className="text-xl font-normal text-graphite"> / {report.maxScore}</span>
              </p>
              <StatusPill tone={report.passed ? 'positive' : 'negative'}>
                {report.passed ? 'Passed' : 'Below the pass mark'}
              </StatusPill>
            </div>
            <ScoreBar score={report.rawScore} max={report.maxScore} pass={report.passThreshold} size="md" className="mt-4 max-w-md" />
            <p className="type-meta figures mt-2.5">
              Pass mark {report.passThreshold} of {report.maxScore} · {percent.toFixed(1)}%
            </p>
          </div>

          <dl className="figures grid content-start gap-2.5 border-t border-rule pt-5 text-sm sm:border-l sm:border-t-0 sm:pl-6 sm:pt-0">
            <SummaryRow label="Multiple choice" value={`${right(mcq)} of ${mcq.length} right`} />
            <SummaryRow label="Written" value={`${right(written)} of ${written.length} right`} />
            <SummaryRow
              label="Topic average"
              value={report.avgScoreAtTime != null ? `${report.avgScoreAtTime.toFixed(1)} / ${report.maxScore}` : '—'}
            />
          </dl>
        </div>

        {report.basedOnPreviousAttempt && (
          <Notice tone="warning" className="mt-3">
            This test leaned on the weak areas from your previous attempt.
          </Notice>
        )}
      </section>

      <section className="grid gap-6 sm:grid-cols-2">
        <ThemeList title="Strengths" items={report.strengths} tone="positive" empty="None recorded on this attempt." />
        <ThemeList
          title="Areas for improvement"
          items={report.weaknesses}
          tone="negative"
          empty="Nothing flagged. Try a harder topic next."
        />
      </section>

      <section aria-labelledby="breakdown-title" className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="breakdown-title" className="type-section text-lg">
            Question breakdown
          </h2>
          <label className="flex cursor-pointer items-center gap-2 text-sm text-graphite">
            <input
              type="checkbox"
              checked={wrongOnly}
              onChange={(e) => onWrongOnly(e.target.checked)}
              className="h-4 w-4 accent-ink"
            />
            Show only wrong answers ({wrongCount})
          </label>
        </div>

        {sections.map(({ key, label, rows, offset, answerLabel }) => {
          const shown = rows
            .map((row, idx) => ({ row, number: idx + offset + 1 }))
            .filter(({ row }) => !wrongOnly || !row.isCorrect)
          if (rows.length === 0) return null
          return (
            <div key={key}>
              <h3 className="type-label mb-2">
                {label} · {right(rows)} of {rows.length} right
              </h3>
              {shown.length === 0 ? (
                <p className="rounded-lg border border-dashed border-edge px-5 py-4 text-sm text-graphite">
                  Every {label.toLowerCase()} question was right.
                </p>
              ) : (
                <ol className="divide-y divide-rule rounded-lg border border-line bg-sheet">
                  {shown.map(({ row, number }) => (
                    <GradedQuestion
                      key={row.questionId}
                      number={number}
                      result={row}
                      written={key === 'SUBJECTIVE'}
                      answerLabel={answerLabel}
                    />
                  ))}
                </ol>
              )}
            </div>
          )
        })}
      </section>

      <div className="flex flex-col-reverse gap-2 border-t border-line pt-6 sm:flex-row sm:justify-end">
        <Link to={`/topics/${topicId}/tests`} className={buttonClass({ size: 'lg' })}>
          All tests
        </Link>
        <Link to={`/topics/${topicId}/test`} className={buttonClass({ size: 'lg' })}>
          Take another test
        </Link>
        <Link to={`/topics/${topicId}/learn`} className={buttonClass({ variant: 'primary', size: 'lg' })}>
          Revisit in Learn Mode
        </Link>
      </div>
    </>
  )
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="text-graphite">{label}</dt>
      <dd className="text-right font-medium text-ink">{value}</dd>
    </div>
  )
}

function ThemeList({
  title,
  items,
  tone,
  empty,
}: {
  title: string
  items: string[]
  tone: 'positive' | 'negative'
  empty: string
}) {
  return (
    <div>
      <h3 className="type-section">{title}</h3>
      {items.length === 0 ? (
        <p className="type-body mt-2 text-graphite">{empty}</p>
      ) : (
        <ul className="mt-2 flex flex-col gap-1.5">
          {items.map((item, idx) => (
            <li key={idx} className="flex items-start gap-2.5 text-sm text-ink">
              <span
                aria-hidden
                className={`mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full ${tone === 'positive' ? 'bg-tick' : 'bg-redpen'}`}
              />
              {item}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

/** A marked question: the grader's tick or cross in the margin, the points in the right margin. */
function GradedQuestion({
  number,
  result,
  written,
  answerLabel,
}: {
  number: number
  result: testAPI.QuestionResult
  written: boolean
  answerLabel: string
}) {
  const Mark = result.isCorrect ? Check : X
  return (
    <li className="grid grid-cols-[2rem_minmax(0,1fr)_auto] gap-x-3 px-4 py-5 sm:grid-cols-[2.5rem_minmax(0,1fr)_auto] sm:px-5">
      <div className="flex flex-col items-start gap-1.5 pt-0.5">
        <span className="figures text-sm font-medium text-graphite">{number}</span>
        <Mark
          size={16}
          strokeWidth={2.5}
          aria-label={result.isCorrect ? 'Right' : 'Wrong'}
          className={result.isCorrect ? 'text-tick' : 'text-redpen'}
        />
      </div>

      <div className="min-w-0">
        <p className="type-question whitespace-pre-wrap text-base leading-[1.55] text-ink">{result.questionText}</p>

        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <div>
            <p className="type-label">Your answer</p>
            <Answer text={result.userAnswer} written={written} />
          </div>
          <div>
            <p className="type-label">{answerLabel}</p>
            <Answer text={result.correctAnswer} written={written} />
          </div>
        </div>

        {result.evaluation && <p className="type-body mt-3 text-graphite">{result.evaluation}</p>}
      </div>

      <p
        className={`figures pt-0.5 text-right text-sm font-semibold ${
          result.pointsAwarded > 0 ? 'text-tick' : result.pointsAwarded < 0 ? 'text-redpen' : 'text-graphite'
        }`}
      >
        {signed(result.pointsAwarded)}
      </p>
    </li>
  )
}

function Answer({ text, written }: { text: string | null; written: boolean }) {
  if (!text) return <p className="mt-1 text-sm text-pencil">Not answered</p>
  return written ? (
    <pre className="mt-1 whitespace-pre-wrap break-words rounded-md border border-line bg-wash p-3 font-mono text-[13px] leading-relaxed text-ink">
      {text}
    </pre>
  ) : (
    <p className="mt-1 text-sm text-ink">{text}</p>
  )
}

function ReportSkeleton() {
  return (
    <div aria-label="Loading report" className="flex flex-col gap-3">
      <div className="h-5 w-40 rounded bg-press" />
      <div className="h-36 rounded-lg border border-line bg-sheet" />
    </div>
  )
}

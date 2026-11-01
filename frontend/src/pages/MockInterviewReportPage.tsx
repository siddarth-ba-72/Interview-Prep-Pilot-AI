import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ChevronDown } from 'lucide-react'
import AppHeader from '../components/AppHeader'
import TopicHeader from '../components/TopicHeader'
import PageContainer, { WIDTH } from '../components/PageContainer'
import RatingBadge from '../components/RatingBadge'
import { buttonClass } from '../components/ui/Button'
import Notice from '../components/ui/Notice'
import ScoreBar from '../components/ui/ScoreBar'
import StatusPill from '../components/ui/StatusPill'
import * as interviewAPI from '../api/interviews'
import { configLabel } from '../features/interviews/labels'

const COMPLETION_REASON_LABELS: Record<string, string> = {
  USER_ENDED: 'Ended early',
  TIME_EXPIRED: 'Time ran out',
  COMPLETED_NATURALLY: 'Completed',
}

export default function MockInterviewReportPage() {
  const { topicId = '', sessionId = '' } = useParams<{ topicId: string; sessionId: string }>()
  const [report, setReport] = useState<interviewAPI.InterviewReportResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!topicId || !sessionId) return
    let cancelled = false
    const loadReport = async () => {
      setLoading(true)
      try {
        const response = await interviewAPI.getInterviewReport(topicId, sessionId)
        if (!cancelled) setReport(response)
      } catch (err) {
        if (!cancelled) setError(interviewAPI.interviewErrorMessage(err, 'Failed to load the interview report'))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void loadReport()
    return () => {
      cancelled = true
    }
  }, [sessionId, topicId])

  return (
    <div className="min-h-screen">
      <AppHeader />
      <TopicHeader topicId={topicId} active="interview" />
      <PageContainer mask maxWidth={WIDTH.topic} className="flex flex-col gap-10">
        {loading && (
          <div aria-label="Loading report" className="flex flex-col gap-3">
            <div className="h-5 w-48 rounded bg-press" />
            <div className="h-36 rounded-lg border border-line bg-sheet" />
          </div>
        )}
        {!loading && (error || !report) && (
          <Notice
            action={
              <Link to={`/topics/${topicId}/interviews`} className={buttonClass({ size: 'sm', variant: 'ghost' })}>
                Back to Mock interview
              </Link>
            }
          >
            {error ?? 'This report could not be found.'}
          </Notice>
        )}
        {report && <ReportBody topicId={topicId} report={report} />}
      </PageContainer>
    </div>
  )
}

function ReportBody({ topicId, report }: { topicId: string; report: interviewAPI.InterviewReportResponse }) {
  const [openExchange, setOpenExchange] = useState<number | null>(null)
  const reason = report.completionReason
    ? COMPLETION_REASON_LABELS[report.completionReason] ?? report.completionReason
    : null
  const date = report.createdAt
    ? new Date(report.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    : null
  const meta = [report.config ? configLabel(report.config) : null, reason, `${report.exchangeSummary.length} answered`, date]
    .filter(Boolean)
    .join(' · ')

  return (
    <>
      <section aria-labelledby="score-title">
        <h2 id="score-title" className="type-section text-lg">
          Interview score
        </h2>
        <div className="mt-3 rounded-lg border border-line bg-sheet p-5 sm:p-6">
          <div className="flex flex-wrap items-center gap-3">
            <p className="figures text-3xl font-semibold tracking-[-0.01em] text-ink">
              {report.score}
              <span className="text-xl font-normal text-graphite"> / {report.maxScore}</span>
            </p>
            <StatusPill tone={report.passed ? 'positive' : 'negative'}>
              {report.passed ? 'Passed' : 'Below the pass mark'}
            </StatusPill>
          </div>
          <ScoreBar score={report.score} max={report.maxScore} pass={report.passThreshold} size="md" className="mt-4 max-w-md" />
          <p className="figures type-meta mt-2.5">
            Pass mark {report.passThreshold} of {report.maxScore}. Each answer earns 100 if strong, 60 if satisfactory, 20 if weak.
          </p>
          <p className="type-meta mt-4 border-t border-rule pt-3">{meta}</p>
        </div>
      </section>

      <section aria-labelledby="assessment-title">
        <h2 id="assessment-title" className="type-section text-lg">
          Overall assessment
        </h2>
        <p className="mt-2 max-w-[68ch] text-[15px] leading-[1.65] text-ink">{report.overallSummary}</p>
      </section>

      <section className="grid gap-6 sm:grid-cols-2">
        <ThemeList title="Strengths" items={report.strengths} tone="positive" />
        <ThemeList title="Areas to improve" items={report.weaknesses} tone="negative" />
      </section>

      {report.improvementSuggestions.length > 0 && (
        <section aria-labelledby="better-title">
          <h2 id="better-title" className="type-section text-lg">
            How a stronger candidate would have answered
          </h2>
          <ol className="mt-3 divide-y divide-rule rounded-lg border border-line bg-sheet">
            {report.improvementSuggestions.map((suggestion, index) => (
              <li key={index} className="px-5 py-5">
                {suggestion.theme && <p className="type-label">{suggestion.theme}</p>}
                <p className="type-question mt-1 text-base leading-[1.55] text-ink">{suggestion.question}</p>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <div>
                    <p className="type-label">Your answer</p>
                    <p className="type-body mt-1 whitespace-pre-wrap text-graphite">
                      {suggestion.userAnswer || 'No answer given.'}
                    </p>
                  </div>
                  <div className="border-l-2 border-tick pl-4">
                    <p className="type-label">A strong answer</p>
                    <p className="type-body mt-1 whitespace-pre-wrap text-ink">{suggestion.betterAnswer}</p>
                  </div>
                </div>
              </li>
            ))}
          </ol>
        </section>
      )}

      {report.exchangeSummary.length > 0 && (
        <section aria-labelledby="questions-title">
          <h2 id="questions-title" className="type-section text-lg">
            Question breakdown
          </h2>
          <ol className="mt-3 divide-y divide-rule rounded-lg border border-line bg-sheet">
            {report.exchangeSummary.map((exchange, index) => {
              const isOpen = openExchange === index
              return (
                <li key={index}>
                  <button
                    type="button"
                    onClick={() => setOpenExchange(isOpen ? null : index)}
                    aria-expanded={isOpen}
                    className="grid w-full grid-cols-[2rem_minmax(0,1fr)_auto] items-start gap-x-3 px-4 py-4 text-left hover:bg-wash sm:grid-cols-[2.5rem_minmax(0,1fr)_auto] sm:px-5"
                  >
                    <span className="figures pt-0.5 text-sm font-medium text-graphite">{index + 1}</span>
                    <span className="min-w-0">
                      <span className="type-label block">
                        {exchange.theme}
                        {exchange.isFollowUp && ' · follow-up'}
                      </span>
                      <span className={`mt-0.5 block text-sm text-ink ${isOpen ? '' : 'truncate'}`}>{exchange.question}</span>
                    </span>
                    <span className="flex shrink-0 items-center gap-2 pt-0.5">
                      <RatingBadge rating={exchange.rating} />
                      <ChevronDown
                        size={15}
                        aria-hidden
                        className={`text-graphite transition-transform duration-150 ${isOpen ? 'rotate-180' : ''}`}
                      />
                    </span>
                  </button>
                  {isOpen && (
                    <div className="grid grid-cols-[2rem_minmax(0,1fr)] gap-x-3 px-4 pb-5 sm:grid-cols-[2.5rem_minmax(0,1fr)] sm:px-5">
                      <div />
                      <div className="flex flex-col gap-3">
                        <div>
                          <p className="type-label">Your answer</p>
                          <p className="type-body mt-1 whitespace-pre-wrap text-graphite">
                            {exchange.userAnswer || 'No answer given.'}
                          </p>
                        </div>
                        {exchange.feedback && (
                          <div>
                            <p className="type-label">Feedback</p>
                            <p className="type-body mt-1 text-ink">{exchange.feedback}</p>
                          </div>
                        )}
                        <p className="figures type-meta">Scored {exchange.points ?? 0} of 100 for this answer.</p>
                      </div>
                    </div>
                  )}
                </li>
              )
            })}
          </ol>
        </section>
      )}

      <div className="flex flex-col-reverse gap-2 border-t border-line pt-6 sm:flex-row sm:justify-end">
        <Link to={`/topics/${topicId}/interviews/history`} className={buttonClass({ size: 'lg' })}>
          All interviews
        </Link>
        <Link to={`/topics/${topicId}/interviews`} className={buttonClass({ size: 'lg' })}>
          Run another interview
        </Link>
        <Link to={`/topics/${topicId}/learn`} className={buttonClass({ variant: 'primary', size: 'lg' })}>
          Revisit in Learn Mode
        </Link>
      </div>
    </>
  )
}

function ThemeList({ title, items, tone }: { title: string; items: string[]; tone: 'positive' | 'negative' }) {
  return (
    <div>
      <h3 className="type-section">{title}</h3>
      {items.length === 0 ? (
        <p className="type-body mt-2 text-graphite">Nothing recorded here.</p>
      ) : (
        <ul className="mt-2 flex flex-col gap-1.5">
          {items.map((item) => (
            <li key={item} className="flex items-start gap-2.5 text-sm text-ink">
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

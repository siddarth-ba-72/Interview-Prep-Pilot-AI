import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  History,
  Loader2,
  Lightbulb,
  RotateCcw,
  TrendingUp,
} from 'lucide-react'
import AppHeader from '../components/AppHeader'
import PageContainer from '../components/PageContainer'
import RatingBadge from '../components/RatingBadge'
import * as interviewAPI from '../api/interviews'

const COMPLETION_REASON_LABELS: Record<string, string> = {
  USER_ENDED: 'Ended early by you',
  TIME_EXPIRED: 'Time ran out',
  COMPLETED_NATURALLY: 'Completed',
}

function ScoreRing({ score, maxScore, passed }: { score: number; maxScore: number; passed: boolean }) {
  const fraction = maxScore > 0 ? Math.min(1, Math.max(0, score / maxScore)) : 0
  const circumference = 2 * Math.PI * 42
  const strokeColor = passed ? 'var(--success)' : 'var(--warning)'

  return (
    <div className="relative h-28 w-28 shrink-0">
      <svg className="h-full w-full -rotate-90" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="42" fill="none" stroke="var(--border)" strokeWidth="8" />
        <circle
          cx="50"
          cy="50"
          r="42"
          fill="none"
          stroke={strokeColor}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - fraction)}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-extrabold tabular-nums text-fg">{score}</span>
        <span className="text-[11px] font-semibold text-muted">/ {maxScore}</span>
      </div>
    </div>
  )
}

function ThemeChips({ items, tone }: { items: string[]; tone: 'success' | 'danger' }) {
  if (items.length === 0) {
    return <p className="text-sm text-muted">Nothing recorded here.</p>
  }
  const className =
    tone === 'success'
      ? 'border-success/30 bg-success-subtle text-success-fg'
      : 'border-danger/30 bg-danger-subtle text-danger-fg'
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <span key={item} className={`rounded-full border px-3 py-1 text-sm font-semibold ${className}`}>
          {item}
        </span>
      ))}
    </div>
  )
}

export default function MockInterviewReportPage() {
  const navigate = useNavigate()
  const { topicId = '', sessionId = '' } = useParams<{ topicId: string; sessionId: string }>()
  const [report, setReport] = useState<interviewAPI.InterviewReportResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [openExchange, setOpenExchange] = useState<number | null>(null)

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

  if (loading) {
    return (
      <div className="min-h-screen bg-bg text-fg">
        <AppHeader onBack={() => navigate('/dashboard')} title="Mock Interview Report" />
        <PageContainer maxWidth="max-w-3xl">
          <div className="flex items-center justify-center gap-3 rounded-2xl border border-border bg-surface p-12">
            <Loader2 size={20} className="animate-spin text-primary" />
            <p className="text-sm font-semibold text-fg">Loading your report…</p>
          </div>
        </PageContainer>
      </div>
    )
  }

  if (error || !report) {
    return (
      <div className="min-h-screen bg-bg text-fg">
        <AppHeader onBack={() => navigate('/dashboard')} title="Mock Interview Report" />
        <PageContainer maxWidth="max-w-3xl">
          <div className="flex flex-col items-start gap-4 rounded-2xl border border-danger/30 bg-danger-subtle p-6">
            <div className="flex items-center gap-2 text-danger-fg">
              <AlertTriangle size={18} />
              <p className="text-sm font-bold">{error ?? 'This report could not be found.'}</p>
            </div>
            <button
              onClick={() => navigate(`/topics/${topicId}/interviews`)}
              className="rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-primary-fg transition-colors hover:bg-primary-hover"
            >
              Back to Mock Interview
            </button>
          </div>
        </PageContainer>
      </div>
    )
  }

  const completionLabel = report.completionReason
    ? COMPLETION_REASON_LABELS[report.completionReason] ?? report.completionReason
    : null

  return (
    <div className="min-h-screen bg-bg text-fg">
      <AppHeader
        onBack={() => navigate('/dashboard')}
        title="Mock Interview Report"
        actions={
          <button
            onClick={() => navigate(`/topics/${topicId}/interviews/history`)}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border px-3 text-sm font-semibold text-muted transition-colors hover:bg-surface-hover hover:text-fg"
          >
            <History size={15} />
            <span className="hidden sm:inline">Past interviews</span>
          </button>
        }
      />
      <PageContainer maxWidth="max-w-3xl">
        <div className="flex flex-col gap-4">
          {/* Score summary */}
          <div className="flex flex-col items-center gap-5 rounded-2xl border border-border bg-surface p-6 shadow-sm sm:flex-row sm:items-center">
            <ScoreRing score={report.score} maxScore={report.maxScore} passed={report.passed} />
            <div className="min-w-0 flex-1 text-center sm:text-left">
              <div
                className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm font-bold ${
                  report.passed
                    ? 'border-success/30 bg-success-subtle text-success-fg'
                    : 'border-warning/30 bg-warning-subtle text-warning-fg'
                }`}
              >
                {report.passed ? <CheckCircle2 size={14} /> : <TrendingUp size={14} />}
                {report.passed ? 'Passed' : 'Needs work'}
              </div>
              <p className="mt-2 text-sm text-muted">
                Pass threshold is {report.passThreshold} out of {report.maxScore}.
              </p>
              <div className="mt-3 flex flex-wrap justify-center gap-2 sm:justify-start">
                {report.config && (
                  <>
                    <span className="rounded-full bg-surface-hover px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide text-muted">
                      {report.config.experienceLevel}
                    </span>
                    <span className="rounded-full bg-surface-hover px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide text-muted">
                      {report.config.difficulty}
                    </span>
                    <span className="rounded-full bg-surface-hover px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide text-muted">
                      {report.config.durationMinutes} min
                    </span>
                  </>
                )}
                {completionLabel && (
                  <span className="rounded-full bg-surface-hover px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide text-muted">
                    {completionLabel}
                  </span>
                )}
                <span className="rounded-full bg-surface-hover px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide text-muted">
                  {report.exchangeSummary.length} answered
                </span>
              </div>
            </div>
          </div>

          {/* Overall summary */}
          <div className="rounded-2xl border border-border bg-surface p-5">
            <h2 className="text-sm font-bold text-fg">Overall assessment</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted">{report.overallSummary}</p>
          </div>

          {/* Strengths / weaknesses */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl border border-border bg-surface p-5">
              <h2 className="mb-3 inline-flex items-center gap-2 text-sm font-bold text-fg">
                <CheckCircle2 size={15} className="text-success" />
                Strengths
              </h2>
              <ThemeChips items={report.strengths} tone="success" />
            </div>
            <div className="rounded-2xl border border-border bg-surface p-5">
              <h2 className="mb-3 inline-flex items-center gap-2 text-sm font-bold text-fg">
                <AlertTriangle size={15} className="text-danger" />
                Areas to improve
              </h2>
              <ThemeChips items={report.weaknesses} tone="danger" />
            </div>
          </div>

          {/* Improvement suggestions */}
          {report.improvementSuggestions.length > 0 && (
            <div className="rounded-2xl border border-border bg-surface p-5">
              <h2 className="inline-flex items-center gap-2 text-sm font-bold text-fg">
                <Lightbulb size={15} className="text-warning" />
                How a stronger candidate would have answered
              </h2>
              <div className="mt-4 flex flex-col gap-4">
                {report.improvementSuggestions.map((suggestion, index) => (
                  <div key={index} className="rounded-xl border border-border p-4">
                    {suggestion.theme && (
                      <p className="text-[11px] font-bold uppercase tracking-wide text-muted">{suggestion.theme}</p>
                    )}
                    <p className="mt-1 text-sm font-semibold text-fg">{suggestion.question}</p>
                    <div className="mt-3 rounded-lg bg-surface-hover p-3">
                      <p className="text-[11px] font-bold uppercase tracking-wide text-muted">Your answer</p>
                      <p className="mt-1 whitespace-pre-wrap text-sm text-muted">
                        {suggestion.userAnswer || '(no answer given)'}
                      </p>
                    </div>
                    <div className="mt-2 rounded-lg border border-success/30 bg-success-subtle p-3">
                      <p className="text-[11px] font-bold uppercase tracking-wide text-success-fg">A strong answer</p>
                      <p className="mt-1 whitespace-pre-wrap text-sm leading-relaxed text-success-fg">
                        {suggestion.betterAnswer}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Per-question breakdown */}
          {report.exchangeSummary.length > 0 && (
            <div className="rounded-2xl border border-border bg-surface p-5">
              <h2 className="text-sm font-bold text-fg">Question breakdown</h2>
              <div className="mt-3 flex flex-col gap-2">
                {report.exchangeSummary.map((exchange, index) => {
                  const isOpen = openExchange === index
                  return (
                    <div key={index} className="rounded-xl border border-border">
                      <button
                        onClick={() => setOpenExchange(isOpen ? null : index)}
                        className="flex w-full items-start justify-between gap-3 p-3 text-left"
                      >
                        <span className="min-w-0">
                          <span className="block text-[11px] font-bold uppercase tracking-wide text-muted">
                            {index + 1}. {exchange.theme}
                            {exchange.isFollowUp && ' · follow-up'}
                          </span>
                          <span className="mt-0.5 block truncate text-sm font-semibold text-fg">
                            {exchange.question}
                          </span>
                        </span>
                        <span className="flex shrink-0 items-center gap-2">
                          <RatingBadge rating={exchange.rating} size="sm" />
                          <ChevronDown
                            size={15}
                            className={`text-muted transition-transform ${isOpen ? 'rotate-180' : ''}`}
                          />
                        </span>
                      </button>
                      {isOpen && (
                        <div className="flex flex-col gap-3 border-t border-border p-3 text-sm">
                          <div>
                            <p className="text-[11px] font-bold uppercase tracking-wide text-muted">Question</p>
                            <p className="mt-1 text-fg">{exchange.question}</p>
                          </div>
                          <div>
                            <p className="text-[11px] font-bold uppercase tracking-wide text-muted">Your answer</p>
                            <p className="mt-1 whitespace-pre-wrap text-muted">
                              {exchange.userAnswer || '(no answer given)'}
                            </p>
                          </div>
                          {exchange.feedback && (
                            <div>
                              <p className="text-[11px] font-bold uppercase tracking-wide text-muted">Feedback</p>
                              <p className="mt-1 text-muted">{exchange.feedback}</p>
                            </div>
                          )}
                          <p className="text-xs font-semibold text-muted">
                            Scored {exchange.points ?? 0} of 100 for this answer.
                          </p>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          <div className="flex flex-col gap-3 sm:flex-row">
            <button
              onClick={() => navigate(`/topics/${topicId}/learn`)}
              className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-primary px-4 py-3 text-sm font-bold text-primary-fg transition-colors hover:bg-primary-hover"
            >
              <BookOpen size={16} />
              Revisit topic in Learn Mode
            </button>
            <button
              onClick={() => navigate(`/topics/${topicId}/interviews`)}
              className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl border border-border px-4 py-3 text-sm font-bold text-fg transition-colors hover:bg-surface-hover"
            >
              <RotateCcw size={16} />
              Run another interview
            </button>
          </div>
        </div>
      </PageContainer>
    </div>
  )
}

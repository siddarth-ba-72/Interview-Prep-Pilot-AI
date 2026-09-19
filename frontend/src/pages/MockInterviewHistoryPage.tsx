import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Loader2, Plus } from 'lucide-react'
import * as interviewAPI from '../api/interviews'
import * as topicAPI from '../api/topics'
import AppHeader from '../components/AppHeader'
import PageContainer from '../components/PageContainer'

const COMPLETION_REASON_LABELS: Record<string, string> = {
  USER_ENDED: 'Ended early',
  TIME_EXPIRED: 'Time ran out',
  COMPLETED_NATURALLY: 'Completed',
}

type Outcome = { label: string; className: string }

/** A completed interview whose report has never been opened has no score yet - reports are
 * generated lazily, so the row says so rather than implying a zero. */
function outcomeFor(summary: interviewAPI.InterviewSummary): Outcome {
  if (summary.status === 'IN_PROGRESS') {
    return { label: 'In progress', className: 'border-primary/30 bg-primary-subtle text-primary' }
  }
  if (summary.passed === null) {
    return { label: 'Not scored yet', className: 'border-border bg-surface-hover text-muted' }
  }
  return summary.passed
    ? { label: 'Passed', className: 'border-success/30 bg-success-subtle text-success-fg' }
    : { label: 'Needs work', className: 'border-warning/30 bg-warning-subtle text-warning-fg' }
}

function formatScore(summary: interviewAPI.InterviewSummary): string {
  if (summary.score === null) return '—'
  return `${summary.score}/${summary.maxScore ?? 100}`
}

function formatSetup(config: interviewAPI.InterviewConfig | null): string {
  if (!config) return 'Setup unavailable'
  return `${config.experienceLevel} · ${config.difficulty} · ${config.durationMinutes} min`
}

function OutcomeBadge({ outcome }: { outcome: Outcome }) {
  return (
    <span className={`inline-block whitespace-nowrap rounded-full border px-2.5 py-1 text-xs font-bold ${outcome.className}`}>
      {outcome.label}
    </span>
  )
}

export default function MockInterviewHistoryPage() {
  const navigate = useNavigate()
  const { topicId = '' } = useParams<{ topicId: string }>()

  const [topicName, setTopicName] = useState('')
  const [sessions, setSessions] = useState<interviewAPI.InterviewSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!topicId) return
    let cancelled = false
    Promise.all([topicAPI.listTopics(), interviewAPI.listInterviews(topicId)])
      .then(([topics, summaries]) => {
        if (cancelled) return
        setTopicName(topics.find((topic) => topic.id === topicId)?.name ?? 'Topic')
        setSessions(summaries) // already newest-first from the server
      })
      .catch((err) => {
        if (!cancelled) setError(interviewAPI.interviewErrorMessage(err, 'Failed to load your interview history.'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [topicId])

  // Rows are newest-first, so attempt #1 is the last one in the list.
  const attemptNumber = (index: number) => sessions.length - index

  const openSession = (summary: interviewAPI.InterviewSummary) => {
    if (summary.status === 'IN_PROGRESS') {
      navigate(`/topics/${topicId}/interviews`)
    } else {
      navigate(`/topics/${topicId}/interviews/${summary.sessionId}/report`)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-bg text-fg">
        <AppHeader onBack={() => navigate('/dashboard')} title="Mock Interviews" subtitle="History" />
        <PageContainer maxWidth="max-w-4xl">
          <div className="flex items-center justify-center gap-3 rounded-2xl border border-border bg-surface p-12">
            <Loader2 size={20} className="animate-spin text-primary" />
            <p className="text-sm font-semibold text-fg">Loading your interview history…</p>
          </div>
        </PageContainer>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-bg text-fg">
        <AppHeader onBack={() => navigate('/dashboard')} title="Mock Interviews" subtitle="History" />
        <PageContainer maxWidth="max-w-4xl" className="flex flex-col items-start gap-4">
          <p className="text-sm font-medium text-danger">{error}</p>
          <button
            onClick={() => navigate('/dashboard')}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-bold text-primary-fg hover:bg-primary-hover"
          >
            Back to Dashboard
          </button>
        </PageContainer>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-bg text-fg">
      <AppHeader
        onBack={() => navigate('/dashboard')}
        title={topicName}
        subtitle="Interview History"
        actions={
          <button
            onClick={() => navigate(`/topics/${topicId}/interviews`)}
            className="flex h-9 items-center gap-1.5 rounded-lg bg-primary px-3 text-sm font-bold text-primary-fg transition-colors hover:bg-primary-hover"
          >
            <Plus size={15} />
            <span className="hidden sm:inline">New Interview</span>
          </button>
        }
      />

      <PageContainer maxWidth="max-w-4xl">
        {sessions.length === 0 ? (
          <div className="flex flex-col items-center gap-4 rounded-2xl border border-dashed border-border bg-surface/50 px-6 py-14 text-center">
            <p className="text-sm font-medium text-muted">No mock interviews yet for this topic.</p>
            <button
              onClick={() => navigate(`/topics/${topicId}/interviews`)}
              className="rounded-lg bg-primary px-5 py-2.5 text-sm font-bold text-primary-fg transition-colors hover:bg-primary-hover"
            >
              Run Your First Interview
            </button>
          </div>
        ) : (
          <>
            {/* Desktop table */}
            <div className="hidden overflow-hidden rounded-2xl border border-border sm:block">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="bg-surface-hover text-xs font-semibold uppercase tracking-wide text-muted">
                    <th className="w-14 px-4 py-3">#</th>
                    <th className="px-4 py-3">Date &amp; Time</th>
                    <th className="px-4 py-3">Setup</th>
                    <th className="px-4 py-3">Score</th>
                    <th className="px-4 py-3">Result</th>
                    <th className="px-4 py-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {sessions.map((summary, index) => {
                    const date = new Date(summary.completedAt ?? summary.createdAt)
                    const outcome = outcomeFor(summary)
                    const reasonLabel = summary.completionReason
                      ? COMPLETION_REASON_LABELS[summary.completionReason] ?? summary.completionReason
                      : null
                    return (
                      <tr
                        key={summary.sessionId}
                        className="border-t border-border bg-surface transition-colors hover:bg-surface-hover"
                      >
                        <td className="px-4 py-3.5 font-semibold text-muted">{attemptNumber(index)}</td>
                        <td className="px-4 py-3.5">
                          <div className="font-medium text-fg">
                            {date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                          </div>
                          <div className="text-xs text-muted">
                            {date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                          </div>
                        </td>
                        <td className="px-4 py-3.5">
                          <div className="text-xs font-semibold text-fg">{formatSetup(summary.config)}</div>
                          <div className="text-xs text-muted">
                            {summary.answeredCount} answered
                            {reasonLabel && ` · ${reasonLabel}`}
                          </div>
                        </td>
                        <td className="px-4 py-3.5 whitespace-nowrap">
                          {summary.score === null ? (
                            <span className="text-muted">—</span>
                          ) : (
                            <span className="font-bold text-fg">{formatScore(summary)}</span>
                          )}
                        </td>
                        <td className="px-4 py-3.5">
                          <OutcomeBadge outcome={outcome} />
                        </td>
                        <td className="px-4 py-3.5 text-right">
                          <button
                            onClick={() => openSession(summary)}
                            className="whitespace-nowrap rounded-lg border border-border px-3 py-1.5 text-xs font-bold text-fg transition-colors hover:bg-surface-hover"
                          >
                            {summary.status === 'IN_PROGRESS' ? 'Resume' : 'View Report'}
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            {/* Mobile card list */}
            <div className="flex flex-col gap-3 sm:hidden">
              {sessions.map((summary, index) => {
                const date = new Date(summary.completedAt ?? summary.createdAt)
                const outcome = outcomeFor(summary)
                const reasonLabel = summary.completionReason
                  ? COMPLETION_REASON_LABELS[summary.completionReason] ?? summary.completionReason
                  : null
                return (
                  <button
                    key={summary.sessionId}
                    onClick={() => openSession(summary)}
                    className="flex flex-col gap-2 rounded-2xl border border-border bg-surface p-4 text-left transition-colors hover:bg-surface-hover"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-semibold text-muted">Interview #{attemptNumber(index)}</span>
                      <OutcomeBadge outcome={outcome} />
                    </div>
                    <div className="flex items-end justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-sm font-bold text-fg">
                          {date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                          <span className="ml-2 font-normal text-muted">
                            {date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </p>
                        <p className="mt-0.5 truncate text-xs text-muted">{formatSetup(summary.config)}</p>
                        <p className="text-xs text-muted">
                          {summary.answeredCount} answered
                          {reasonLabel && ` · ${reasonLabel}`}
                        </p>
                      </div>
                      <p className="shrink-0 text-sm font-bold text-fg">{formatScore(summary)}</p>
                    </div>
                  </button>
                )
              })}
            </div>
          </>
        )}
      </PageContainer>
    </div>
  )
}

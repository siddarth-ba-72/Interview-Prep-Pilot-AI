import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import * as interviewAPI from '../api/interviews'
import AppHeader from '../components/AppHeader'
import TopicHeader from '../components/TopicHeader'
import HistorySwitch from '../components/HistorySwitch'
import PageContainer, { WIDTH } from '../components/PageContainer'
import { Button, buttonClass } from '../components/ui/Button'
import EmptyState from '../components/ui/EmptyState'
import Notice from '../components/ui/Notice'
import ScoreBar from '../components/ui/ScoreBar'
import StatusPill, { type PillTone } from '../components/ui/StatusPill'
import { INTERVIEW_MAX, INTERVIEW_PASS, configLabel } from '../features/interviews/labels'

const COMPLETION_REASON_LABELS: Record<string, string> = {
  USER_ENDED: 'ended early',
  TIME_EXPIRED: 'time ran out',
  COMPLETED_NATURALLY: 'completed',
}

/** A completed interview whose report has never been opened has no score yet: reports are
 * generated lazily, so the row says so rather than implying a zero. */
function outcomeFor(summary: interviewAPI.InterviewSummary): { label: string; tone: PillTone } {
  if (summary.status === 'IN_PROGRESS') return { label: 'In progress', tone: 'accent' }
  if (summary.passed === null) return { label: 'Not scored yet', tone: 'neutral' }
  return summary.passed ? { label: 'Passed', tone: 'positive' } : { label: 'Below', tone: 'negative' }
}

function formatDate(date: Date) {
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}
function formatTime(date: Date) {
  return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
}

export default function MockInterviewHistoryPage() {
  const navigate = useNavigate()
  const { topicId = '' } = useParams<{ topicId: string }>()

  const [sessions, setSessions] = useState<interviewAPI.InterviewSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!topicId) return
    let cancelled = false
    interviewAPI
      .listInterviews(topicId)
      .then((summaries) => !cancelled && setSessions(summaries)) // newest first from the server
      .catch((err) => !cancelled && setError(interviewAPI.interviewErrorMessage(err, 'Could not load your interview history.')))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [topicId])

  const attemptNumber = (index: number) => sessions.length - index
  const openSession = (summary: interviewAPI.InterviewSummary) =>
    navigate(
      summary.status === 'IN_PROGRESS'
        ? `/topics/${topicId}/interviews`
        : `/topics/${topicId}/interviews/${summary.sessionId}/report`
    )

  return (
    <div className="min-h-screen">
      <AppHeader />
      <TopicHeader topicId={topicId} active="history" />

      <PageContainer mask maxWidth={WIDTH.topic} className="flex flex-col gap-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <HistorySwitch topicId={topicId} current="interviews" />
          {sessions.length > 0 && (
            <Link to={`/topics/${topicId}/interviews`} className={buttonClass({ variant: 'primary' })}>
              New interview
            </Link>
          )}
        </div>

        {loading && <div aria-label="Loading interviews" className="h-40 rounded-lg border border-line bg-sheet" />}
        {error && <Notice>{error}</Notice>}

        {!loading && !error && sessions.length === 0 && (
          <EmptyState
            action={
              <Button variant="primary" onClick={() => navigate(`/topics/${topicId}/interviews`)}>
                Set up an interview
              </Button>
            }
          >
            No mock interviews on this topic yet. Each one is timed and rated answer by answer.
          </EmptyState>
        )}

        {sessions.length > 0 && (
          <>
            <p className="type-body text-graphite">{summarise(sessions)}</p>

            <div className="hidden overflow-hidden rounded-lg border border-line bg-sheet sm:block">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="text-xs text-graphite">
                    <th className="w-16 px-5 py-3 font-normal">No.</th>
                    <th className="px-5 py-3 font-normal">Taken</th>
                    <th className="px-5 py-3 font-normal">Setup</th>
                    <th className="w-48 px-5 py-3 text-right font-normal">Score</th>
                    <th className="px-5 py-3 font-normal">Result</th>
                    <th className="px-5 py-3">
                      <span className="sr-only">Open</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {sessions.map((summary, index) => {
                    const date = new Date(summary.completedAt ?? summary.createdAt)
                    const outcome = outcomeFor(summary)
                    const reason = summary.completionReason
                      ? COMPLETION_REASON_LABELS[summary.completionReason] ?? summary.completionReason
                      : null
                    return (
                      <tr key={summary.sessionId} className="border-t border-rule">
                        <td className="figures px-5 py-3.5 text-graphite">#{attemptNumber(index)}</td>
                        <td className="px-5 py-3.5">
                          <div className="text-ink">{formatDate(date)}</div>
                          <div className="type-meta">{formatTime(date)}</div>
                        </td>
                        <td className="px-5 py-3.5">
                          <div className="text-ink">{configLabel(summary.config)}</div>
                          <div className="type-meta">
                            {summary.answeredCount} answered{reason && `, ${reason}`}
                          </div>
                        </td>
                        <td className="px-5 py-3.5">
                          {summary.score === null ? (
                            <div className="text-right text-pencil">—</div>
                          ) : (
                            <>
                              <div className="figures text-right">
                                <span className="font-semibold text-ink">{summary.score}</span>
                                <span className="text-graphite"> / {summary.maxScore ?? INTERVIEW_MAX}</span>
                              </div>
                              <ScoreBar
                                score={summary.score}
                                max={summary.maxScore ?? INTERVIEW_MAX}
                                pass={INTERVIEW_PASS}
                                className="ml-auto mt-1.5 w-32"
                              />
                            </>
                          )}
                        </td>
                        <td className="px-5 py-3.5">
                          <StatusPill tone={outcome.tone}>{outcome.label}</StatusPill>
                        </td>
                        <td className="px-5 py-3.5 text-right">
                          <Button size="sm" variant={summary.status === 'IN_PROGRESS' ? 'primary' : 'secondary'} onClick={() => openSession(summary)}>
                            {summary.status === 'IN_PROGRESS' ? 'Resume' : 'View report'}
                          </Button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            <ul className="divide-y divide-rule rounded-lg border border-line bg-sheet sm:hidden">
              {sessions.map((summary) => {
                const date = new Date(summary.completedAt ?? summary.createdAt)
                const outcome = outcomeFor(summary)
                return (
                  <li key={summary.sessionId}>
                    <button
                      type="button"
                      onClick={() => openSession(summary)}
                      className="flex w-full items-center justify-between gap-4 px-4 py-3.5 text-left hover:bg-wash"
                    >
                      <span className="min-w-0">
                        <span className="block truncate text-sm text-ink">{configLabel(summary.config)}</span>
                        <span className="type-meta block">
                          {formatDate(date)} · {summary.answeredCount} answered
                        </span>
                      </span>
                      <span className="flex shrink-0 flex-col items-end gap-1">
                        <span className="figures text-sm">
                          {summary.score === null ? (
                            <span className="text-pencil">—</span>
                          ) : (
                            <>
                              <span className="font-semibold text-ink">{summary.score}</span>
                              <span className="text-graphite"> / {summary.maxScore ?? INTERVIEW_MAX}</span>
                            </>
                          )}
                        </span>
                        <StatusPill tone={outcome.tone}>{outcome.label}</StatusPill>
                      </span>
                    </button>
                  </li>
                )
              })}
            </ul>
          </>
        )}
      </PageContainer>
    </div>
  )
}

function summarise(sessions: interviewAPI.InterviewSummary[]): string {
  const scored = sessions.filter((s) => s.score !== null)
  const count = `${sessions.length} ${sessions.length === 1 ? 'interview' : 'interviews'}`
  const running = sessions.some((s) => s.status === 'IN_PROGRESS') ? ' One is still running; its clock has not stopped.' : ''
  if (scored.length === 0) return `${count}, none scored yet.${running}`
  const best = Math.max(...scored.map((s) => s.score!))
  return `${count}. Best score ${best} of ${INTERVIEW_MAX}, against a pass mark of ${INTERVIEW_PASS}.${running}`
}

import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import * as testAPI from '../api/tests'
import AppHeader from '../components/AppHeader'
import TopicHeader from '../components/TopicHeader'
import HistorySwitch from '../components/HistorySwitch'
import PageContainer, { WIDTH } from '../components/PageContainer'
import { TEST_MAX, TEST_PASS } from '../components/TopicRow'
import { Button, buttonClass } from '../components/ui/Button'
import EmptyState from '../components/ui/EmptyState'
import Notice from '../components/ui/Notice'
import ScoreBar from '../components/ui/ScoreBar'
import StatusPill from '../components/ui/StatusPill'

function formatDate(date: Date) {
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}
function formatTime(date: Date) {
  return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
}

export default function TestHistoryPage() {
  const navigate = useNavigate()
  const { topicId = '' } = useParams<{ topicId: string }>()

  const [sessions, setSessions] = useState<testAPI.TestSessionListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!topicId) return
    testAPI
      .listTestSessions(topicId)
      .then((items) =>
        setSessions([...items].sort((a, b) => new Date(b.completedAt).getTime() - new Date(a.completedAt).getTime()))
      )
      .catch(() => setError('Could not load your test history.'))
      .finally(() => setLoading(false))
  }, [topicId])

  const openReport = (sessionId: string) => navigate(`/topics/${topicId}/tests/${sessionId}/report`)

  return (
    <div className="min-h-screen">
      <AppHeader />
      <TopicHeader topicId={topicId} active="history" />

      <PageContainer mask maxWidth={WIDTH.topic} className="flex flex-col gap-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <HistorySwitch topicId={topicId} current="tests" />
          {sessions.length > 0 && (
            <Link to={`/topics/${topicId}/test`} className={buttonClass({ variant: 'primary' })}>
              New test
            </Link>
          )}
        </div>

        {loading && <div aria-label="Loading tests" className="h-40 rounded-lg border border-line bg-sheet" />}
        {error && <Notice>{error}</Notice>}

        {!loading && !error && sessions.length === 0 && (
          <EmptyState
            action={
              <Button variant="primary" onClick={() => navigate(`/topics/${topicId}/test`)}>
                Take a test
              </Button>
            }
          >
            No tests on this topic yet. A test is 20 questions, graded against a pass mark of {TEST_PASS}.
          </EmptyState>
        )}

        {sessions.length > 0 && (
          <>
            <p className="type-body text-graphite">{summarise(sessions)}</p>

            {/* Table from the small breakpoint up */}
            <div className="hidden overflow-hidden rounded-lg border border-line bg-sheet sm:block">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="text-xs text-graphite">
                    <th className="w-20 px-5 py-3 font-normal">Attempt</th>
                    <th className="px-5 py-3 font-normal">Taken</th>
                    <th className="w-56 px-5 py-3 text-right font-normal">Score</th>
                    <th className="px-5 py-3 font-normal">Result</th>
                    <th className="px-5 py-3">
                      <span className="sr-only">Report</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {sessions.map((s, index) => {
                    const date = new Date(s.completedAt)
                    const passed = s.rawScore >= TEST_PASS
                    return (
                      <tr key={s.sessionId} className="border-t border-rule">
                        <td className="figures px-5 py-3.5 text-graphite">#{s.attemptNumber ?? sessions.length - index}</td>
                        <td className="px-5 py-3.5">
                          <div className="text-ink">{formatDate(date)}</div>
                          <div className="type-meta">{formatTime(date)}</div>
                        </td>
                        <td className="px-5 py-3.5">
                          <div className="figures text-right">
                            <span className="font-semibold text-ink">{s.rawScore}</span>
                            <span className="text-graphite"> / {TEST_MAX}</span>
                          </div>
                          <ScoreBar score={s.rawScore} max={TEST_MAX} pass={TEST_PASS} className="ml-auto mt-1.5 w-36" />
                        </td>
                        <td className="px-5 py-3.5">
                          <StatusPill tone={passed ? 'positive' : 'negative'}>{passed ? 'Passed' : 'Below'}</StatusPill>
                        </td>
                        <td className="px-5 py-3.5 text-right">
                          <Button size="sm" onClick={() => openReport(s.sessionId)}>
                            View report
                          </Button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            {/* Two-line rows on phones */}
            <ul className="divide-y divide-rule rounded-lg border border-line bg-sheet sm:hidden">
              {sessions.map((s, index) => {
                const date = new Date(s.completedAt)
                const passed = s.rawScore >= TEST_PASS
                return (
                  <li key={s.sessionId}>
                    <button
                      type="button"
                      onClick={() => openReport(s.sessionId)}
                      className="flex w-full items-center justify-between gap-4 px-4 py-3.5 text-left hover:bg-wash"
                    >
                      <span className="min-w-0">
                        <span className="block text-sm text-ink">
                          Attempt #{s.attemptNumber ?? sessions.length - index}
                        </span>
                        <span className="type-meta block">
                          {formatDate(date)}, {formatTime(date)}
                        </span>
                      </span>
                      <span className="flex shrink-0 flex-col items-end gap-1">
                        <span className="figures text-sm">
                          <span className="font-semibold text-ink">{s.rawScore}</span>
                          <span className="text-graphite"> / {TEST_MAX}</span>
                        </span>
                        <StatusPill tone={passed ? 'positive' : 'negative'}>{passed ? 'Passed' : 'Below'}</StatusPill>
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

/** "3 tests. Latest 50, best 50. 1 of 3 passed." The newest comes first in the list. */
function summarise(sessions: testAPI.TestSessionListItem[]): string {
  const latest = sessions[0].rawScore
  const best = Math.max(...sessions.map((s) => s.rawScore))
  const passed = sessions.filter((s) => s.rawScore >= TEST_PASS).length
  const count = `${sessions.length} ${sessions.length === 1 ? 'test' : 'tests'}`
  if (sessions.length === 1) return `${count}, scored ${latest} of ${TEST_MAX}.`
  return `${count}. Latest ${latest}, best ${best}. ${passed} of ${sessions.length} cleared the pass mark of ${TEST_PASS}.`
}

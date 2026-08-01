import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Plus } from 'lucide-react'
import * as testAPI from '../api/tests'
import * as topicAPI from '../api/topics'
import AppHeader from '../components/AppHeader'
import PageContainer from '../components/PageContainer'

export default function TestHistoryPage() {
  const navigate = useNavigate()
  const { topicId } = useParams<{ topicId: string }>()

  const [topicName, setTopicName] = useState<string>('')
  const [sessions, setSessions] = useState<testAPI.TestSessionListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!topicId) return
    Promise.all([topicAPI.listTopics(), testAPI.listTestSessions(topicId)])
      .then(([topics, s]) => {
        const t = topics.find((x) => x.id === topicId)
        setTopicName(t?.name ?? 'Topic')
        // Sort descending by completedAt
        const sorted = [...s].sort(
          (a, b) => new Date(b.completedAt).getTime() - new Date(a.completedAt).getTime()
        )
        setSessions(sorted)
      })
      .catch(() => setError('Failed to load test history.'))
      .finally(() => setLoading(false))
  }, [topicId])

  if (loading) {
    return (
      <div className="min-h-screen bg-bg">
        <AppHeader onBack={() => navigate('/dashboard')} subtitle="Test History" />
        <PageContainer maxWidth="max-w-4xl">
          <p className="text-sm text-muted">Loading test history…</p>
        </PageContainer>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-bg">
        <AppHeader onBack={() => navigate('/dashboard')} subtitle="Test History" />
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
    <div className="min-h-screen bg-bg">
      <AppHeader
        onBack={() => navigate('/dashboard')}
        title={topicName}
        subtitle="Test History"
        actions={
          <button
            onClick={() => navigate(`/topics/${topicId}/test`)}
            className="flex h-9 items-center gap-1.5 rounded-lg bg-primary px-3 text-sm font-bold text-primary-fg transition-colors hover:bg-primary-hover"
          >
            <Plus size={15} />
            <span className="hidden sm:inline">New Test</span>
          </button>
        }
      />

      <PageContainer maxWidth="max-w-4xl">
        {sessions.length === 0 ? (
          <div className="flex flex-col items-center gap-4 rounded-2xl border border-dashed border-border bg-surface/50 px-6 py-14 text-center">
            <p className="text-sm font-medium text-muted">No tests taken yet for this topic.</p>
            <button
              onClick={() => navigate(`/topics/${topicId}/test`)}
              className="rounded-lg bg-primary px-5 py-2.5 text-sm font-bold text-primary-fg transition-colors hover:bg-primary-hover"
            >
              Take Your First Test
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
                    <th className="px-4 py-3">Score</th>
                    <th className="px-4 py-3">Result</th>
                    <th className="px-4 py-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {sessions.map((s, index) => {
                    const date = new Date(s.completedAt)
                    const passed = s.rawScore >= 36
                    const pct = Math.max(0, Math.round((s.rawScore / 60) * 100))
                    return (
                      <tr key={s.sessionId} className="border-t border-border bg-surface transition-colors hover:bg-surface-hover">
                        <td className="px-4 py-3.5 font-semibold text-muted">{sessions.length - index}</td>
                        <td className="px-4 py-3.5">
                          <div className="font-medium text-fg">
                            {date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                          </div>
                          <div className="text-xs text-muted">
                            {date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                          </div>
                        </td>
                        <td className="px-4 py-3.5">
                          <span className="font-bold text-fg">{s.rawScore}</span>
                          <span className="text-muted">/60</span>
                          <span className="ml-1 text-xs text-muted">({pct}%)</span>
                        </td>
                        <td className="px-4 py-3.5">
                          <span
                            className={`rounded-full px-2.5 py-1 text-xs font-bold ${
                              passed ? 'bg-success-subtle text-success-fg' : 'bg-danger-subtle text-danger-fg'
                            }`}
                          >
                            {passed ? 'Pass' : 'Fail'}
                          </span>
                        </td>
                        <td className="px-4 py-3.5 text-right">
                          <button
                            onClick={() => navigate(`/topics/${topicId}/tests/${s.sessionId}/report`)}
                            className="rounded-lg border border-border px-3 py-1.5 text-xs font-bold text-fg transition-colors hover:bg-surface-hover"
                          >
                            View Report
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
              {sessions.map((s, index) => {
                const date = new Date(s.completedAt)
                const passed = s.rawScore >= 36
                const pct = Math.max(0, Math.round((s.rawScore / 60) * 100))
                return (
                  <button
                    key={s.sessionId}
                    onClick={() => navigate(`/topics/${topicId}/tests/${s.sessionId}/report`)}
                    className="flex flex-col gap-2 rounded-2xl border border-border bg-surface p-4 text-left transition-colors hover:bg-surface-hover"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-muted">Test #{sessions.length - index}</span>
                      <span
                        className={`rounded-full px-2.5 py-1 text-xs font-bold ${
                          passed ? 'bg-success-subtle text-success-fg' : 'bg-danger-subtle text-danger-fg'
                        }`}
                      >
                        {passed ? 'Pass' : 'Fail'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-bold text-fg">
                          {date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                        </p>
                        <p className="text-xs text-muted">
                          {date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                        </p>
                      </div>
                      <p className="text-sm font-bold text-fg">
                        {s.rawScore}/60 <span className="font-normal text-muted">({pct}%)</span>
                      </p>
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

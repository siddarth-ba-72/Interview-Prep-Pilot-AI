import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import * as testAPI from '../api/tests'
import * as topicAPI from '../api/topics'
import './TestHistoryPage.css'

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
      <div className="history-page">
        <p className="history-loading">Loading test history…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="history-page history-page--error">
        <p>{error}</p>
        <button onClick={() => navigate('/dashboard')}>Back to Dashboard</button>
      </div>
    )
  }

  return (
    <div className="history-page">
      <div className="history-header">
        <div>
          <button className="back-button" onClick={() => navigate('/dashboard')}>
            ← Dashboard
          </button>
        </div>
        <h1 className="history-title">
          {topicName} — Test History
        </h1>
        <button
          className="history-new-test-button"
          onClick={() => navigate(`/topics/${topicId}/test`)}
        >
          + New Test
        </button>
      </div>

      {sessions.length === 0 ? (
        <div className="history-empty">
          <p>No tests taken yet for this topic.</p>
          <button
            className="history-start-button"
            onClick={() => navigate(`/topics/${topicId}/test`)}
          >
            Take Your First Test
          </button>
        </div>
      ) : (
        <div className="history-table-wrapper">
          <table className="history-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Date &amp; Time</th>
                <th>Score</th>
                <th>Result</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((s, index) => {
                const date = new Date(s.completedAt)
                const passed = s.rawScore >= 36
                const pct = Math.max(0, Math.round((s.rawScore / 60) * 100))
                return (
                  <tr key={s.sessionId} className={passed ? 'row-pass' : 'row-fail'}>
                    <td className="col-number">{sessions.length - index}</td>
                    <td className="col-date">
                      <span className="date-primary">
                        {date.toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric',
                        })}
                      </span>
                      <span className="date-secondary">
                        {date.toLocaleTimeString('en-US', {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </td>
                    <td className="col-score">
                      <span className="score-value">{s.rawScore}</span>
                      <span className="score-max">/60</span>
                      <span className="score-pct">({pct}%)</span>
                    </td>
                    <td className="col-result">
                      <span className={`badge ${passed ? 'badge-pass' : 'badge-fail'}`}>
                        {passed ? 'Pass' : 'Fail'}
                      </span>
                    </td>
                    <td className="col-action">
                      <button
                        className="view-report-button"
                        onClick={() =>
                          navigate(`/topics/${topicId}/tests/${s.sessionId}/report`)
                        }
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
      )}
    </div>
  )
}

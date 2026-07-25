import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useAppSelector } from '../hooks'
import * as testAPI from '../api/tests'
import './TestReportPage.css'

export default function TestReportPage() {
  const navigate = useNavigate()
  const params = useParams<{ topicId: string; testId: string }>()
  const topicId = params.topicId!
  const testId = params.testId!
  
  const [report, setReport] = useState<testAPI.TestReportResponse | null>(null)
  const [expandedSections, setExpandedSections] = useState<{ [key: string]: boolean }>({
    MCQ: true,
    SUBJECTIVE: true,
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Try to get report from Redux first, otherwise fetch
  const reports = useAppSelector((state: any) => state.tests.reportsBySessionId)
  const cachedReport = reports[testId]

  useEffect(() => {
    if (!topicId || !testId) {
      setError('Topic ID or Test ID is missing')
      setLoading(false)
      return
    }

    async function loadReport() {
      try {
        if (cachedReport) {
          setReport(cachedReport)
        } else {
          const data = await testAPI.getTestReport(topicId, testId)
          setReport(data)
        }
      } catch (err) {
        setError((err as Error).message || 'Failed to load report')
      } finally {
        setLoading(false)
      }
    }

    loadReport()
  }, [topicId, testId, cachedReport])

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }))
  }

  if (loading) {
    return <div className="report-page"><p>Loading report...</p></div>
  }

  if (error) {
    return (
      <div className="report-page error">
        <p>{error}</p>
        <button onClick={() => navigate('/dashboard')}>Back to Dashboard</button>
      </div>
    )
  }

  if (!report) {
    return <div className="report-page"><p>Report not found</p></div>
  }

  const mcqResults = report.questionSummary.filter((q: testAPI.QuestionResult) => q.section === 'MCQ')
  const subjectiveResults = report.questionSummary.filter((q: testAPI.QuestionResult) => q.section === 'SUBJECTIVE')

  return (
    <div className="report-page">
      <div className="report-header">
        <h1>Test Report</h1>
        <button className="back-button" onClick={() => navigate(`/topics/${topicId}/tests`)}>← Test History</button>
      </div>

      <div className="report-content">
        {/* Score Summary */}
        <section className="score-summary">
          <h2>Score Summary</h2>
          <div className="summary-grid">
            <div className="summary-item">
              <h3>Raw Score</h3>
              <p className="score-value">{report.rawScore} / {report.maxScore}</p>
            </div>
            <div className="summary-item">
              <h3>Percentage</h3>
              <p className="score-value">{((report.rawScore / report.maxScore) * 100).toFixed(1)}%</p>
            </div>
            <div className="summary-item">
              <h3>Status</h3>
              <p className={`status ${report.passed ? 'passed' : 'failed'}`}>
                {report.passed ? 'PASSED' : 'FAILED'}
              </p>
            </div>
            <div className="summary-item">
              <h3>All-Time Average</h3>
              <p className="score-value">
                {report.avgScoreAtTime ? report.avgScoreAtTime.toFixed(1) : '—'} / {report.maxScore}
              </p>
            </div>
          </div>
        </section>

        {/* Strengths & Weaknesses */}
        <section className="strengths-weaknesses">
          <div className="strength-section">
            <h3>Strengths</h3>
            <ul className="tag-list strengths">
              {report.strengths.map((strength: string, idx: number) => (
                <li key={idx} className="tag strength-tag">{strength}</li>
              ))}
            </ul>
          </div>
          <div className="weakness-section">
            <h3>Areas for Improvement</h3>
            <ul className="tag-list weaknesses">
              {report.weaknesses.map((weakness: string, idx: number) => (
                <li key={idx} className="tag weakness-tag">{weakness}</li>
              ))}
            </ul>
          </div>
        </section>

        {/* Question Breakdown */}
        <section className="question-breakdown">
          <h2>Question Breakdown</h2>

          {/* MCQ Section */}
          {mcqResults.length > 0 && (
            <div className="breakdown-section">
              <div
                className="section-header"
                onClick={() => toggleSection('MCQ')}
              >
                <h3>Multiple Choice Questions ({mcqResults.length})</h3>
                <span className="toggle-icon">{expandedSections.MCQ ? '▼' : '▶'}</span>
              </div>

              {expandedSections.MCQ && (
                <div className="section-content">
                  {mcqResults.map((result: testAPI.QuestionResult, idx: number) => (
                    <div key={result.questionId} className={`question-result ${result.isCorrect ? 'correct' : 'incorrect'}`}>
                      <div className="question-header">
                        <h4>Question {idx + 1}</h4>
                        <span className={`badge ${result.isCorrect ? 'correct-badge' : 'incorrect-badge'}`}>
                          {result.isCorrect ? `+${result.pointsAwarded}` : `${result.pointsAwarded}`}
                        </span>
                      </div>
                      <p className="question-text">{result.questionText}</p>
                      <div className="answer-section">
                        <div className="answer-item">
                          <strong>Your Answer:</strong>
                          <p className={result.isCorrect ? 'correct-answer' : 'incorrect-answer'}>
                            {result.userAnswer || '(Not answered)'}
                          </p>
                        </div>
                        <div className="answer-item">
                          <strong>Correct Answer:</strong>
                          <p className="correct-answer">{result.correctAnswer}</p>
                        </div>
                      </div>
                      <p className="evaluation">{result.evaluation}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Subjective Section */}
          {subjectiveResults.length > 0 && (
            <div className="breakdown-section">
              <div
                className="section-header"
                onClick={() => toggleSection('SUBJECTIVE')}
              >
                <h3>Subjective / Code Completion ({subjectiveResults.length})</h3>
                <span className="toggle-icon">{expandedSections.SUBJECTIVE ? '▼' : '▶'}</span>
              </div>

              {expandedSections.SUBJECTIVE && (
                <div className="section-content">
                  {subjectiveResults.map((result: testAPI.QuestionResult, idx: number) => (
                    <div key={result.questionId} className={`question-result ${result.isCorrect ? 'correct' : 'incorrect'}`}>
                      <div className="question-header">
                        <h4>Question {idx + mcqResults.length + 1}</h4>
                        <span className={`badge ${result.isCorrect ? 'correct-badge' : 'incorrect-badge'}`}>
                          {result.isCorrect ? `+${result.pointsAwarded}` : `${result.pointsAwarded}`}
                        </span>
                      </div>
                      <p className="question-text">{result.questionText}</p>
                      <div className="answer-section">
                        <div className="answer-item">
                          <strong>Your Answer:</strong>
                          <pre className={result.isCorrect ? 'code-block correct-answer' : 'code-block incorrect-answer'}>
                            {result.userAnswer || '(Not answered)'}
                          </pre>
                        </div>
                        <div className="answer-item">
                          <strong>Model Answer:</strong>
                          <pre className="code-block correct-answer">{result.correctAnswer}</pre>
                        </div>
                      </div>
                      <p className="evaluation">{result.evaluation}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>

        {/* Action Buttons */}
        <div className="report-actions">
          <button
            className="button-primary"
            onClick={() => navigate(`/topics/${topicId}/learn`)}
          >
            Revisit Learn Mode
          </button>
          <button
            className="button-secondary"
            onClick={() => navigate('/dashboard')}
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    </div>
  )
}

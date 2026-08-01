import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { useAppSelector } from '../hooks'
import * as testAPI from '../api/tests'
import AppHeader from '../components/AppHeader'
import PageContainer from '../components/PageContainer'

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
    return (
      <div className="min-h-screen bg-bg">
        <AppHeader onBack={() => navigate(`/topics/${topicId}/tests`)} subtitle="Test Report" />
        <PageContainer maxWidth="max-w-4xl">
          <p className="text-sm text-muted">Loading report...</p>
        </PageContainer>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-bg">
        <AppHeader onBack={() => navigate(`/topics/${topicId}/tests`)} subtitle="Test Report" />
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

  if (!report) {
    return (
      <div className="min-h-screen bg-bg">
        <AppHeader onBack={() => navigate(`/topics/${topicId}/tests`)} subtitle="Test Report" />
        <PageContainer maxWidth="max-w-4xl">
          <p className="text-sm text-muted">Report not found</p>
        </PageContainer>
      </div>
    )
  }

  const mcqResults = report.questionSummary.filter((q: testAPI.QuestionResult) => q.section === 'MCQ')
  const subjectiveResults = report.questionSummary.filter((q: testAPI.QuestionResult) => q.section === 'SUBJECTIVE')

  const sections = [
    { key: 'MCQ', label: 'Multiple Choice Questions', results: mcqResults, offset: 0 },
    { key: 'SUBJECTIVE', label: 'Subjective / Code Completion', results: subjectiveResults, offset: mcqResults.length },
  ]

  return (
    <div className="min-h-screen bg-bg">
      <AppHeader onBack={() => navigate(`/topics/${topicId}/tests`)} title="Test Report" />

      <PageContainer maxWidth="max-w-4xl" className="flex flex-col gap-8">
        <section>
          <h2 className="mb-3 text-lg font-bold text-fg">Score Summary</h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-2xl border border-border bg-surface p-4 text-center">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">Raw Score</h3>
              <p className="mt-1 text-xl font-extrabold text-primary">
                {report.rawScore} / {report.maxScore}
              </p>
            </div>
            <div className="rounded-2xl border border-border bg-surface p-4 text-center">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">Percentage</h3>
              <p className="mt-1 text-xl font-extrabold text-primary">
                {((report.rawScore / report.maxScore) * 100).toFixed(1)}%
              </p>
            </div>
            <div className="rounded-2xl border border-border bg-surface p-4 text-center">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">Status</h3>
              <p
                className={`mt-1 text-sm font-extrabold ${
                  report.passed ? 'text-success-fg' : 'text-danger-fg'
                }`}
              >
                {report.passed ? 'PASSED' : 'FAILED'}
              </p>
            </div>
            <div className="rounded-2xl border border-border bg-surface p-4 text-center">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">All-Time Average</h3>
              <p className="mt-1 text-xl font-extrabold text-primary">
                {report.avgScoreAtTime ? report.avgScoreAtTime.toFixed(1) : '—'} / {report.maxScore}
              </p>
            </div>
          </div>
        </section>

        <section className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <h3 className="mb-2 text-sm font-bold text-fg">Strengths</h3>
            <ul className="flex flex-wrap gap-2">
              {report.strengths.map((strength: string, idx: number) => (
                <li key={idx} className="rounded-full bg-success-subtle px-3 py-1 text-xs font-semibold text-success-fg">
                  {strength}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="mb-2 text-sm font-bold text-fg">Areas for Improvement</h3>
            <ul className="flex flex-wrap gap-2">
              {report.weaknesses.map((weakness: string, idx: number) => (
                <li key={idx} className="rounded-full bg-danger-subtle px-3 py-1 text-xs font-semibold text-danger-fg">
                  {weakness}
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-bold text-fg">Question Breakdown</h2>
          <div className="flex flex-col gap-4">
            {sections.map(
              ({ key, label, results, offset }) =>
                results.length > 0 && (
                  <div key={key} className="overflow-hidden rounded-2xl border border-border bg-surface">
                    <button
                      onClick={() => toggleSection(key)}
                      className="flex w-full items-center justify-between px-5 py-4 text-left"
                    >
                      <h3 className="text-sm font-bold text-fg">
                        {label} ({results.length})
                      </h3>
                      {expandedSections[key] ? (
                        <ChevronDown size={16} className="text-muted" />
                      ) : (
                        <ChevronRight size={16} className="text-muted" />
                      )}
                    </button>

                    {expandedSections[key] && (
                      <div className="divide-y divide-border border-t border-border">
                        {results.map((result: testAPI.QuestionResult, idx: number) => (
                          <div
                            key={result.questionId}
                            className={`border-l-4 p-5 ${
                              result.isCorrect ? 'border-success' : 'border-danger'
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <h4 className="text-sm font-bold text-fg">Question {idx + offset + 1}</h4>
                              <span
                                className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${
                                  result.isCorrect ? 'bg-success-subtle text-success-fg' : 'bg-danger-subtle text-danger-fg'
                                }`}
                              >
                                {result.isCorrect ? `+${result.pointsAwarded}` : `${result.pointsAwarded}`}
                              </span>
                            </div>
                            <p className="mt-2 text-sm text-fg">{result.questionText}</p>

                            <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
                              <div>
                                <p className="text-xs font-semibold uppercase tracking-wide text-muted">Your Answer</p>
                                {key === 'SUBJECTIVE' ? (
                                  <pre
                                    className={`mt-1 whitespace-pre-wrap rounded-lg bg-bg p-3 font-mono text-xs ${
                                      result.isCorrect ? 'text-success-fg' : 'text-danger-fg'
                                    }`}
                                  >
                                    {result.userAnswer || '(Not answered)'}
                                  </pre>
                                ) : (
                                  <p className={`mt-1 text-sm ${result.isCorrect ? 'text-success-fg' : 'text-danger-fg'}`}>
                                    {result.userAnswer || '(Not answered)'}
                                  </p>
                                )}
                              </div>
                              <div>
                                <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                                  {key === 'SUBJECTIVE' ? 'Model Answer' : 'Correct Answer'}
                                </p>
                                {key === 'SUBJECTIVE' ? (
                                  <pre className="mt-1 whitespace-pre-wrap rounded-lg bg-bg p-3 font-mono text-xs text-success-fg">
                                    {result.correctAnswer}
                                  </pre>
                                ) : (
                                  <p className="mt-1 text-sm text-success-fg">{result.correctAnswer}</p>
                                )}
                              </div>
                            </div>

                            <p className="mt-3 text-sm italic text-muted">{result.evaluation}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )
            )}
          </div>
        </section>

        <div className="flex flex-col-reverse gap-3 pb-4 sm:flex-row sm:justify-end">
          <button
            onClick={() => navigate('/dashboard')}
            className="rounded-lg border border-border px-5 py-2.5 text-sm font-bold text-fg transition-colors hover:bg-surface-hover"
          >
            Back to Dashboard
          </button>
          <button
            onClick={() => navigate(`/topics/${topicId}/learn`)}
            className="rounded-lg bg-primary px-5 py-2.5 text-sm font-bold text-primary-fg transition-colors hover:bg-primary-hover"
          >
            Revisit Learn Mode
          </button>
        </div>
      </PageContainer>
    </div>
  )
}

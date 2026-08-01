import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useAppDispatch, useAppSelector } from '../hooks'
import * as testAPI from '../api/tests'
import * as topicAPI from '../api/topics'
import type { RootState } from '../store'
import {
  setTestGenerating,
  setTestSession,
  updateAnswer,
  setTestSubmitting,
  setTestCompleted,
  openResultsModal,
} from '../features/tests/testSlice'
import ResultsModal from '../components/ResultsModal'
import AppHeader from '../components/AppHeader'
import PageContainer from '../components/PageContainer'

export default function TestPage() {
  const navigate = useNavigate()
  const params = useParams<{ topicId: string }>()
  const topicId = params.topicId!
  const dispatch = useAppDispatch()

  const [topic, setTopic] = useState<topicAPI.Topic | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const testState = useAppSelector((state: RootState) => state.tests.activeSessionByTopicId[topicId])

  // Load topic and initialize test on mount
  useEffect(() => {
    if (!topicId) {
      setError('Topic ID is missing')
      setLoading(false)
      return
    }

    async function loadTopicAndTest() {
      try {
        const topics = await topicAPI.listTopics()
        const currentTopic = topics.find((t: topicAPI.Topic) => t.id === topicId)
        if (!currentTopic) {
          setError('Topic not found')
          return
        }
        setTopic(currentTopic)

        // Start test
        dispatch(setTestGenerating({ topicId }))
        const response = await testAPI.startTest(topicId)
        dispatch(
          setTestSession({
            topicId,
            sessionId: response.sessionId,
            questions: response.questions,
            attemptNumber: response.attemptNumber,
            basedOnPreviousAttempt: response.basedOnPreviousAttempt,
          })
        )
      } catch (err) {
        setError((err as Error).message || 'Failed to load test')
      } finally {
        setLoading(false)
      }
    }

    loadTopicAndTest()
  }, [topicId, dispatch])

  const handleAnswerChange = (questionId: string, answer: string | null): void => {
    dispatch(updateAnswer({ topicId, questionId, answer }))
  }

  const handleSubmit = async () => {
    if (!testState) return

    const unansweredCount = testState.questions.length -
      Object.values(testState.answers).filter((a) => a !== null).length

    if (unansweredCount > 0) {
      if (!confirm(`${unansweredCount} of ${testState.questions.length} questions unanswered. Submit anyway?`)) {
        return
      }
    }

    try {
      dispatch(setTestSubmitting({ topicId }))

      const answers: testAPI.SubmitAnswerRequest[] = testState.questions.map((q: testAPI.TestQuestion) => ({
        questionId: q.questionId,
        userAnswer: testState.answers[q.questionId] || null,
      }))

      const report = await testAPI.submitTest(topicId, testState.sessionId!, {
        answers,
      })

      dispatch(setTestCompleted({ topicId, report }))
      dispatch(openResultsModal({ sessionId: testState.sessionId! }))
    } catch (err) {
      setError((err as Error).message || 'Failed to submit test')
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-bg">
        <AppHeader onBack={() => navigate('/dashboard')} subtitle="Test Mode" />
        <PageContainer maxWidth="max-w-3xl">
          <p className="text-sm text-muted">Generating test...</p>
        </PageContainer>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-bg">
        <AppHeader onBack={() => navigate('/dashboard')} subtitle="Test Mode" />
        <PageContainer maxWidth="max-w-3xl" className="flex flex-col items-start gap-4">
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

  if (!testState || !topic) {
    return (
      <div className="min-h-screen bg-bg">
        <AppHeader onBack={() => navigate('/dashboard')} subtitle="Test Mode" />
        <PageContainer maxWidth="max-w-3xl">
          <p className="text-sm text-muted">Loading...</p>
        </PageContainer>
      </div>
    )
  }

  const mcqQuestions = testState.questions.filter((q: testAPI.TestQuestion) => q.section === 'MCQ')
  const subjectiveQuestions = testState.questions.filter((q: testAPI.TestQuestion) => q.section === 'SUBJECTIVE')
  const answeredCount = Object.values(testState.answers).filter((a) => a !== null).length
  const isSubmitting = testState.status === 'submitting'

  return (
    <div className="min-h-screen bg-bg">
      <AppHeader onBack={() => navigate('/dashboard')} title={topic.name} subtitle="Test Mode" />

      <PageContainer maxWidth="max-w-3xl" className="flex flex-col gap-8">
        <div>
          <div className="mb-2 flex items-center gap-2">
            <span className="rounded-full bg-primary-subtle px-3 py-1 text-xs font-bold text-primary">
              Attempt #{testState.attemptNumber ?? 1}
            </span>
            {testState.basedOnPreviousAttempt && (
              <span className="rounded-full bg-warning-subtle px-3 py-1 text-xs font-semibold text-warning-fg">
                Focused on your weak areas from last attempt
              </span>
            )}
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-border">
            <div
              className="h-full rounded-full bg-primary transition-all duration-300"
              style={{ width: `${(answeredCount / testState.questions.length) * 100}%` }}
            />
          </div>
          <p className="mt-2 text-sm text-muted">
            {answeredCount} of {testState.questions.length} questions answered
          </p>
        </div>

        <section className="flex flex-col gap-4">
          <h2 className="text-lg font-bold text-fg">
            Multiple Choice Questions <span className="text-sm font-medium text-muted">(10 questions)</span>
          </h2>
          {mcqQuestions.map((question: testAPI.TestQuestion, idx: number) => (
            <div key={question.questionId} className="rounded-2xl border border-border bg-surface p-5">
              <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">Question {idx + 1}</h3>
              <p className="mb-4 text-sm font-medium text-fg">{question.text}</p>
              <div className="flex flex-col gap-2">
                {question.options?.map((option: string) => {
                  const checked = testState.answers[question.questionId] === option
                  return (
                    <label
                      key={option}
                      className={`flex cursor-pointer items-center gap-3 rounded-lg border px-3.5 py-2.5 text-sm transition-colors ${
                        checked
                          ? 'border-primary bg-primary-subtle text-fg'
                          : 'border-border text-fg hover:bg-surface-hover'
                      }`}
                    >
                      <input
                        type="radio"
                        name={question.questionId}
                        value={option}
                        checked={checked}
                        onChange={(e) => handleAnswerChange(question.questionId, e.target.value)}
                        disabled={isSubmitting}
                        className="h-4 w-4 accent-primary"
                      />
                      {option}
                    </label>
                  )
                })}
              </div>
            </div>
          ))}
        </section>

        <section className="flex flex-col gap-4">
          <h2 className="text-lg font-bold text-fg">
            Subjective / Code Completion <span className="text-sm font-medium text-muted">(10 questions)</span>
          </h2>
          {subjectiveQuestions.map((question: testAPI.TestQuestion, idx: number) => (
            <div key={question.questionId} className="rounded-2xl border border-border bg-surface p-5">
              <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">
                Question {idx + 1 + mcqQuestions.length}
              </h3>
              <p className="mb-4 text-sm font-medium text-fg">{question.text}</p>
              <textarea
                value={testState.answers[question.questionId] || ''}
                onChange={(e) => handleAnswerChange(question.questionId, e.target.value || null)}
                placeholder="Enter your answer here..."
                disabled={isSubmitting}
                className="min-h-32 w-full rounded-lg border border-border bg-bg p-3 font-mono text-sm text-fg outline-none transition-colors placeholder:font-sans placeholder:text-muted focus:border-primary focus:ring-2 focus:ring-primary/20"
              />
            </div>
          ))}
        </section>

        <div className="flex justify-end pb-4">
          <button
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="rounded-xl bg-primary px-6 py-3 text-sm font-bold text-primary-fg transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isSubmitting ? 'Submitting...' : 'Submit Test'}
          </button>
        </div>
      </PageContainer>

      <ResultsModal />
    </div>
  )
}

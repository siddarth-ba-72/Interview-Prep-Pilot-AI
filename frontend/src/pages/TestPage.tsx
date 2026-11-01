import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useAppDispatch, useAppSelector } from '../hooks'
import * as testAPI from '../api/tests'
import * as topicAPI from '../api/topics'
import { trackEvent } from '../features/analytics/clarity'
import type { RootState } from '../store'
import {
  setTestGenerating,
  setTestSession,
  updateAnswer,
  setTestSubmitting,
  setTestSubmitFailed,
  setTestCompleted,
  openResultsModal,
} from '../features/tests/testSlice'
import ResultsModal from '../components/ResultsModal'
import AppHeader from '../components/AppHeader'
import TopicHeader from '../components/TopicHeader'
import PageContainer, { WIDTH } from '../components/PageContainer'
import { Button } from '../components/ui/Button'
import { textareaClass } from '../components/ui/field'
import Notice from '../components/ui/Notice'
import StatusPill from '../components/ui/StatusPill'
import Spinner from '../components/ui/Spinner'

/**
 * One start request per topic at a time. React's StrictMode runs effects twice in development, and a
 * second, later response would replace a test the learner has already started answering.
 */
const startRequests = new Map<string, Promise<testAPI.TestSessionStartResponse>>()

function startTestOnce(topicId: string): Promise<testAPI.TestSessionStartResponse> {
  const pending = startRequests.get(topicId)
  if (pending) return pending
  const request = testAPI.startTest(topicId).finally(() => startRequests.delete(topicId))
  startRequests.set(topicId, request)
  return request
}

export default function TestPage() {
  const navigate = useNavigate()
  const params = useParams<{ topicId: string }>()
  const topicId = params.topicId!
  const dispatch = useAppDispatch()

  const [loadError, setLoadError] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [confirmingBlank, setConfirmingBlank] = useState(false)

  const testState = useAppSelector((state: RootState) => state.tests.activeSessionByTopicId[topicId])

  // Start the test on mount; the server returns the in-progress one if there is one
  useEffect(() => {
    if (!topicId) {
      setLoadError('Topic ID is missing')
      setLoading(false)
      return
    }
    let cancelled = false

    async function loadTest() {
      try {
        dispatch(setTestGenerating({ topicId }))
        const response = await startTestOnce(topicId)
        if (cancelled) return
        dispatch(
          setTestSession({
            topicId,
            sessionId: response.sessionId,
            questions: response.questions,
            attemptNumber: response.attemptNumber,
            basedOnPreviousAttempt: response.basedOnPreviousAttempt,
          })
        )
        trackEvent('test_started')
      } catch (err) {
        if (!cancelled) setLoadError(topicAPI.extractErrorMessage(err, (err as Error).message || 'Failed to load test'))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    loadTest()
    return () => {
      cancelled = true
    }
  }, [topicId, dispatch])

  const handleAnswerChange = (questionId: string, answer: string | null): void => {
    dispatch(updateAnswer({ topicId, questionId, answer }))
  }

  const blankCount = testState
    ? testState.questions.length - Object.values(testState.answers).filter((a) => a !== null).length
    : 0

  const submit = async () => {
    if (!testState?.sessionId) return
    setConfirmingBlank(false)
    setSubmitError(null)
    try {
      dispatch(setTestSubmitting({ topicId }))
      const answers: testAPI.SubmitAnswerRequest[] = testState.questions.map((q) => ({
        questionId: q.questionId,
        userAnswer: testState.answers[q.questionId] || null,
      }))
      const report = await testAPI.submitTest(topicId, testState.sessionId, { answers })
      dispatch(setTestCompleted({ topicId, report }))
      trackEvent('test_submitted')
      dispatch(openResultsModal({ sessionId: testState.sessionId }))
    } catch (err) {
      setSubmitError(topicAPI.extractErrorMessage(err, 'Could not grade your test. Your answers are still here; try again.'))
      dispatch(setTestSubmitFailed({ topicId }))
    }
  }

  const handleSubmit = () => {
    if (blankCount > 0 && !confirmingBlank) {
      setConfirmingBlank(true)
      return
    }
    void submit()
  }

  const ready = !loading && !loadError && testState && testState.status !== 'generating'

  return (
    <div className="min-h-screen">
      <AppHeader />
      <TopicHeader topicId={topicId} active="test" />

      {!ready && (
        <PageContainer maxWidth={WIDTH.topic}>
          {loadError ? (
            <Notice
              action={
                <Button size="sm" variant="ghost" onClick={() => navigate('/dashboard')}>
                  Back to topics
                </Button>
              }
            >
              {loadError}
            </Notice>
          ) : (
            <div className="rounded-lg border border-line bg-sheet px-5 py-6">
              <p className="flex items-center gap-2.5 text-sm font-medium text-ink">
                <Spinner />
                Writing your test…
              </p>
              <p className="type-body mt-1 pl-[26px] text-graphite">
                Ten multiple-choice and ten written questions, pitched at your track. This can take up to a minute.
              </p>
            </div>
          )}
        </PageContainer>
      )}

      {ready && (
        <TestPaper
          testState={testState}
          blankCount={blankCount}
          confirmingBlank={confirmingBlank}
          submitError={submitError}
          onAnswer={handleAnswerChange}
          onSubmit={handleSubmit}
          onCancelConfirm={() => setConfirmingBlank(false)}
        />
      )}

      <ResultsModal topicId={topicId} />
    </div>
  )
}

type TestState = NonNullable<RootState['tests']['activeSessionByTopicId'][string]>

function TestPaper({
  testState,
  blankCount,
  confirmingBlank,
  submitError,
  onAnswer,
  onSubmit,
  onCancelConfirm,
}: {
  testState: TestState
  blankCount: number
  confirmingBlank: boolean
  submitError: string | null
  onAnswer: (questionId: string, answer: string | null) => void
  onSubmit: () => void
  onCancelConfirm: () => void
}) {
  const mcq = testState.questions.filter((q) => q.section === 'MCQ')
  const written = testState.questions.filter((q) => q.section === 'SUBJECTIVE')
  const total = testState.questions.length
  const answered = total - blankCount
  const isSubmitting = testState.status === 'submitting'
  const isCompleted = testState.status === 'completed'

  return (
    <>
      {/* Progress stays in view while the paper scrolls */}
      <div className="sticky top-[53px] z-20 border-b border-line bg-paper">
        <div className={`mx-auto flex w-full ${WIDTH.topic} items-center gap-4 px-4 py-2.5 sm:px-6 lg:px-8`}>
          <span className="figures shrink-0 text-sm text-graphite">
            <span className="font-medium text-ink">{answered}</span> of {total} questions answered
          </span>
          <div className="h-1.5 min-w-0 flex-1 overflow-hidden rounded-full bg-press" aria-hidden>
            <div
              className="h-full origin-left rounded-full bg-ballpoint transition-transform duration-300 ease-out"
              style={{ transform: `scaleX(${total ? answered / total : 0})` }}
            />
          </div>
          <Button variant="primary" size="sm" onClick={onSubmit} disabled={isSubmitting || isCompleted} className="shrink-0">
            {isSubmitting && <Spinner size={14} className="text-action-ink" />}
            {isSubmitting ? 'Grading…' : 'Submit'}
          </Button>
        </div>
      </div>

      <PageContainer mask maxWidth={WIDTH.topic} className="flex flex-col gap-10">
        <div className="flex flex-wrap items-center gap-2">
          <StatusPill tone="neutral">Attempt #{testState.attemptNumber ?? 1}</StatusPill>
          {testState.basedOnPreviousAttempt && (
            <StatusPill tone="warning">Focused on your weak areas from last attempt</StatusPill>
          )}
        </div>

        <Section title="Multiple choice" rule={`${mcq.length} questions. A right answer scores +1, a wrong one −1, a blank 0.`}>
          {mcq.map((question, idx) => (
            <Question key={question.questionId} number={idx + 1} text={question.text}>
              <div className="flex flex-col gap-1.5" role="radiogroup" aria-label={`Question ${idx + 1} options`}>
                {question.options?.map((option) => {
                  const checked = testState.answers[question.questionId] === option
                  return (
                    <label
                      key={option}
                      className={`flex cursor-pointer items-start gap-3 rounded-md border px-3 py-2.5 text-sm leading-snug transition-colors duration-150 ${
                        checked ? 'border-ink bg-sheet ring-1 ring-ink' : 'border-line bg-sheet hover:border-edge hover:bg-wash'
                      }`}
                    >
                      <input
                        type="radio"
                        name={question.questionId}
                        value={option}
                        checked={checked}
                        onChange={(e) => onAnswer(question.questionId, e.target.value)}
                        disabled={isSubmitting || isCompleted}
                        className="mt-0.5 h-4 w-4 shrink-0 accent-ink"
                      />
                      <span className="text-ink">{option}</span>
                    </label>
                  )
                })}
              </div>
            </Question>
          ))}
        </Section>

        <Section title="Written answers" rule={`${written.length} questions. A right answer scores +5, a wrong one −5, a blank 0. Code is fine.`}>
          {written.map((question, idx) => (
            <Question key={question.questionId} number={idx + 1 + mcq.length} text={question.text}>
              <textarea
                aria-label={`Answer to question ${idx + 1 + mcq.length}`}
                value={testState.answers[question.questionId] || ''}
                onChange={(e) => onAnswer(question.questionId, e.target.value || null)}
                placeholder="Enter your answer here…"
                disabled={isSubmitting || isCompleted}
                className={`${textareaClass} min-h-32 resize-y font-mono text-[13px] placeholder:font-sans sm:text-[13px]`}
              />
            </Question>
          ))}
        </Section>

        <div className="flex flex-col items-stretch gap-3 border-t border-line pt-6 sm:flex-row sm:items-center sm:justify-between">
          {submitError ? (
            <Notice className="sm:flex-1">{submitError}</Notice>
          ) : confirmingBlank ? (
            <p className="text-sm text-ink">
              {blankCount} {blankCount === 1 ? 'question is' : 'questions are'} blank and will score 0. Submit anyway?
            </p>
          ) : (
            <p className="figures text-sm text-graphite">
              {blankCount === 0 ? 'Every question has an answer.' : `${blankCount} still blank.`}
            </p>
          )}
          <div className="flex shrink-0 gap-2">
            {confirmingBlank && (
              <Button onClick={onCancelConfirm} size="lg">
                Keep answering
              </Button>
            )}
            <Button variant="primary" size="lg" onClick={onSubmit} disabled={isSubmitting || isCompleted}>
              {isSubmitting ? 'Grading…' : confirmingBlank ? 'Submit anyway' : 'Submit test'}
            </Button>
          </div>
        </div>
      </PageContainer>
    </>
  )
}

function Section({ title, rule, children }: { title: string; rule: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-4">
      <div>
        <h2 className="type-section text-lg">{title}</h2>
        <p className="type-body text-graphite">{rule}</p>
      </div>
      <div className="divide-y divide-rule rounded-lg border border-line bg-sheet">{children}</div>
    </section>
  )
}

/** One question on the paper: its number in the margin, the question in the serif, then the answer. */
function Question({ number, text, children }: { number: number; text: string; children: React.ReactNode }) {
  return (
    <article className="grid grid-cols-[2rem_minmax(0,1fr)] gap-x-3 px-4 py-5 sm:grid-cols-[2.5rem_minmax(0,1fr)] sm:px-5">
      <h3 className="figures pt-0.5 text-sm font-medium text-graphite">
        <span className="sr-only">Question </span>
        {number}
      </h3>
      <div className="min-w-0">
        <p className="type-question mb-4 whitespace-pre-wrap text-[17px] leading-[1.55] text-ink">{text}</p>
        {children}
      </div>
    </article>
  )
}

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowRight, ChevronDown, Flag } from 'lucide-react'
import { useAppDispatch, useAppSelector } from '../hooks'
import type { RootState } from '../store'
import AppHeader from '../components/AppHeader'
import TopicHeader, { useTopicName } from '../components/TopicHeader'
import PageContainer, { WIDTH } from '../components/PageContainer'
import RatingBadge from '../components/RatingBadge'
import { Button } from '../components/ui/Button'
import { textareaClass } from '../components/ui/field'
import Notice from '../components/ui/Notice'
import Spinner from '../components/ui/Spinner'
import StatusPill from '../components/ui/StatusPill'
import * as interviewAPI from '../api/interviews'
import type { InterviewConfig } from '../api/interviews'
import { trackEvent } from '../features/analytics/clarity'
import {
  DIFFICULTIES,
  DURATIONS,
  EXPERIENCE_LEVELS,
  INTERVIEW_MAX,
  INTERVIEW_PASS,
  configLabel,
} from '../features/interviews/labels'
import {
  advanceToNextQuestion,
  interviewEnding,
  interviewEvaluating,
  interviewSessionLoaded,
  interviewStarting,
  interviewTurnCompleted,
  interviewTurnFailed,
  interviewReset,
  storeInterviewReport,
} from '../features/interviews/interviewSlice'

function formatCountdown(totalSeconds: number): string {
  const clamped = Math.max(0, totalSeconds)
  const minutes = Math.floor(clamped / 60)
  const seconds = clamped % 60
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

function countWords(text: string): number {
  const trimmed = text.trim()
  return trimmed ? trimmed.split(/\s+/).length : 0
}

export default function MockInterviewPage() {
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const { topicId = '' } = useParams<{ topicId: string }>()

  const session = useAppSelector((state: RootState) => state.interviews.activeSessionByTopicId[topicId])
  const topicName = useTopicName(topicId)
  // A college student (per their onboarding answers) only picks the duration; the backend
  // enforces the student level too.
  const profileIsStudent = useAppSelector((state: RootState) => state.auth.user?.experienceLevel === 'STUDENT')

  const [config, setConfig] = useState<InterviewConfig>(
    profileIsStudent
      ? { experienceLevel: 'STUDENT', difficulty: 'EASY', durationMinutes: 30 }
      : { experienceLevel: 'INTERMEDIATE', difficulty: 'MEDIUM', durationMinutes: 30 }
  )
  // Students get a fixed mix of mostly easy questions, so the difficulty picker is pinned to Easy.
  const isStudent = config.experienceLevel === 'STUDENT'
  const [answer, setAnswer] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [checkingForResume, setCheckingForResume] = useState(true)
  const [resumableSessionId, setResumableSessionId] = useState<string | null>(null)
  const [pastInterviewCount, setPastInterviewCount] = useState(0)
  const [confirmingEnd, setConfirmingEnd] = useState(false)
  const [remainingSeconds, setRemainingSeconds] = useState<number | null>(null)
  const [transcriptOpen, setTranscriptOpen] = useState(false)

  const answerRef = useRef(answer)
  const expiryHandledRef = useRef(false)
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)

  useEffect(() => {
    answerRef.current = answer
  }, [answer])

  const phase = session?.phase
  const sessionId = session?.sessionId ?? null
  const deadlineAt = session?.deadlineAt ?? null

  // ---------------------------------------------------------------- resume detection

  useEffect(() => {
    if (!topicId || session) {
      setCheckingForResume(false)
      return
    }
    let cancelled = false
    const findResumable = async () => {
      try {
        const sessions = await interviewAPI.listInterviews(topicId)
        const inProgress = sessions.find((item) => item.status === 'IN_PROGRESS')
        if (cancelled) return
        // The same lookup tells us whether there is any history worth linking to.
        setPastInterviewCount(sessions.filter((item) => item.status === 'COMPLETED').length)
        if (inProgress) {
          setResumableSessionId(inProgress.sessionId)
          setConfig(inProgress.config)
        }
      } catch {
        // A failed lookup only costs us the resume affordance - the config screen still works.
      } finally {
        if (!cancelled) setCheckingForResume(false)
      }
    }
    void findResumable()
    return () => {
      cancelled = true
    }
  }, [topicId, session])

  // ---------------------------------------------------------------- countdown

  useEffect(() => {
    if (!deadlineAt || phase === 'completed' || phase === 'ending') {
      return
    }
    const deadlineMs = new Date(deadlineAt).getTime()
    const tick = () => setRemainingSeconds(Math.max(0, Math.round((deadlineMs - Date.now()) / 1000)))
    tick()
    const interval = window.setInterval(tick, 1000)
    return () => window.clearInterval(interval)
  }, [deadlineAt, phase])

  // The session is cleared on the way out so returning to this route offers a fresh setup
  // screen rather than a stale "completed" session.
  const goToReport = useCallback(
    (report: interviewAPI.InterviewReportResponse, id: string) => {
      dispatch(storeInterviewReport({ report }))
      dispatch(interviewReset({ topicId }))
      navigate(`/topics/${topicId}/interviews/${id}/report`)
    },
    [dispatch, navigate, topicId],
  )

  const finalize = useCallback(
    async (id: string) => {
      dispatch(interviewEnding({ topicId }))
      try {
        const report = await interviewAPI.endInterview(topicId, id)
        trackEvent('interview_completed')
        goToReport(report, id)
      } catch (err) {
        setError(interviewAPI.interviewErrorMessage(err, 'Failed to generate the interview report'))
        dispatch(interviewTurnFailed({ topicId }))
      }
    },
    [dispatch, goToReport, topicId],
  )

  const submitAnswer = useCallback(
    async (text: string) => {
      if (!sessionId) return
      setBusy(true)
      setError(null)
      dispatch(interviewEvaluating({ topicId }))
      try {
        const response = await interviewAPI.answerInterview(topicId, sessionId, text)
        if (response.isComplete) {
          await finalize(sessionId)
          return
        }
        dispatch(
          interviewTurnCompleted({
            topicId,
            evaluation: response.evaluation,
            exchange: response.exchange,
            nextQuestion: response.nextQuestion,
            themeProgress: response.themeProgress,
          }),
        )
        setAnswer('')
      } catch (err) {
        setError(interviewAPI.interviewErrorMessage(err, 'Failed to submit your answer'))
        dispatch(interviewTurnFailed({ topicId }))
      } finally {
        setBusy(false)
      }
    },
    [dispatch, finalize, sessionId, topicId],
  )

  // The wall-clock deadline is authoritative. When the local countdown reaches it we submit
  // whatever is typed (spec section 2) and let the server decide whether it still counts.
  useEffect(() => {
    if (remainingSeconds === null || remainingSeconds > 0 || !sessionId) return
    if (expiryHandledRef.current) return
    if (phase !== 'active' && phase !== 'feedback') return

    expiryHandledRef.current = true
    if (phase === 'active' && answerRef.current.trim()) {
      void submitAnswer(answerRef.current)
    } else {
      void finalize(sessionId)
    }
  }, [remainingSeconds, phase, sessionId, submitAnswer, finalize])

  // ---------------------------------------------------------------- actions

  const handleStart = async () => {
    if (!topicId) return
    setBusy(true)
    setError(null)
    dispatch(interviewStarting({ topicId }))
    try {
      const response = await interviewAPI.startInterview(topicId, config)
      expiryHandledRef.current = false
      dispatch(interviewSessionLoaded({ topicId, session: response }))
      trackEvent('interview_started')
    } catch (err) {
      setError(interviewAPI.interviewErrorMessage(err, 'Failed to start the interview'))
      dispatch(interviewReset({ topicId }))
    } finally {
      setBusy(false)
    }
  }

  const handleResume = async () => {
    if (!topicId || !resumableSessionId) return
    setBusy(true)
    setError(null)
    try {
      const state = await interviewAPI.getInterview(topicId, resumableSessionId)
      if (state.isComplete && state.report) {
        // The deadline passed while the user was away - straight to the report (spec section 5).
        goToReport(state.report, state.sessionId)
        return
      }
      expiryHandledRef.current = false
      dispatch(interviewSessionLoaded({ topicId, session: state }))
    } catch (err) {
      setError(interviewAPI.interviewErrorMessage(err, 'Failed to resume the interview'))
    } finally {
      setBusy(false)
    }
  }

  const handleEndEarly = async () => {
    if (!sessionId) return
    setConfirmingEnd(false)
    expiryHandledRef.current = true
    await finalize(sessionId)
  }

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter' && answer.trim() && !busy) {
      event.preventDefault()
      void submitAnswer(answer)
    }
  }

  const elapsedFraction = useMemo(() => {
    if (remainingSeconds === null || !session?.config) return 0
    const total = session.config.durationMinutes * 60
    return Math.min(1, Math.max(0, (total - remainingSeconds) / total))
  }, [remainingSeconds, session?.config])

  // ---------------------------------------------------------------- render: setup

  if (!session) {
    return (
      <div className="min-h-screen">
        <AppHeader />
        <TopicHeader topicId={topicId} active="interview" />
        <PageContainer maxWidth={WIDTH.topic} className="flex flex-col gap-6">
          <div>
            <h2 className="type-section text-lg">Choose your interview setup</h2>
            <p className="type-body mt-1 max-w-2xl text-graphite">
              {profileIsStudent
                ? 'One question at a time, on a clock that does not pause. Questions are pitched for college students, so you only pick how long it runs.'
                : 'One question at a time, on a clock that does not pause. The bar for a strong answer follows the experience level you pick.'}
              {pastInterviewCount > 0 && (
                <>
                  {' '}
                  <Link
                    to={`/topics/${topicId}/interviews/history`}
                    className="text-ink underline decoration-edge underline-offset-4 hover:decoration-ink"
                  >
                    {pastInterviewCount} past {pastInterviewCount === 1 ? 'interview' : 'interviews'}
                  </Link>
                </>
              )}
            </p>
          </div>

          {error && <Notice>{error}</Notice>}

          {resumableSessionId && (
            <div className="flex flex-col gap-3 rounded-lg border border-ink bg-sheet p-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-medium text-ink">You have an interview in progress</p>
                <p className="type-body mt-0.5 text-graphite">Its clock has kept running. Pick up where you left off.</p>
              </div>
              <Button variant="primary" onClick={handleResume} disabled={busy}>
                {busy ? <Spinner size={14} className="text-action-ink" /> : <ArrowRight size={16} aria-hidden />}
                Resume interview
              </Button>
            </div>
          )}

          <fieldset disabled={busy} className="divide-y divide-rule rounded-lg border border-line bg-sheet">
            <SetupRow
              title="Experience level"
              note={
                profileIsStudent
                  ? 'Set from your profile: college student. Change it in Profile.'
                  : 'How much depth an answer needs to count as strong.'
              }
            >
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {EXPERIENCE_LEVELS.map((level) => (
                  <Choice
                    key={level.value}
                    selected={config.experienceLevel === level.value}
                    disabled={profileIsStudent}
                    onClick={() =>
                      setConfig((current) => ({
                        ...current,
                        experienceLevel: level.value,
                        difficulty: level.value === 'STUDENT' ? 'EASY' : current.difficulty,
                      }))
                    }
                    label={level.label}
                    hint={level.years}
                  />
                ))}
              </div>
            </SetupRow>

            <SetupRow
              title="Difficulty"
              note={
                isStudent
                  ? 'Set for students: mostly easy questions, about one in five at medium.'
                  : 'The starting complexity, and how fast follow-ups escalate.'
              }
            >
              <div className="grid grid-cols-3 gap-2">
                {DIFFICULTIES.map((option) => (
                  <Choice
                    key={option.value}
                    selected={config.difficulty === option.value}
                    disabled={isStudent}
                    onClick={() => setConfig((current) => ({ ...current, difficulty: option.value }))}
                    label={option.label}
                    hint={option.hint}
                  />
                ))}
              </div>
            </SetupRow>

            <SetupRow title="Duration" note="A fixed window on the wall clock. It keeps running if you leave.">
              <div className="grid grid-cols-3 gap-2">
                {DURATIONS.map((minutes) => (
                  <Choice
                    key={minutes}
                    selected={config.durationMinutes === minutes}
                    onClick={() => setConfig((current) => ({ ...current, durationMinutes: minutes }))}
                    label={`${minutes} min`}
                  />
                ))}
              </div>
            </SetupRow>
          </fieldset>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="figures type-body text-graphite">{configLabel(config)}. Pass mark {INTERVIEW_PASS} of {INTERVIEW_MAX}.</p>
            <Button variant="primary" size="lg" onClick={handleStart} disabled={busy || checkingForResume}>
              {busy && <Spinner size={14} className="text-action-ink" />}
              {busy ? 'Preparing your interview…' : resumableSessionId ? 'Start a new interview' : 'Start interview'}
            </Button>
          </div>
        </PageContainer>
      </div>
    )
  }

  // ---------------------------------------------------------------- render: preparing / finalizing

  if (phase === 'starting' || phase === 'ending' || phase === 'completed') {
    return (
      <div className="min-h-screen">
        <AppHeader />
        <TopicHeader topicId={topicId} active="interview" />
        <PageContainer maxWidth={WIDTH.topic}>
          <div className="rounded-lg border border-line bg-sheet px-5 py-6">
            <p className="flex items-center gap-2.5 text-sm font-medium text-ink">
              <Spinner />
              {phase === 'starting'
                ? 'Planning your interview and writing the first question…'
                : 'Scoring your answers and writing your report…'}
            </p>
            <p className="type-body mt-1 pl-[26px] text-graphite">This usually takes a few seconds.</p>
            {error && <Notice className="mt-4">{error}</Notice>}
          </div>
        </PageContainer>
      </div>
    )
  }

  const question = session.currentQuestion
  const isLowTime = remainingSeconds !== null && remainingSeconds <= 60
  const words = countWords(answer)
  const themeProgress = session.themeProgress

  return (
    <div className="min-h-screen">
      <AppHeader />

      {/* The clock is the one thing that must always be visible */}
      <div className="sticky top-[53px] z-20 border-b border-line bg-paper">
        <div className={`mx-auto flex w-full ${WIDTH.topic} items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8`}>
          <div className="min-w-0">
            <h1 className="truncate text-sm font-medium text-ink">
              Mock interview{topicName && <span className="font-normal text-graphite"> · {topicName}</span>}
            </h1>
            <p className="type-meta truncate">
              {session.config ? configLabel(session.config) : null}
              {themeProgress && themeProgress.totalThemes > 0 && (
                <>
                  {session.config ? ' · ' : ''}Theme {themeProgress.currentThemeIndex} of about {themeProgress.totalThemes}
                </>
              )}
            </p>
          </div>

          <div className="flex shrink-0 items-center gap-3">
            <p
              aria-label="Time left"
              className={`figures text-2xl font-semibold tracking-[-0.01em] ${isLowTime ? 'text-redpen' : 'text-ink'}`}
            >
              {remainingSeconds !== null ? formatCountdown(remainingSeconds) : '–:––'}
            </p>
            {confirmingEnd ? (
              <span className="flex items-center gap-1.5">
                <span className="hidden text-[13px] text-graphite sm:inline">End and get your report?</span>
                <Button size="sm" variant="danger" onClick={handleEndEarly}>
                  Yes, end it
                </Button>
                <Button size="sm" variant="quiet" onClick={() => setConfirmingEnd(false)}>
                  Cancel
                </Button>
              </span>
            ) : (
              <Button size="sm" onClick={() => setConfirmingEnd(true)} disabled={busy}>
                <Flag size={14} aria-hidden />
                End interview
              </Button>
            )}
          </div>
        </div>
        <div className="h-0.5 w-full bg-rule" aria-hidden>
          <div
            className={`h-full origin-left transition-transform duration-1000 ease-linear ${isLowTime ? 'bg-redpen' : 'bg-ballpoint'}`}
            style={{ transform: `scaleX(${elapsedFraction})` }}
          />
        </div>
      </div>

      <PageContainer mask maxWidth={WIDTH.topic} className="flex flex-col gap-5">
        {error && <Notice>{error}</Notice>}

        {/* Feedback on the answer just submitted */}
        {phase === 'feedback' && session.pendingFeedback && (
          <section className="rounded-lg border border-line bg-sheet p-5">
            <div className="flex items-center justify-between gap-3">
              <h2 className="type-section">Feedback on your answer</h2>
              <RatingBadge rating={session.pendingFeedback.rating} />
            </div>
            <p className="type-body mt-2 max-w-[68ch] text-ink">{session.pendingFeedback.feedback}</p>
            <Button
              variant="primary"
              className="mt-4"
              onClick={() => dispatch(advanceToNextQuestion({ topicId }))}
              disabled={!session.pendingQuestion}
            >
              Next question
              <ArrowRight size={16} aria-hidden />
            </Button>
          </section>
        )}

        {phase === 'evaluating' && (
          <div className="flex items-center gap-2.5 rounded-lg border border-line bg-sheet px-5 py-4">
            <Spinner />
            <p className="text-sm text-ink">Reading your answer and preparing the next question…</p>
          </div>
        )}

        {/* Current question and the answer box */}
        {phase === 'active' && question && (
          <section className="flex flex-col gap-4">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="type-label">{question.theme}</span>
                {question.isFollowUp && <StatusPill tone="accent">Follow-up</StatusPill>}
              </div>
              <p className="type-question mt-2 max-w-[60ch] text-[22px] leading-[1.45] text-ink" data-testid="interview-question">
                {question.question}
              </p>
            </div>

            <div>
              <label htmlFor="interview-answer" className="sr-only">
                Your answer
              </label>
              <textarea
                id="interview-answer"
                ref={textareaRef}
                autoFocus
                className={`${textareaClass} min-h-48 resize-y text-[15px] sm:text-[15px]`}
                placeholder="Answer as you would out loud in a real interview…"
                value={answer}
                onChange={(event) => setAnswer(event.target.value)}
                onKeyDown={handleKeyDown}
                disabled={busy}
              />
              <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                <span className="figures type-meta">
                  {words} {words === 1 ? 'word' : 'words'}
                  <span className="hidden sm:inline"> · ⌘ or Ctrl + Enter to submit</span>
                </span>
                <Button variant="primary" size="lg" onClick={() => void submitAnswer(answer)} disabled={busy || !answer.trim()}>
                  {busy && <Spinner size={14} className="text-action-ink" />}
                  Submit answer
                </Button>
              </div>
            </div>
          </section>
        )}

        {/* Everything answered so far */}
        {session.exchanges.length > 0 && (
          <section className="rounded-lg border border-line bg-sheet">
            <button
              type="button"
              onClick={() => setTranscriptOpen((open) => !open)}
              aria-expanded={transcriptOpen}
              className="flex w-full items-center justify-between gap-3 px-5 py-3.5 text-left"
            >
              <span className="flex items-baseline gap-2">
                <span className="text-sm font-medium text-ink">Transcript</span>
                <span className="figures type-meta">{session.exchanges.length} answered</span>
              </span>
              <ChevronDown
                size={16}
                aria-hidden
                className={`shrink-0 text-graphite transition-transform duration-150 ${transcriptOpen ? 'rotate-180' : ''}`}
              />
            </button>
            {transcriptOpen && (
              <ol className="divide-y divide-rule border-t border-line">
                {session.exchanges.map((exchange) => (
                  <li key={exchange.index} className="px-5 py-4">
                    <div className="flex items-start justify-between gap-3">
                      <p className="type-label">
                        {exchange.theme}
                        {exchange.isFollowUp && ' · follow-up'}
                      </p>
                      <RatingBadge rating={exchange.rating} />
                    </div>
                    <p className="type-question mt-1.5 text-base text-ink">{exchange.question}</p>
                    <p className="type-body mt-2 whitespace-pre-wrap text-graphite">
                      {exchange.userAnswer || 'No answer given.'}
                    </p>
                    {exchange.feedback && (
                      <p className="type-body mt-2 border-l-2 border-edge pl-3 text-ink">{exchange.feedback}</p>
                    )}
                  </li>
                ))}
              </ol>
            )}
          </section>
        )}
      </PageContainer>
    </div>
  )
}

function SetupRow({ title, note, children }: { title: string; note: string; children: React.ReactNode }) {
  return (
    <div role="group" aria-label={title} className="grid gap-3 p-5 md:grid-cols-[220px_minmax(0,1fr)] md:gap-8">
      <div>
        <h3 className="text-sm font-medium text-ink">{title}</h3>
        <p className="type-meta mt-0.5 text-pretty">{note}</p>
      </div>
      {children}
    </div>
  )
}

/** One option in a setup group. Selection is an ink outline; disabled options stay readable. */
function Choice({
  selected,
  disabled = false,
  onClick,
  label,
  hint,
}: {
  selected: boolean
  disabled?: boolean
  onClick: () => void
  label: string
  hint?: string
}) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      disabled={disabled}
      onClick={onClick}
      className={`rounded-md border px-3 py-2.5 text-left transition-[border-color,background-color,transform] duration-150 active:scale-[0.98] disabled:cursor-not-allowed ${
        selected
          ? 'border-ink bg-sheet ring-1 ring-ink'
          : 'border-line bg-sheet hover:border-edge hover:bg-wash disabled:text-graphite disabled:hover:border-line disabled:hover:bg-sheet'
      }`}
    >
      <span className={`block text-sm font-medium ${selected ? 'text-ink' : disabled ? 'text-graphite' : 'text-ink'}`}>{label}</span>
      {hint && <span className="type-meta block">{hint}</span>}
    </button>
  )
}

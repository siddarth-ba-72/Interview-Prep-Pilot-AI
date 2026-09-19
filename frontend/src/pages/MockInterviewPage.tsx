import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ArrowRight,
  ChevronDown,
  Clock,
  CornerDownLeft,
  Flag,
  History,
  Loader2,
  MessageSquareText,
  Sparkles,
} from 'lucide-react'
import { useAppDispatch, useAppSelector } from '../hooks'
import type { RootState } from '../store'
import AppHeader from '../components/AppHeader'
import PageContainer from '../components/PageContainer'
import RatingBadge from '../components/RatingBadge'
import * as interviewAPI from '../api/interviews'
import type { Difficulty, ExperienceLevel, InterviewConfig } from '../api/interviews'
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

const EXPERIENCE_LEVELS: Array<{ value: ExperienceLevel; label: string; years: string }> = [
  { value: 'JUNIOR', label: 'Junior', years: '0-2 years' },
  { value: 'INTERMEDIATE', label: 'Intermediate', years: '2-5 years' },
  { value: 'SENIOR', label: 'Senior', years: '5-8 years' },
  { value: 'MASTER', label: 'Master', years: '8-13 years' },
  { value: 'ADVANCED', label: 'Advanced', years: '13+ years' },
]

const DIFFICULTIES: Array<{ value: Difficulty; label: string; hint: string }> = [
  { value: 'EASY', label: 'Easy', hint: 'Warm-up pace' },
  { value: 'MEDIUM', label: 'Medium', hint: 'Realistic bar' },
  { value: 'HARD', label: 'Hard', hint: 'Pushes hard' },
]

const DURATIONS = [30, 45, 60]

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

  const [config, setConfig] = useState<InterviewConfig>({
    experienceLevel: 'INTERMEDIATE',
    difficulty: 'MEDIUM',
    durationMinutes: 30,
  })
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
      <div className="min-h-screen bg-bg text-fg">
        <AppHeader
          onBack={() => navigate('/dashboard')}
          title="Mock Interview"
          subtitle="Setup"
          actions={
            <button
              onClick={() => navigate(`/topics/${topicId}/interviews/history`)}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border px-3 text-sm font-semibold text-muted transition-colors hover:bg-surface-hover hover:text-fg"
            >
              <History size={15} />
              <span className="hidden sm:inline">
                Past interviews{pastInterviewCount > 0 ? ` (${pastInterviewCount})` : ''}
              </span>
            </button>
          }
        />
        <PageContainer maxWidth="max-w-3xl">
          <div className="flex flex-col gap-6">
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Choose your interview setup</h1>
              <p className="mt-1 text-sm text-muted">
                One question at a time, on a hard clock. The bar for a strong answer is calibrated to the
                experience level you pick.
              </p>
            </div>

            {error && (
              <div className="rounded-xl border border-danger/30 bg-danger-subtle px-4 py-3 text-sm font-medium text-danger-fg">
                {error}
              </div>
            )}

            {resumableSessionId && (
              <div className="flex flex-col gap-3 rounded-2xl border border-primary/30 bg-primary-subtle p-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-bold text-fg">You have an interview in progress</p>
                  <p className="mt-0.5 text-sm text-muted">
                    Its clock has been running the whole time. Pick up where you left off.
                  </p>
                </div>
                <button
                  onClick={handleResume}
                  disabled={busy}
                  className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-fg transition-colors hover:bg-primary-hover disabled:opacity-60"
                >
                  {busy ? <Loader2 size={16} className="animate-spin" /> : <ArrowRight size={16} />}
                  Resume interview
                </button>
              </div>
            )}

            <fieldset disabled={busy} className="flex flex-col gap-6">
              <div>
                <legend className="text-sm font-bold text-fg">Experience level</legend>
                <p className="mb-3 text-xs text-muted">Sets how much depth an answer needs to count as strong.</p>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
                  {EXPERIENCE_LEVELS.map((level) => {
                    const selected = config.experienceLevel === level.value
                    return (
                      <button
                        key={level.value}
                        type="button"
                        onClick={() => setConfig((current) => ({ ...current, experienceLevel: level.value }))}
                        className={`rounded-xl border p-3 text-left transition-colors ${
                          selected
                            ? 'border-primary bg-primary-subtle'
                            : 'border-border bg-surface hover:bg-surface-hover'
                        }`}
                      >
                        <span className="block text-sm font-bold text-fg">{level.label}</span>
                        <span className="mt-0.5 block text-xs text-muted">{level.years}</span>
                      </button>
                    )
                  })}
                </div>
              </div>

              <div className="grid gap-6 sm:grid-cols-2">
                <div>
                  <legend className="text-sm font-bold text-fg">Difficulty</legend>
                  <p className="mb-3 text-xs text-muted">Baseline complexity and how fast follow-ups escalate.</p>
                  <div className="grid grid-cols-3 gap-2">
                    {DIFFICULTIES.map((option) => {
                      const selected = config.difficulty === option.value
                      return (
                        <button
                          key={option.value}
                          type="button"
                          onClick={() => setConfig((current) => ({ ...current, difficulty: option.value }))}
                          className={`rounded-xl border p-3 text-left transition-colors ${
                            selected
                              ? 'border-primary bg-primary-subtle'
                              : 'border-border bg-surface hover:bg-surface-hover'
                          }`}
                        >
                          <span className="block text-sm font-bold text-fg">{option.label}</span>
                          <span className="mt-0.5 block text-xs text-muted">{option.hint}</span>
                        </button>
                      )
                    })}
                  </div>
                </div>

                <div>
                  <legend className="text-sm font-bold text-fg">Duration</legend>
                  <p className="mb-3 text-xs text-muted">A hard wall-clock window. The clock does not pause.</p>
                  <div className="grid grid-cols-3 gap-2">
                    {DURATIONS.map((minutes) => {
                      const selected = config.durationMinutes === minutes
                      return (
                        <button
                          key={minutes}
                          type="button"
                          onClick={() => setConfig((current) => ({ ...current, durationMinutes: minutes }))}
                          className={`rounded-xl border p-3 text-center transition-colors ${
                            selected
                              ? 'border-primary bg-primary-subtle'
                              : 'border-border bg-surface hover:bg-surface-hover'
                          }`}
                        >
                          <span className="block text-sm font-bold text-fg">{minutes}</span>
                          <span className="mt-0.5 block text-xs text-muted">minutes</span>
                        </button>
                      )
                    })}
                  </div>
                </div>
              </div>
            </fieldset>

            <button
              onClick={handleStart}
              disabled={busy || checkingForResume}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-bold text-primary-fg transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60"
            >
              {busy ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
              {busy ? 'Preparing your interview…' : resumableSessionId ? 'Start a new interview' : 'Start interview'}
            </button>
          </div>
        </PageContainer>
      </div>
    )
  }

  // ---------------------------------------------------------------- render: preparing / finalizing

  if (phase === 'starting' || phase === 'ending' || phase === 'completed') {
    const message =
      phase === 'starting'
        ? 'Planning your interview and writing the first question…'
        : 'Scoring your answers and writing your report…'
    return (
      <div className="min-h-screen bg-bg text-fg">
        <AppHeader title="Mock Interview" subtitle={phase === 'starting' ? 'Preparing' : 'Wrapping up'} />
        <PageContainer maxWidth="max-w-3xl">
          <div className="flex flex-col items-center gap-4 rounded-2xl border border-border bg-surface p-12 text-center">
            <Loader2 size={28} className="animate-spin text-primary" />
            <p className="text-sm font-semibold text-fg">{message}</p>
            <p className="text-xs text-muted">This usually takes a few seconds.</p>
            {error && <p className="text-sm font-medium text-danger-fg">{error}</p>}
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
    <div className="min-h-screen bg-bg text-fg">
      <AppHeader
        onBack={() => navigate('/dashboard')}
        title="Mock Interview"
        subtitle={session.config ? `${session.config.experienceLevel} · ${session.config.difficulty}` : undefined}
      />

      {/* Timer bar - the one thing that must always be visible */}
      <div className="sticky top-16 z-10 border-b border-border bg-surface/85 backdrop-blur-md">
        <div className="mx-auto flex w-full max-w-3xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <span
              className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 font-mono text-sm font-bold tabular-nums ${
                isLowTime ? 'bg-danger-subtle text-danger-fg' : 'bg-surface-hover text-fg'
              }`}
            >
              <Clock size={14} />
              {remainingSeconds !== null ? formatCountdown(remainingSeconds) : '--:--'}
            </span>
            {themeProgress && themeProgress.totalThemes > 0 && (
              <span className="truncate text-xs font-medium text-muted">
                Theme {themeProgress.currentThemeIndex} of ~{themeProgress.totalThemes}
              </span>
            )}
          </div>

          <div className="flex shrink-0 items-center gap-2">
            {confirmingEnd ? (
              <>
                <span className="hidden text-xs font-medium text-muted sm:inline">End and get your report?</span>
                <button
                  onClick={handleEndEarly}
                  className="rounded-lg bg-danger px-3 py-1.5 text-xs font-bold text-white transition-opacity hover:opacity-90"
                >
                  Yes, end it
                </button>
                <button
                  onClick={() => setConfirmingEnd(false)}
                  className="rounded-lg border border-border px-3 py-1.5 text-xs font-semibold text-muted transition-colors hover:bg-surface-hover"
                >
                  Cancel
                </button>
              </>
            ) : (
              <button
                onClick={() => setConfirmingEnd(true)}
                disabled={busy}
                className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs font-semibold text-muted transition-colors hover:bg-surface-hover hover:text-fg disabled:opacity-50"
              >
                <Flag size={13} />
                End interview
              </button>
            )}
          </div>
        </div>
        <div className="h-0.5 w-full bg-border">
          <div
            className={`h-full transition-all duration-1000 ease-linear ${isLowTime ? 'bg-danger' : 'bg-primary'}`}
            style={{ width: `${elapsedFraction * 100}%` }}
          />
        </div>
      </div>

      <PageContainer maxWidth="max-w-3xl">
        <div className="flex flex-col gap-4">
          {error && (
            <div className="rounded-xl border border-danger/30 bg-danger-subtle px-4 py-3 text-sm font-medium text-danger-fg">
              {error}
            </div>
          )}

          {/* Transcript of everything answered so far */}
          {session.exchanges.length > 0 && (
            <div className="rounded-2xl border border-border bg-surface">
              <button
                onClick={() => setTranscriptOpen((open) => !open)}
                className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
              >
                <span className="inline-flex items-center gap-2 text-sm font-bold text-fg">
                  <MessageSquareText size={15} className="text-muted" />
                  Transcript
                  <span className="rounded-full bg-surface-hover px-2 py-0.5 text-xs font-semibold text-muted">
                    {session.exchanges.length} answered
                  </span>
                </span>
                <ChevronDown
                  size={16}
                  className={`shrink-0 text-muted transition-transform ${transcriptOpen ? 'rotate-180' : ''}`}
                />
              </button>
              {transcriptOpen && (
                <div className="flex flex-col gap-3 border-t border-border p-4">
                  {session.exchanges.map((exchange) => (
                    <div key={exchange.index} className="rounded-xl border border-border p-3">
                      <div className="flex items-start justify-between gap-3">
                        <p className="text-[11px] font-bold uppercase tracking-wide text-muted">{exchange.theme}</p>
                        <RatingBadge rating={exchange.rating} size="sm" />
                      </div>
                      <p className="mt-1.5 text-sm font-semibold text-fg">{exchange.question}</p>
                      <p className="mt-1.5 whitespace-pre-wrap text-sm text-muted">
                        {exchange.userAnswer || '(no answer given)'}
                      </p>
                      {exchange.feedback && (
                        <p className="mt-2 border-t border-border pt-2 text-sm italic text-muted">{exchange.feedback}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Feedback on the answer just submitted */}
          {phase === 'feedback' && session.pendingFeedback && (
            <div className="rounded-2xl border border-border bg-surface p-5">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-sm font-bold text-fg">Feedback on your answer</h2>
                <RatingBadge rating={session.pendingFeedback.rating} />
              </div>
              <p className="mt-2 text-sm leading-relaxed text-muted">{session.pendingFeedback.feedback}</p>
              <button
                onClick={() => dispatch(advanceToNextQuestion({ topicId }))}
                disabled={!session.pendingQuestion}
                className="mt-4 inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-bold text-primary-fg transition-colors hover:bg-primary-hover disabled:opacity-60"
              >
                Next question
                <ArrowRight size={16} />
              </button>
            </div>
          )}

          {phase === 'evaluating' && (
            <div className="flex items-center gap-3 rounded-2xl border border-border bg-surface p-5">
              <Loader2 size={18} className="animate-spin text-primary" />
              <p className="text-sm font-semibold text-fg">Reading your answer and preparing the next question…</p>
            </div>
          )}

          {/* Current question + answer box */}
          {phase === 'active' && question && (
            <>
              <div className="rounded-2xl border border-border bg-surface p-5 shadow-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-full bg-surface-hover px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide text-muted">
                    {question.theme}
                  </span>
                  {question.isFollowUp && (
                    <span className="rounded-full border border-accent/30 bg-primary-subtle px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide text-fg">
                      Follow-up
                    </span>
                  )}
                </div>
                <p className="mt-3 text-lg font-semibold leading-relaxed text-fg">{question.question}</p>
              </div>

              <div className="rounded-2xl border border-border bg-surface p-4">
                <textarea
                  ref={textareaRef}
                  autoFocus
                  className="min-h-40 w-full resize-y rounded-xl border border-border bg-bg px-3 py-2.5 text-sm leading-relaxed text-fg outline-none transition-colors placeholder:text-muted focus:border-primary"
                  placeholder="Answer as you would out loud in a real interview…"
                  value={answer}
                  onChange={(event) => setAnswer(event.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={busy}
                />
                <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                  <span className="text-xs text-muted">
                    {words} word{words === 1 ? '' : 's'}
                    <span className="ml-2 hidden items-center gap-1 sm:inline-flex">
                      · <CornerDownLeft size={11} /> Cmd/Ctrl + Enter to submit
                    </span>
                  </span>
                  <button
                    onClick={() => void submitAnswer(answer)}
                    disabled={busy || !answer.trim()}
                    className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-bold text-primary-fg transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {busy && <Loader2 size={15} className="animate-spin" />}
                    Submit answer
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </PageContainer>
    </div>
  )
}

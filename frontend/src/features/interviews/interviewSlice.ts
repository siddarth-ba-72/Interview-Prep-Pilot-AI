import { createSlice, type PayloadAction } from '@reduxjs/toolkit'
import type {
  InterviewConfig,
  InterviewEvaluation,
  InterviewExchange,
  InterviewQuestion,
  InterviewReportResponse,
  InterviewStartResponse,
  InterviewStateResponse,
  ThemeProgress,
} from '../../api/interviews'

/**
 * Mirrors the Phase 4 interview flow:
 *   starting -> active -> evaluating -> feedback -> active -> ... -> ending -> completed
 */
export type InterviewPhase =
  | 'starting'
  | 'active'
  | 'evaluating'
  | 'feedback'
  | 'ending'
  | 'completed'

export interface InterviewSessionState {
  sessionId: string | null
  phase: InterviewPhase
  config: InterviewConfig | null
  deadlineAt: string | null
  currentQuestion: InterviewQuestion | null
  /** Held back while feedback is on screen, then promoted by `advanceToNextQuestion`. */
  pendingQuestion: InterviewQuestion | null
  themeProgress: ThemeProgress | null
  exchanges: InterviewExchange[]
  pendingFeedback: InterviewEvaluation | null
  completionReason: string | null
  resumed: boolean
}

interface InterviewsState {
  activeSessionByTopicId: { [topicId: string]: InterviewSessionState }
  reportsBySessionId: { [sessionId: string]: InterviewReportResponse }
}

const initialState: InterviewsState = {
  activeSessionByTopicId: {},
  reportsBySessionId: {},
}

function emptySession(phase: InterviewPhase): InterviewSessionState {
  return {
    sessionId: null,
    phase,
    config: null,
    deadlineAt: null,
    currentQuestion: null,
    pendingQuestion: null,
    themeProgress: null,
    exchanges: [],
    pendingFeedback: null,
    completionReason: null,
    resumed: false,
  }
}

const interviewSlice = createSlice({
  name: 'interviews',
  initialState,
  reducers: {
    interviewStarting: (state, action: PayloadAction<{ topicId: string }>) => {
      state.activeSessionByTopicId[action.payload.topicId] = emptySession('starting')
    },

    /** Seeds the session from a start or resume response. */
    interviewSessionLoaded: (
      state,
      action: PayloadAction<{ topicId: string; session: InterviewStartResponse | InterviewStateResponse }>,
    ) => {
      const { topicId, session } = action.payload
      const isComplete = 'isComplete' in session ? session.isComplete : session.status === 'COMPLETED'
      state.activeSessionByTopicId[topicId] = {
        sessionId: session.sessionId,
        phase: isComplete ? 'completed' : 'active',
        config: session.config,
        deadlineAt: session.deadlineAt,
        currentQuestion: session.currentQuestion,
        pendingQuestion: null,
        themeProgress: session.themeProgress,
        exchanges: session.exchanges ?? [],
        pendingFeedback: null,
        completionReason: 'completionReason' in session ? session.completionReason : null,
        resumed: 'resumed' in session ? session.resumed : true,
      }
    },

    interviewEvaluating: (state, action: PayloadAction<{ topicId: string }>) => {
      const session = state.activeSessionByTopicId[action.payload.topicId]
      if (session) session.phase = 'evaluating'
    },

    /** An answer was graded: record the exchange, show the feedback, hold the next question. */
    interviewTurnCompleted: (
      state,
      action: PayloadAction<{
        topicId: string
        evaluation: InterviewEvaluation | null
        exchange: InterviewExchange | null
        nextQuestion: InterviewQuestion | null
        themeProgress: ThemeProgress | null
      }>,
    ) => {
      const { topicId, evaluation, exchange, nextQuestion, themeProgress } = action.payload
      const session = state.activeSessionByTopicId[topicId]
      if (!session) return
      if (exchange) session.exchanges.push(exchange)
      session.pendingFeedback = evaluation
      session.pendingQuestion = nextQuestion
      session.currentQuestion = null
      if (themeProgress) session.themeProgress = themeProgress
      session.phase = 'feedback'
    },

    advanceToNextQuestion: (state, action: PayloadAction<{ topicId: string }>) => {
      const session = state.activeSessionByTopicId[action.payload.topicId]
      if (!session || !session.pendingQuestion) return
      session.currentQuestion = session.pendingQuestion
      session.pendingQuestion = null
      session.pendingFeedback = null
      session.phase = 'active'
    },

    /** A turn or finalization failed - return the candidate to a usable state instead of
     * stranding them on a spinner. */
    interviewTurnFailed: (state, action: PayloadAction<{ topicId: string }>) => {
      const session = state.activeSessionByTopicId[action.payload.topicId]
      if (!session) return
      if (session.phase === 'evaluating') {
        session.phase = 'active'
      } else if (session.phase === 'ending') {
        session.phase = session.pendingQuestion ? 'feedback' : 'active'
      }
    },

    interviewEnding: (state, action: PayloadAction<{ topicId: string }>) => {
      const session = state.activeSessionByTopicId[action.payload.topicId]
      if (session) session.phase = 'ending'
    },

    interviewCompleted: (state, action: PayloadAction<{ topicId: string; report: InterviewReportResponse }>) => {
      const { topicId, report } = action.payload
      const session = state.activeSessionByTopicId[topicId]
      if (session) {
        session.phase = 'completed'
        session.currentQuestion = null
        session.pendingQuestion = null
        session.completionReason = report.completionReason
      }
      state.reportsBySessionId[report.sessionId] = report
    },

    storeInterviewReport: (state, action: PayloadAction<{ report: InterviewReportResponse }>) => {
      state.reportsBySessionId[action.payload.report.sessionId] = action.payload.report
    },

    /** Clears the session so the topic shows the config screen again. */
    interviewReset: (state, action: PayloadAction<{ topicId: string }>) => {
      delete state.activeSessionByTopicId[action.payload.topicId]
    },
  },
})

export const {
  interviewStarting,
  interviewSessionLoaded,
  interviewEvaluating,
  interviewTurnCompleted,
  advanceToNextQuestion,
  interviewTurnFailed,
  interviewEnding,
  interviewCompleted,
  storeInterviewReport,
  interviewReset,
} = interviewSlice.actions

export default interviewSlice.reducer

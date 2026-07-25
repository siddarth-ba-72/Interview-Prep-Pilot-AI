import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import { TestQuestion, TestReportResponse } from '../../api/tests'

interface TestSessionState {
  sessionId: string | null
  status: 'idle' | 'generating' | 'in_progress' | 'submitting' | 'completed'
  questions: TestQuestion[]
  answers: { [questionId: string]: string | null }
}

interface TestsState {
  activeSessionByTopicId: { [topicId: string]: TestSessionState }
  reportsBySessionId: { [sessionId: string]: TestReportResponse }
  resultsModal: {
    open: boolean
    sessionId: string | null
  }
}

const initialState: TestsState = {
  activeSessionByTopicId: {},
  reportsBySessionId: {},
  resultsModal: {
    open: false,
    sessionId: null,
  },
}

const testSlice = createSlice({
  name: 'tests',
  initialState,
  reducers: {
    setTestGenerating: (state, action: PayloadAction<{ topicId: string }>) => {
      const { topicId } = action.payload
      if (!state.activeSessionByTopicId[topicId]) {
        state.activeSessionByTopicId[topicId] = {
          sessionId: null,
          status: 'generating',
          questions: [],
          answers: {},
        }
      } else {
        state.activeSessionByTopicId[topicId].status = 'generating'
      }
    },

    setTestSession: (state, action: PayloadAction<{
      topicId: string
      sessionId: string
      questions: TestQuestion[]
    }>) => {
      const { topicId, sessionId, questions } = action.payload
      state.activeSessionByTopicId[topicId] = {
        sessionId,
        status: 'in_progress',
        questions,
        answers: {},
      }
    },

    updateAnswer: (state, action: PayloadAction<{
      topicId: string
      questionId: string
      answer: string | null
    }>) => {
      const { topicId, questionId, answer } = action.payload
      if (state.activeSessionByTopicId[topicId]) {
        state.activeSessionByTopicId[topicId].answers[questionId] = answer
      }
    },

    setTestSubmitting: (state, action: PayloadAction<{ topicId: string }>) => {
      const { topicId } = action.payload
      if (state.activeSessionByTopicId[topicId]) {
        state.activeSessionByTopicId[topicId].status = 'submitting'
      }
    },

    setTestCompleted: (state, action: PayloadAction<{
      topicId: string
      report: TestReportResponse
    }>) => {
      const { topicId, report } = action.payload
      if (state.activeSessionByTopicId[topicId]) {
        state.activeSessionByTopicId[topicId].status = 'completed'
      }
      state.reportsBySessionId[report.testSessionId] = report
    },

    openResultsModal: (state, action: PayloadAction<{ sessionId: string }>) => {
      const { sessionId } = action.payload
      state.resultsModal.open = true
      state.resultsModal.sessionId = sessionId
    },

    closeResultsModal: (state) => {
      state.resultsModal.open = false
      state.resultsModal.sessionId = null
    },

    storeReport: (state, action: PayloadAction<{ report: TestReportResponse }>) => {
      const { report } = action.payload
      state.reportsBySessionId[report.testSessionId] = report
    },

    clearTestSession: (state, action: PayloadAction<{ topicId: string }>) => {
      const { topicId } = action.payload
      delete state.activeSessionByTopicId[topicId]
    },
  },
})

export const {
  setTestGenerating,
  setTestSession,
  updateAnswer,
  setTestSubmitting,
  setTestCompleted,
  openResultsModal,
  closeResultsModal,
  storeReport,
  clearTestSession,
} = testSlice.actions

export default testSlice.reducer

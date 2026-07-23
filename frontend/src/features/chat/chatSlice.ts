import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import type { ChatMessage } from '../../api/chat'

export type ChatStatus = 'loading' | 'idle' | 'streaming' | 'error'

interface ChatSessionState {
  messages: ChatMessage[]
  streamingContent: string
  status: ChatStatus
  error: string | null
}

interface ChatState {
  sessionsByTopicId: Record<string, ChatSessionState>
}

const initialState: ChatState = {
  sessionsByTopicId: {},
}

function ensureSession(state: ChatState, topicId: string): ChatSessionState {
  if (!state.sessionsByTopicId[topicId]) {
    state.sessionsByTopicId[topicId] = { messages: [], streamingContent: '', status: 'loading', error: null }
  }
  return state.sessionsByTopicId[topicId]
}

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    sessionLoading(state, action: PayloadAction<{ topicId: string }>) {
      const session = ensureSession(state, action.payload.topicId)
      session.status = 'loading'
      session.error = null
    },
    sessionLoaded(state, action: PayloadAction<{ topicId: string; messages: ChatMessage[] }>) {
      const session = ensureSession(state, action.payload.topicId)
      session.messages = action.payload.messages
      session.streamingContent = ''
      session.status = 'idle'
      session.error = null
    },
    sessionLoadFailed(state, action: PayloadAction<{ topicId: string; error: string }>) {
      const session = ensureSession(state, action.payload.topicId)
      session.status = 'error'
      session.error = action.payload.error
    },
    userMessageAppended(state, action: PayloadAction<{ topicId: string; content: string }>) {
      const session = ensureSession(state, action.payload.topicId)
      session.messages.push({ role: 'USER', content: action.payload.content, timestamp: new Date().toISOString() })
      session.streamingContent = ''
      session.status = 'streaming'
      session.error = null
    },
    tokenReceived(state, action: PayloadAction<{ topicId: string; token: string }>) {
      const session = ensureSession(state, action.payload.topicId)
      session.streamingContent += action.payload.token
    },
    streamCompleted(state, action: PayloadAction<{ topicId: string }>) {
      const session = ensureSession(state, action.payload.topicId)
      if (session.streamingContent) {
        session.messages.push({ role: 'AI', content: session.streamingContent, timestamp: new Date().toISOString() })
      }
      session.streamingContent = ''
      session.status = 'idle'
    },
    streamErrored(state, action: PayloadAction<{ topicId: string; message: string }>) {
      const session = ensureSession(state, action.payload.topicId)
      session.streamingContent = ''
      session.status = 'error'
      session.error = action.payload.message
    },
  },
})

export const {
  sessionLoading,
  sessionLoaded,
  sessionLoadFailed,
  userMessageAppended,
  tokenReceived,
  streamCompleted,
  streamErrored,
} = chatSlice.actions
export default chatSlice.reducer

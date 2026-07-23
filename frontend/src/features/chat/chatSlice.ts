import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import type { ChatMessage } from '../../api/chat'

export type ChatStatus = 'loading' | 'idle' | 'streaming' | 'error'

interface ChatSessionState {
  messages: ChatMessage[]
  streamingContent: string
  status: ChatStatus
  error: string | null
  hasMore: boolean
  isLoadingMore: boolean
  oldestTimestamp: string | null
}

interface ChatState {
  sessionsByTopicId: Record<string, ChatSessionState>
}

const initialState: ChatState = {
  sessionsByTopicId: {},
}

function ensureSession(state: ChatState, topicId: string): ChatSessionState {
  if (!state.sessionsByTopicId[topicId]) {
    state.sessionsByTopicId[topicId] = {
      messages: [],
      streamingContent: '',
      status: 'loading',
      error: null,
      hasMore: false,
      isLoadingMore: false,
      oldestTimestamp: null,
    }
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
    sessionLoaded(state, action: PayloadAction<{ topicId: string; messages: ChatMessage[]; hasMore: boolean }>) {
      const session = ensureSession(state, action.payload.topicId)
      session.messages = action.payload.messages
      session.streamingContent = ''
      session.status = 'idle'
      session.error = null
      session.hasMore = action.payload.hasMore
      session.oldestTimestamp = action.payload.messages[0]?.timestamp ?? null
    },
    sessionLoadFailed(state, action: PayloadAction<{ topicId: string; error: string }>) {
      const session = ensureSession(state, action.payload.topicId)
      session.status = 'error'
      session.error = action.payload.error
    },
    olderMessagesLoadingStarted(state, action: PayloadAction<{ topicId: string }>) {
      const session = ensureSession(state, action.payload.topicId)
      session.isLoadingMore = true
    },
    olderMessagesLoaded(state, action: PayloadAction<{ topicId: string; messages: ChatMessage[]; hasMore: boolean }>) {
      const session = ensureSession(state, action.payload.topicId)
      session.messages = [...action.payload.messages, ...session.messages]
      session.hasMore = action.payload.hasMore
      session.isLoadingMore = false
      session.oldestTimestamp = action.payload.messages[0]?.timestamp ?? session.oldestTimestamp
    },
    olderMessagesLoadFailed(state, action: PayloadAction<{ topicId: string }>) {
      const session = ensureSession(state, action.payload.topicId)
      session.isLoadingMore = false
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
  olderMessagesLoadingStarted,
  olderMessagesLoaded,
  olderMessagesLoadFailed,
  userMessageAppended,
  tokenReceived,
  streamCompleted,
  streamErrored,
} = chatSlice.actions
export default chatSlice.reducer

import { useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useAppDispatch, useAppSelector } from '../hooks'
import { getChatSession } from '../api/chat'
import { extractErrorMessage } from '../api/topics'
import { streamChatMessage } from '../api/chatStream'
import {
  sessionLoadFailed,
  sessionLoaded,
  sessionLoading,
  streamCompleted,
  streamErrored,
  tokenReceived,
  userMessageAppended,
} from '../features/chat/chatSlice'
import ChatHistory from '../components/ChatHistory'
import MessageInput from '../components/MessageInput'

export default function LearnModePage() {
  const { topicId } = useParams<{ topicId: string }>()
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const session = useAppSelector((state) => (topicId ? state.chat.sessionsByTopicId[topicId] : undefined))

  useEffect(() => {
    if (!topicId) return
    dispatch(sessionLoading({ topicId }))
    getChatSession(topicId)
      .then((data) => dispatch(sessionLoaded({ topicId, messages: data.messages })))
      .catch((error) =>
        dispatch(sessionLoadFailed({ topicId, error: extractErrorMessage(error, 'Could not load this chat.') }))
      )
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topicId])

  async function handleSend(content: string) {
    if (!topicId) return
    dispatch(userMessageAppended({ topicId, content }))
    await streamChatMessage(topicId, content, {
      onEvent: (event) => {
        if (event.type === 'token') dispatch(tokenReceived({ topicId, token: event.token }))
        else if (event.type === 'done') dispatch(streamCompleted({ topicId }))
        else if (event.type === 'error') dispatch(streamErrored({ topicId, message: event.message }))
      },
      onFatalError: (message) => dispatch(streamErrored({ topicId, message })),
    })
  }

  if (!topicId) return null

  return (
    <div className="chat-shell">
      <header className="chat-header">
        <button className="secondary-button chat-back-button" onClick={() => navigate('/dashboard')}>
          ← Back
        </button>
        <h1>Learn Mode</h1>
      </header>

      {!session || session.status === 'loading' ? (
        <p className="muted-text">Loading chat...</p>
      ) : (
        <>
          <ChatHistory
            messages={session.messages}
            streamingContent={session.streamingContent}
            isStreaming={session.status === 'streaming'}
          />
          {session.status === 'error' && session.error && <p className="error-text">{session.error}</p>}
          <MessageInput onSend={handleSend} disabled={session.status === 'streaming'} />
        </>
      )}
    </div>
  )
}

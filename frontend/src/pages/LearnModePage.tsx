import { useCallback, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAppDispatch, useAppSelector } from '../hooks'
import { getChatSession, getOlderMessages } from '../api/chat'
import { extractErrorMessage, listTopics } from '../api/topics'
import { streamChatMessage } from '../api/chatStream'
import {
  olderMessagesLoadFailed,
  olderMessagesLoaded,
  olderMessagesLoadingStarted,
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
import AppHeader from '../components/AppHeader'

export default function LearnModePage() {
  const { topicId } = useParams<{ topicId: string }>()
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const session = useAppSelector((state) => (topicId ? state.chat.sessionsByTopicId[topicId] : undefined))
  const topicsQuery = useQuery({ queryKey: ['topics'], queryFn: listTopics, staleTime: Infinity })
  const topicName = topicsQuery.data?.find((t) => t.id === topicId)?.name

  useEffect(() => {
    if (!topicId) return
    dispatch(sessionLoading({ topicId }))
    getChatSession(topicId)
      .then((data) => dispatch(sessionLoaded({ topicId, messages: data.messages, hasMore: data.hasMore })))
      .catch((error) =>
        dispatch(sessionLoadFailed({ topicId, error: extractErrorMessage(error, 'Could not load this chat.') }))
      )
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topicId])

  const handleLoadMore = useCallback(() => {
    if (!topicId || !session?.hasMore || session.isLoadingMore || !session.oldestTimestamp) return
    dispatch(olderMessagesLoadingStarted({ topicId }))
    getOlderMessages(topicId, session.oldestTimestamp)
      .then((data) => dispatch(olderMessagesLoaded({ topicId, messages: data.messages, hasMore: data.hasMore })))
      .catch(() => dispatch(olderMessagesLoadFailed({ topicId })))
  }, [topicId, session?.hasMore, session?.isLoadingMore, session?.oldestTimestamp, dispatch])

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
    <div className="flex h-screen flex-col bg-bg">
      <AppHeader onBack={() => navigate('/dashboard')} title={topicName} subtitle="Learn Mode" />

      {!session || session.status === 'loading' ? (
        <p className="px-6 py-8 text-sm text-muted">Loading chat...</p>
      ) : (
        <div className="flex flex-1 flex-col overflow-hidden">
          <ChatHistory
            messages={session.messages}
            streamingContent={session.streamingContent}
            isStreaming={session.status === 'streaming'}
            hasMore={session.hasMore}
            isLoadingMore={session.isLoadingMore}
            onLoadMore={handleLoadMore}
          />
          {session.status === 'error' && session.error && (
            <p className="mx-auto w-full max-w-3xl px-4 text-sm font-medium text-danger sm:px-6">{session.error}</p>
          )}
          <div className="border-t border-border bg-surface px-4 py-3 sm:px-6">
            <div className="mx-auto w-full max-w-3xl">
              <MessageInput onSend={handleSend} disabled={session.status === 'streaming'} />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

import { useCallback, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useAppDispatch, useAppSelector } from '../hooks'
import { getChatSession, getOlderMessages } from '../api/chat'
import { extractErrorMessage } from '../api/topics'
import { streamChatMessage } from '../api/chatStream'
import { trackEvent } from '../features/analytics/clarity'
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
import TopicHeader from '../components/TopicHeader'
import Notice from '../components/ui/Notice'

export default function LearnModePage() {
  const { topicId } = useParams<{ topicId: string }>()
  const dispatch = useAppDispatch()
  const session = useAppSelector((state) => (topicId ? state.chat.sessionsByTopicId[topicId] : undefined))

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
        else if (event.type === 'done') {
          dispatch(streamCompleted({ topicId }))
          trackEvent('learn_message_sent')
        } else if (event.type === 'error') dispatch(streamErrored({ topicId, message: event.message }))
      },
      onFatalError: (message) => dispatch(streamErrored({ topicId, message })),
    })
  }

  if (!topicId) return null

  return (
    <div className="flex h-[calc(100dvh-49px)] flex-col">
      <AppHeader />
      <TopicHeader topicId={topicId} active="learn" />

      {!session || session.status === 'loading' ? (
        <div aria-label="Loading chat" className="mx-auto w-full max-w-4xl flex-1 px-4 py-8 sm:px-6 lg:px-8">
          <div className="flex max-w-[68ch] flex-col gap-2.5">
            <div className="h-4 w-3/4 rounded bg-press" />
            <div className="h-4 w-full rounded bg-wash" />
            <div className="h-4 w-2/3 rounded bg-wash" />
          </div>
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col">
          <ChatHistory
            messages={session.messages}
            streamingContent={session.streamingContent}
            isStreaming={session.status === 'streaming'}
            hasMore={session.hasMore}
            isLoadingMore={session.isLoadingMore}
            onLoadMore={handleLoadMore}
          />
          <div className="border-t border-line bg-paper">
            <div className="mx-auto w-full max-w-4xl px-4 pb-4 pt-3 sm:px-6 lg:px-8">
              {session.status === 'error' && session.error && (
                <Notice className="mb-3">{session.error}</Notice>
              )}
              <MessageInput onSend={handleSend} disabled={session.status === 'streaming'} />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

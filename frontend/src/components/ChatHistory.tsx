import { useEffect, useRef } from 'react'
import type { ChatMessage } from '../api/chat'
import AiMessage from './AiMessage'
import UserMessage from './UserMessage'
import StreamingMessage from './StreamingMessage'

interface ChatHistoryProps {
  messages: ChatMessage[]
  streamingContent: string
  isStreaming: boolean
  hasMore: boolean
  isLoadingMore: boolean
  onLoadMore: () => void
}

export default function ChatHistory({
  messages,
  streamingContent,
  isStreaming,
  hasMore,
  isLoadingMore,
  onLoadMore,
}: ChatHistoryProps) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const topSentinelRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const prevScrollHeightRef = useRef<number>(0)
  const isLoadingMoreRef = useRef(isLoadingMore)

  // Keep ref in sync so IntersectionObserver callback has latest value
  isLoadingMoreRef.current = isLoadingMore

  // Scroll to bottom when new messages arrive (not when loading older ones)
  const prevMessageCountRef = useRef(messages.length)
  useEffect(() => {
    const prevCount = prevMessageCountRef.current
    const newCount = messages.length
    prevMessageCountRef.current = newCount

    if (newCount > prevCount && prevScrollHeightRef.current > 0) {
      // Older messages were prepended — restore scroll position
      const container = containerRef.current
      if (container) {
        container.scrollTop = container.scrollHeight - prevScrollHeightRef.current
      }
      prevScrollHeightRef.current = 0
    } else {
      // New message at bottom — scroll down
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [streamingContent])

  // IntersectionObserver on the top sentinel
  useEffect(() => {
    const sentinel = topSentinelRef.current
    if (!sentinel) return

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !isLoadingMoreRef.current) {
          // Save scroll height before prepend
          prevScrollHeightRef.current = containerRef.current?.scrollHeight ?? 0
          onLoadMore()
        }
      },
      { threshold: 0.1 }
    )
    observer.observe(sentinel)
    return () => observer.disconnect()
  }, [onLoadMore])

  return (
    <div className="chat-history" ref={containerRef}>
      <div ref={topSentinelRef} />
      {isLoadingMore && <p className="muted-text chat-loading-more">Loading older messages...</p>}
      {!hasMore && messages.length > 0 && (
        <p className="muted-text chat-history-start">You've reached the beginning of the conversation.</p>
      )}
      {messages.map((message, index) =>
        message.role === 'AI' ? (
          <AiMessage key={index} content={message.content} />
        ) : (
          <UserMessage key={index} content={message.content} />
        )
      )}
      {isStreaming && <StreamingMessage content={streamingContent} />}
      <div ref={bottomRef} />
    </div>
  )
}

import { useEffect, useRef } from 'react'
import type { ChatMessage } from '../api/chat'
import AiMessage from './AiMessage'
import UserMessage from './UserMessage'
import StreamingMessage from './StreamingMessage'

interface ChatHistoryProps {
  messages: ChatMessage[]
  streamingContent: string
  isStreaming: boolean
}

export default function ChatHistory({ messages, streamingContent, isStreaming }: ChatHistoryProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  return (
    <div className="chat-history">
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

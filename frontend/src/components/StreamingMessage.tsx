import ReactMarkdown from 'react-markdown'

interface StreamingMessageProps {
  content: string
}

export default function StreamingMessage({ content }: StreamingMessageProps) {
  return (
    <div className="chat-message chat-message-ai">
      <div className="chat-message-bubble">
        {content ? <ReactMarkdown>{content}</ReactMarkdown> : <span className="typing-indicator">Thinking...</span>}
      </div>
    </div>
  )
}

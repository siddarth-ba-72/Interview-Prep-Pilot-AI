import ReactMarkdown from 'react-markdown'

interface AiMessageProps {
  content: string
}

export default function AiMessage({ content }: AiMessageProps) {
  return (
    <div className="chat-message chat-message-ai">
      <div className="chat-message-bubble">
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
    </div>
  )
}

import ReactMarkdown from 'react-markdown'

interface UserMessageProps {
  content: string
}

export default function UserMessage({ content }: UserMessageProps) {
  return (
    <div className="chat-message chat-message-user">
      <div className="chat-message-bubble">
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
    </div>
  )
}

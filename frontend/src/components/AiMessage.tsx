import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { PROSE } from './ui/prose'

/** The tutor's reply, set as a page of notes rather than a chat bubble. */
export default function AiMessage({ content }: { content: string }) {
  return (
    <div data-testid="chat-message-ai" data-clarity-mask="True">
      <div className={PROSE}>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
      </div>
    </div>
  )
}

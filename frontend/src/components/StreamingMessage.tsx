import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { PROSE } from './ui/prose'

/** The reply while it streams in. Until the first token arrives it says so. */
export default function StreamingMessage({ content }: { content: string }) {
  return (
    <div data-testid="chat-message-streaming" data-clarity-mask="True">
      {content ? (
        <div className={PROSE}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        </div>
      ) : (
        <p className="flex items-center gap-1.5 text-[15px] text-graphite">
          Thinking…
          <span aria-hidden className="animate-caret inline-block h-4 w-[2px] bg-ballpoint" />
        </p>
      )}
    </div>
  )
}

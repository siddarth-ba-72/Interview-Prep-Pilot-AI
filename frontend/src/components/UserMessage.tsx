import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

/** What the learner wrote: a short note on the right, in a white card. */
export default function UserMessage({ content }: { content: string }) {
  return (
    <div className="flex justify-end" data-testid="chat-message-user" data-clarity-mask="True">
      <div className="max-w-[min(80%,36rem)] rounded-lg border border-line bg-sheet px-4 py-2.5">
        <div className="prose max-w-none text-[15px] leading-[1.6] prose-p:my-1 prose-pre:my-2">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        </div>
      </div>
    </div>
  )
}

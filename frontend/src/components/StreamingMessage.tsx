import ReactMarkdown from 'react-markdown'

interface StreamingMessageProps {
  content: string
}

export default function StreamingMessage({ content }: StreamingMessageProps) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[80%] rounded-2xl rounded-bl-sm border border-border bg-surface px-4 py-3">
        {content ? (
          <div className="prose prose-sm dark:prose-invert max-w-none prose-p:my-1.5 prose-pre:my-2 prose-headings:my-2">
            <ReactMarkdown>{content}</ReactMarkdown>
          </div>
        ) : (
          <span className="text-sm italic text-muted">Thinking...</span>
        )}
      </div>
    </div>
  )
}

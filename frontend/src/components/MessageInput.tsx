import { FormEvent, useState } from 'react'
import { Send } from 'lucide-react'

interface MessageInputProps {
  onSend: (content: string) => void
  disabled: boolean
}

export default function MessageInput({ onSend, disabled }: MessageInputProps) {
  const [content, setContent] = useState('')

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!content.trim() || disabled) return
    onSend(content.trim())
    setContent('')
  }

  return (
    <form className="flex items-end gap-3" onSubmit={handleSubmit}>
      <textarea
        placeholder="Type your message..."
        value={content}
        onChange={(e) => setContent(e.target.value)}
        disabled={disabled}
        rows={2}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSubmit(e)
          }
        }}
        className="min-h-[46px] flex-1 resize-none rounded-xl border border-border bg-bg px-3.5 py-2.5 text-sm text-fg outline-none transition-colors placeholder:text-muted focus:border-primary focus:ring-2 focus:ring-primary/20"
      />
      <button
        type="submit"
        disabled={disabled || !content.trim()}
        className="flex h-[46px] shrink-0 items-center gap-1.5 rounded-xl bg-primary px-5 text-sm font-bold text-primary-fg transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
      >
        <Send size={15} />
        <span className="hidden sm:inline">Send</span>
      </button>
    </form>
  )
}

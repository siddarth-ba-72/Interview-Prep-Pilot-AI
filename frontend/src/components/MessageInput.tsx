import { FormEvent, useState } from 'react'
import { ArrowUp } from 'lucide-react'
import { Button } from './ui/Button'
import { textareaClass } from './ui/field'

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
    <form onSubmit={handleSubmit}>
      <div className="flex items-end gap-2">
        <label htmlFor="learn-message" className="sr-only">
          Message the tutor
        </label>
        <textarea
          id="learn-message"
          placeholder="Type your message…"
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
          className={`${textareaClass} min-h-[46px] resize-none`}
        />
        <Button type="submit" variant="primary" size="lg" disabled={disabled || !content.trim()} className="h-[46px]">
          <ArrowUp size={16} aria-hidden />
          Send
        </Button>
      </div>
      <p className="type-meta mt-1.5 hidden sm:block">Enter to send, Shift + Enter for a new line.</p>
    </form>
  )
}

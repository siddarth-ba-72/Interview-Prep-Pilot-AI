import { FormEvent, useState } from 'react'

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
    <form className="message-input-bar" onSubmit={handleSubmit}>
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
      />
      <button type="submit" className="primary-button message-send-button" disabled={disabled || !content.trim()}>
        Send
      </button>
    </form>
  )
}

import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { useMutation } from '@tanstack/react-query'
import { CircleCheck, MessageSquareText } from 'lucide-react'
import { FEEDBACK_MAX_LENGTH, submitFeedback } from '../api/feedback'
import { extractErrorMessage } from '../api/topics'
import { trackEvent } from '../features/analytics/clarity'

/** Header button that opens a modal for sending feedback. Users can send as many as they like. */
export default function FeedbackButton() {
  const [open, setOpen] = useState(false)
  // Kept while the modal is closed, so a stray click outside does not lose a draft
  const [message, setMessage] = useState('')
  const [sent, setSent] = useState(false)

  const mutation = useMutation({
    mutationFn: submitFeedback,
    onSuccess: () => {
      setMessage('')
      setSent(true)
      trackEvent('feedback_sent')
    },
  })

  function openModal() {
    if (!mutation.isPending) {
      mutation.reset()
      setSent(false)
    }
    setOpen(true)
  }

  useEffect(() => {
    if (!open) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open])

  const trimmed = message.trim()
  const canSend = trimmed.length > 0 && !mutation.isPending

  return (
    <>
      <button
        type="button"
        onClick={openModal}
        aria-label="Send feedback"
        title="Send feedback"
        className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border px-3 text-sm font-semibold text-muted transition-colors hover:bg-surface-hover hover:text-fg"
      >
        <MessageSquareText size={15} />
        <span className="hidden lg:inline">Feedback</span>
      </button>

      {/* Portal: the header's backdrop blur would otherwise confine a fixed overlay to the header */}
      {open &&
        createPortal(
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
            onClick={() => setOpen(false)}
          >
            <div
              role="dialog"
              aria-modal="true"
              aria-labelledby="feedback-title"
              className="animate-modal-pop w-full max-w-lg rounded-2xl border border-border bg-surface p-6 shadow-2xl"
              onClick={(event) => event.stopPropagation()}
            >
              {sent ? (
                <div className="flex flex-col items-center gap-3 py-4 text-center">
                  <CircleCheck size={40} className="text-success" />
                  <h2 id="feedback-title" className="text-xl font-extrabold text-fg">
                    Thanks for your feedback
                  </h2>
                  <p className="text-sm text-muted">We read every message.</p>
                  <div className="mt-3 flex gap-2">
                    <button
                      type="button"
                      onClick={() => setSent(false)}
                      className="rounded-lg border border-border px-4 py-2.5 text-sm font-bold text-fg transition-colors hover:bg-surface-hover"
                    >
                      Send more
                    </button>
                    <button
                      type="button"
                      onClick={() => setOpen(false)}
                      className="rounded-lg bg-primary px-4 py-2.5 text-sm font-bold text-primary-fg transition-colors hover:bg-primary-hover"
                    >
                      Close
                    </button>
                  </div>
                </div>
              ) : (
                <form
                  data-clarity-mask="True"
                  onSubmit={(event) => {
                    event.preventDefault()
                    if (canSend) mutation.mutate(trimmed)
                  }}
                >
                  <h2 id="feedback-title" className="text-xl font-extrabold text-fg">
                    Send feedback
                  </h2>
                  <p className="mt-1 text-sm text-muted">
                    What is working, what is broken, what you would like to see.
                  </p>

                  <textarea
                    value={message}
                    onChange={(event) => setMessage(event.target.value)}
                    maxLength={FEEDBACK_MAX_LENGTH}
                    rows={6}
                    autoFocus
                    aria-label="Your feedback"
                    placeholder="Your feedback"
                    className="mt-4 w-full resize-y rounded-xl border border-border bg-bg px-3 py-2.5 text-sm text-fg outline-none transition-colors placeholder:text-muted focus:border-primary"
                  />
                  <div className="mt-1 flex items-start justify-between gap-3">
                    <p className="text-sm font-medium text-danger" role="alert">
                      {mutation.isError &&
                        extractErrorMessage(mutation.error, 'Could not send your feedback. Please try again.')}
                    </p>
                    <span className="shrink-0 text-xs tabular-nums text-muted">
                      {message.length}/{FEEDBACK_MAX_LENGTH}
                    </span>
                  </div>

                  <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
                    <button
                      type="button"
                      onClick={() => setOpen(false)}
                      className="rounded-lg border border-border px-4 py-2.5 text-sm font-bold text-fg transition-colors hover:bg-surface-hover"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={!canSend}
                      className="rounded-lg bg-primary px-4 py-2.5 text-sm font-bold text-primary-fg transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {mutation.isPending ? 'Sending…' : 'Send'}
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>,
          document.body,
        )}
    </>
  )
}

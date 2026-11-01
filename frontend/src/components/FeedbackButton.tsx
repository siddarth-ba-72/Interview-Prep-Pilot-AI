import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { MessageSquareText } from 'lucide-react'
import { FEEDBACK_MAX_LENGTH, submitFeedback } from '../api/feedback'
import { extractErrorMessage } from '../api/topics'
import { trackEvent } from '../features/analytics/clarity'
import { Button, buttonClass } from './ui/Button'
import { textareaClass } from './ui/field'
import Dialog from './ui/Dialog'

/** Header button that opens a dialog for sending feedback. Users can send as many as they like. */
export default function FeedbackButton() {
  const [open, setOpen] = useState(false)
  // Kept while the dialog is closed, so a stray click outside does not lose a draft
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

  function openDialog() {
    if (!mutation.isPending) {
      mutation.reset()
      setSent(false)
    }
    setOpen(true)
  }

  const trimmed = message.trim()
  const canSend = trimmed.length > 0 && !mutation.isPending

  return (
    <>
      <button
        type="button"
        onClick={openDialog}
        aria-label="Send feedback"
        title="Send feedback"
        className={buttonClass({ variant: 'quiet', size: 'sm', className: 'w-8 px-0 lg:w-auto lg:px-2.5' })}
      >
        <MessageSquareText size={16} aria-hidden />
        <span className="hidden lg:inline">Feedback</span>
      </button>

      {open && (
        <Dialog labelledBy="feedback-title" onClose={() => setOpen(false)}>
          {sent ? (
            <div>
              <h2 id="feedback-title" className="type-section text-lg">
                Thanks for your feedback
              </h2>
              <p className="type-body mt-1 text-graphite">We read every message.</p>
              <div className="mt-6 flex justify-end gap-2">
                <Button onClick={() => setSent(false)}>Send more</Button>
                <Button variant="primary" onClick={() => setOpen(false)}>
                  Close
                </Button>
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
              <h2 id="feedback-title" className="type-section text-lg">
                Send feedback
              </h2>
              <p className="type-body mt-1 text-graphite">What works, what is broken, what you would like to see.</p>

              <label htmlFor="feedback-message" className="sr-only">
                Your feedback
              </label>
              <textarea
                id="feedback-message"
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                maxLength={FEEDBACK_MAX_LENGTH}
                rows={6}
                autoFocus
                placeholder="Your feedback"
                className={`${textareaClass} mt-4 resize-y`}
              />
              <div className="mt-1.5 flex items-start justify-between gap-3">
                <p className="text-sm text-redpen" role="alert">
                  {mutation.isError && extractErrorMessage(mutation.error, 'Could not send your feedback. Please try again.')}
                </p>
                <span className="figures shrink-0 text-xs text-pencil">
                  {message.length.toLocaleString()} / {FEEDBACK_MAX_LENGTH.toLocaleString()}
                </span>
              </div>

              <div className="mt-5 flex justify-end gap-2">
                <Button onClick={() => setOpen(false)}>Cancel</Button>
                <Button type="submit" variant="primary" disabled={!canSend}>
                  {mutation.isPending ? 'Sending…' : 'Send'}
                </Button>
              </div>
            </form>
          )}
        </Dialog>
      )}
    </>
  )
}

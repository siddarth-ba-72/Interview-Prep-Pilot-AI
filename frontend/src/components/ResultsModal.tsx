import { useNavigate } from 'react-router-dom'
import { useAppDispatch, useAppSelector } from '../hooks'
import { closeResultsModal } from '../features/tests/testSlice'

export default function ResultsModal() {
  const navigate = useNavigate()
  const dispatch = useAppDispatch()

  const { open, sessionId } = useAppSelector((state) => state.tests.resultsModal)
  const reports = useAppSelector((state) => state.tests.reportsBySessionId)

  if (!open || !sessionId) return null

  const report = reports[sessionId]
  if (!report) return null

  const handleViewReport = () => {
    const topicId = report.testSessionId.split('/')[0] // Adjust based on your URL structure
    navigate(`/topics/${topicId}/tests/${sessionId}/report`)
  }

  const handleGoToLearn = () => {
    dispatch(closeResultsModal())
    navigate('/dashboard')
  }

  const handleDismiss = () => {
    dispatch(closeResultsModal())
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={handleDismiss}
    >
      <div
        className="animate-modal-pop w-full max-w-lg rounded-2xl border border-border bg-surface p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-xl font-extrabold text-fg">Test Results</h2>

        <div className="mt-5 grid grid-cols-2 gap-3">
          <div className="rounded-xl border border-border bg-bg p-4 text-center">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">This Test</h3>
            <p className="mt-1 text-2xl font-extrabold text-primary">
              {report.rawScore} / {report.maxScore}
            </p>
          </div>

          <div className="rounded-xl border border-border bg-bg p-4 text-center">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">All-Time Average</h3>
            <p className="mt-1 text-2xl font-extrabold text-primary">
              {report.avgScoreAtTime ? report.avgScoreAtTime.toFixed(1) : '—'} / {report.maxScore}
            </p>
          </div>

          <div
            className={`col-span-2 rounded-xl px-4 py-3 text-center text-sm font-bold ${
              report.passed ? 'bg-success-subtle text-success-fg' : 'bg-warning-subtle text-warning-fg'
            }`}
          >
            {report.passed ? '🎉 Great job!' : '💪 Keep going'}
          </div>
        </div>

        <div className="mt-5 text-sm leading-relaxed text-muted">
          {report.passed ? (
            <p>Excellent performance! You've demonstrated solid understanding of this topic.</p>
          ) : (
            <>
              <p>
                Score: <strong className="font-bold text-fg">{report.rawScore} / {report.maxScore}</strong>{' '}
                (Pass threshold: {report.passThreshold})
              </p>
              <p className="mt-1">Consider revisiting Learn Mode to strengthen your understanding.</p>
            </>
          )}
        </div>

        <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <button
            onClick={handleViewReport}
            className="rounded-lg border border-border px-4 py-2.5 text-sm font-bold text-fg transition-colors hover:bg-surface-hover"
          >
            View Full Report
          </button>
          {!report.passed && (
            <button
              onClick={handleGoToLearn}
              className="rounded-lg border border-border px-4 py-2.5 text-sm font-bold text-fg transition-colors hover:bg-surface-hover"
            >
              Go to Learn Mode
            </button>
          )}
          <button
            onClick={handleDismiss}
            className="rounded-lg bg-primary px-4 py-2.5 text-sm font-bold text-primary-fg transition-colors hover:bg-primary-hover"
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  )
}

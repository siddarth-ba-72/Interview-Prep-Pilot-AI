import { useNavigate } from 'react-router-dom'
import { useAppDispatch, useAppSelector } from '../hooks'
import { closeResultsModal } from '../features/tests/testSlice'
import { Button } from './ui/Button'
import Dialog from './ui/Dialog'
import ScoreBar from './ui/ScoreBar'
import StatusPill from './ui/StatusPill'

/** Shown the moment a test is graded: the score against the pass mark, then where to go next. */
export default function ResultsModal({ topicId }: { topicId: string }) {
  const navigate = useNavigate()
  const dispatch = useAppDispatch()

  const { open, sessionId } = useAppSelector((state) => state.tests.resultsModal)
  const reports = useAppSelector((state) => state.tests.reportsBySessionId)

  if (!open || !sessionId) return null
  const report = reports[sessionId]
  if (!report) return null

  // Close first: the modal lives in the store and would otherwise reopen over the next test
  const go = (path: string) => {
    dispatch(closeResultsModal())
    navigate(path)
  }
  const dismiss = () => dispatch(closeResultsModal())

  return (
    <Dialog labelledBy="results-title" onClose={dismiss} mask>
      <h2 id="results-title" className="type-section text-lg">
        Test results
      </h2>
      <p className="type-body text-graphite">Attempt #{report.attemptNumber ?? 1}</p>

      <div className="mt-5 flex items-end justify-between gap-4">
        <p className="figures text-3xl font-semibold tracking-[-0.01em] text-ink">
          {report.rawScore} / {report.maxScore}
        </p>
        <StatusPill tone={report.passed ? 'positive' : 'negative'}>
          {report.passed ? 'Passed' : 'Below the pass mark'}
        </StatusPill>
      </div>
      <ScoreBar score={report.rawScore} max={report.maxScore} pass={report.passThreshold} size="md" className="mt-3" />
      <p className="figures type-meta mt-2.5">
        Pass mark {report.passThreshold}. Your average on this topic is now{' '}
        {report.avgScoreAtTime != null ? report.avgScoreAtTime.toFixed(1) : '—'}.
      </p>

      {!report.passed && (
        <p className="type-body mt-4 text-ink">
          The full report lists the questions you missed with model answers. Learn Mode is the quickest way to close
          the gaps before a re-test.
        </p>
      )}

      <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <Button onClick={dismiss}>Dismiss</Button>
        {!report.passed && <Button onClick={() => go(`/topics/${topicId}/learn`)}>Go to Learn Mode</Button>}
        <Button variant="primary" onClick={() => go(`/topics/${topicId}/tests/${sessionId}/report`)}>
          View full report
        </Button>
      </div>
    </Dialog>
  )
}

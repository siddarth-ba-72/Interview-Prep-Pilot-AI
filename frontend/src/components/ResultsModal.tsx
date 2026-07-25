import { useNavigate } from 'react-router-dom'
import { useAppDispatch, useAppSelector } from '../hooks'
import { closeResultsModal } from '../features/tests/testSlice'
import './ResultsModal.css'

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
    // We need to extract topicId from the test session
    // For now, navigate back to dashboard
    dispatch(closeResultsModal())
    navigate('/dashboard')
  }
  
  const handleDismiss = () => {
    dispatch(closeResultsModal())
  }

  return (
    <div className="modal-overlay" onClick={handleDismiss}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Test Results</h2>
        </div>

        <div className="score-panel">
          <div className="score-section">
            <h3>This Test</h3>
            <p className="score-display">{report.rawScore} / {report.maxScore}</p>
          </div>

          <div className="score-section">
            <h3>All-Time Average</h3>
            <p className="score-display">
              {report.avgScoreAtTime ? report.avgScoreAtTime.toFixed(1) : '—'} / {report.maxScore}
            </p>
          </div>

          <div className={`passed-badge ${report.passed ? 'passed' : 'failed'}`}>
            {report.passed ? '🎉 Great job!' : '💪 Keep going'}
          </div>
        </div>

        <div className="modal-body">
          {report.passed ? (
            <div className="passed-message">
              <p>Excellent performance! You've demonstrated solid understanding of this topic.</p>
            </div>
          ) : (
            <div className="failed-message">
              <p>
                Score: <strong>{report.rawScore} / {report.maxScore}</strong> (Pass threshold: {report.passThreshold})
              </p>
              <p>Consider revisiting Learn Mode to strengthen your understanding.</p>
            </div>
          )}
        </div>

        <div className="modal-actions">
          <button className="button-secondary" onClick={handleViewReport}>
            View Full Report
          </button>
          {!report.passed && (
            <button className="button-secondary" onClick={handleGoToLearn}>
              Go to Learn Mode
            </button>
          )}
          <button className="button-primary" onClick={handleDismiss}>
            Dismiss
          </button>
        </div>
      </div>
    </div>
  )
}

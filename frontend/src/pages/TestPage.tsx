import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useAppDispatch, useAppSelector } from '../hooks'
import * as testAPI from '../api/tests'
import * as topicAPI from '../api/topics'
import {
  setTestGenerating,
  setTestSession,
  updateAnswer,
  setTestSubmitting,
  setTestCompleted,
  openResultsModal,
} from '../features/tests/testSlice'
import ResultsModal from '../components/ResultsModal'
import './TestPage.css'

export default function TestPage() {
  const navigate = useNavigate()
  const params = useParams<{ topicId: string }>()
  const topicId = params.topicId!
  const dispatch = useAppDispatch()

  const [topic, setTopic] = useState<topicAPI.Topic | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const testState = useAppSelector((state: any) => state.tests.activeSessionByTopicId[topicId])

  // Load topic and initialize test on mount
  useEffect(() => {
    if (!topicId) {
      setError('Topic ID is missing')
      setLoading(false)
      return
    }
    
    async function loadTopicAndTest() {
      try {
        const topics = await topicAPI.listTopics()
        const currentTopic = topics.find((t: topicAPI.Topic) => t.id === topicId)
        if (!currentTopic) {
          setError('Topic not found')
          return
        }
        setTopic(currentTopic)

        // Start test
        dispatch(setTestGenerating({ topicId }))
        const response = await testAPI.startTest(topicId)
        dispatch(
          setTestSession({
            topicId,
            sessionId: response.sessionId,
            questions: response.questions,
          })
        )
      } catch (err) {
        setError((err as Error).message || 'Failed to load test')
      } finally {
        setLoading(false)
      }
    }

    loadTopicAndTest()
  }, [topicId, dispatch])

  const handleAnswerChange = (questionId: string, answer: string | null): void => {
    dispatch(updateAnswer({ topicId, questionId, answer }))
  }

  const handleSubmit = async () => {
    if (!testState) return

    const unansweredCount = testState.questions.length - 
      Object.values(testState.answers).filter((a) => a !== null).length
    
    if (unansweredCount > 0) {
      if (!confirm(`${unansweredCount} of ${testState.questions.length} questions unanswered. Submit anyway?`)) {
        return
      }
    }

    try {
      dispatch(setTestSubmitting({ topicId }))
      
      const answers: testAPI.SubmitAnswerRequest[] = testState.questions.map((q: testAPI.TestQuestion) => ({
        questionId: q.questionId,
        userAnswer: testState.answers[q.questionId] || null,
      }))

      const report = await testAPI.submitTest(topicId, testState.sessionId!, {
        answers,
      })

      dispatch(setTestCompleted({ topicId, report }))
      dispatch(openResultsModal({ sessionId: testState.sessionId! }))
    } catch (err) {
      setError((err as Error).message || 'Failed to submit test')
    }
  }

  if (loading) {
    return <div className="test-page"><p>Generating test...</p></div>
  }

  if (error) {
    return (
      <div className="test-page error">
        <p>{error}</p>
        <button onClick={() => navigate('/dashboard')}>Back to Dashboard</button>
      </div>
    )
  }

  if (!testState || !topic) {
    return <div className="test-page"><p>Loading...</p></div>
  }

  const mcqQuestions = testState.questions.filter((q: testAPI.TestQuestion) => q.section === 'MCQ')
  const subjectiveQuestions = testState.questions.filter((q: testAPI.TestQuestion) => q.section === 'SUBJECTIVE')
  const answeredCount = Object.values(testState.answers).filter((a) => a !== null).length

  return (
    <div className="test-page">
      <div className="test-header">
        <h1>{topic.name}</h1>
        <p>Test Mode</p>
      </div>

      <div className="test-content">
        <div className="test-progress-bar">
          <div className="progress-fill" style={{ width: `${(answeredCount / testState.questions.length) * 100}%` }}></div>
        </div>
        <p className="progress-text">{answeredCount} of {testState.questions.length} questions answered</p>

        {/* MCQ Section */}
        <section className="test-section">
          <h2>Multiple Choice Questions (10 questions)</h2>
          {mcqQuestions.map((question: testAPI.TestQuestion, idx: number) => (
            <div key={question.questionId} className="question-container">
              <h3>Question {idx + 1}</h3>
              <p className="question-text">{question.text}</p>
              <div className="options">
                {question.options?.map((option: string) => (
                  <label key={option} className="option-label">
                    <input
                      type="radio"
                      name={question.questionId}
                      value={option}
                      checked={testState.answers[question.questionId] === option}
                      onChange={(e) => handleAnswerChange(question.questionId, e.target.value)}
                      disabled={testState.status === 'submitting'}
                    />
                    {option}
                  </label>
                ))}
              </div>
            </div>
          ))}
        </section>

        {/* Subjective Section */}
        <section className="test-section">
          <h2>Subjective / Code Completion (10 questions)</h2>
          {subjectiveQuestions.map((question: testAPI.TestQuestion, idx: number) => (
            <div key={question.questionId} className="question-container">
              <h3>Question {idx + 1 + mcqQuestions.length}</h3>
              <p className="question-text">{question.text}</p>
              <textarea
                className="answer-textarea"
                value={testState.answers[question.questionId] || ''}
                onChange={(e) => handleAnswerChange(question.questionId, e.target.value || null)}
                placeholder="Enter your answer here..."
                disabled={testState.status === 'submitting'}
              />
            </div>
          ))}
        </section>

        {/* Submit Button */}
        <div className="submit-section">
          <button
            className="submit-button"
            onClick={handleSubmit}
            disabled={testState.status === 'submitting'}
          >
            {testState.status === 'submitting' ? 'Submitting...' : 'Submit Test'}
          </button>
        </div>
      </div>

      {/* Results Modal */}
      <ResultsModal />
    </div>
  )
}

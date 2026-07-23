import { useNavigate } from 'react-router-dom'
import { useState } from 'react'
import type { Topic } from '../api/topics'

interface TopicCardProps {
  topic: Topic
  onDelete: (topicId: string) => void
  isDeleting: boolean
}

export default function TopicCard({ topic, onDelete, isDeleting }: TopicCardProps) {
  const navigate = useNavigate()
  const [confirming, setConfirming] = useState(false)

  function handleDeleteClick() {
    if (confirming) {
      onDelete(topic.id)
      setConfirming(false)
    } else {
      setConfirming(true)
    }
  }

  const initial = topic.name.charAt(0).toUpperCase()

  return (
    <div className="topic-card">
      <div className="topic-card-top">
        <div className="topic-avatar">{initial}</div>
        <button
          className="topic-delete-button"
          onClick={handleDeleteClick}
          onBlur={() => setConfirming(false)}
          disabled={isDeleting}
        >
          {confirming ? '✓ Confirm' : '✕'}
        </button>
      </div>
      <h3 className="topic-card-name">{topic.name}</h3>
      <p className="topic-card-date">{new Date(topic.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</p>
      <div className="topic-card-modes">
        <button className="mode-button mode-button-primary" onClick={() => navigate(`/topics/${topic.id}/learn`)}>
          Learn
        </button>
        <button className="mode-button" disabled title="Coming soon">
          Test
        </button>
        <button className="mode-button" disabled title="Coming soon">
          Mock
        </button>
      </div>
    </div>
  )
}

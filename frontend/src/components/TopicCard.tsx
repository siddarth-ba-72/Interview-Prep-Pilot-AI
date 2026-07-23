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

  return (
    <div className="topic-card">
      <div className="topic-card-header">
        <h3>{topic.name}</h3>
        <button
          className="topic-delete-button"
          onClick={handleDeleteClick}
          onBlur={() => setConfirming(false)}
          disabled={isDeleting}
        >
          {confirming ? 'Confirm delete?' : 'Delete'}
        </button>
      </div>
      <div className="topic-card-modes">
        <button className="mode-button" onClick={() => navigate(`/topics/${topic.id}/learn`)}>
          Learn
        </button>
        <button className="mode-button" disabled title="Coming in a future phase">
          Test
        </button>
        <button className="mode-button" disabled title="Coming in a future phase">
          Mock Interview
        </button>
      </div>
    </div>
  )
}

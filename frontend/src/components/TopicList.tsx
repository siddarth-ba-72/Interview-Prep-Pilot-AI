import type { Topic } from '../api/topics'
import TopicCard from './TopicCard'

interface TopicListProps {
  topics: Topic[]
  onDelete: (topicId: string) => void
  deletingId: string | null
}

export default function TopicList({ topics, onDelete, deletingId }: TopicListProps) {
  if (topics.length === 0) {
    return <p className="muted-text">No topics yet. Add one above to get started.</p>
  }

  return (
    <div className="topic-grid">
      {topics.map((topic) => (
        <TopicCard key={topic.id} topic={topic} onDelete={onDelete} isDeleting={deletingId === topic.id} />
      ))}
    </div>
  )
}

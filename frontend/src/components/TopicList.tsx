import type { Topic } from '../api/topics'
import TopicRow from './TopicRow'
import EmptyState from './ui/EmptyState'

interface TopicListProps {
  topics: Topic[]
  onDelete: (topicId: string) => void
  deletingId: string | null
}

export default function TopicList({ topics, onDelete, deletingId }: TopicListProps) {
  if (topics.length === 0) {
    return <EmptyState>No topics yet. Add one above to get started.</EmptyState>
  }

  return (
    <ul className="divide-y divide-rule rounded-lg border border-line bg-sheet">
      {topics.map((topic) => (
        <TopicRow key={topic.id} topic={topic} onDelete={onDelete} isDeleting={deletingId === topic.id} />
      ))}
    </ul>
  )
}

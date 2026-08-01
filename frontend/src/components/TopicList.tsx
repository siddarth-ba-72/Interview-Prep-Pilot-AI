import type { Topic } from '../api/topics'
import TopicCard from './TopicCard'

interface TopicListProps {
  topics: Topic[]
  onDelete: (topicId: string) => void
  deletingId: string | null
}

export default function TopicList({ topics, onDelete, deletingId }: TopicListProps) {
  if (topics.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-border bg-surface/50 px-6 py-14 text-center">
        <p className="text-sm font-medium text-muted">No topics yet. Add one above to get started.</p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {topics.map((topic) => (
        <TopicCard key={topic.id} topic={topic} onDelete={onDelete} isDeleting={deletingId === topic.id} />
      ))}
    </div>
  )
}

import { Link } from 'react-router-dom'
import { Rocket } from 'lucide-react'
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
      <div className="relative overflow-hidden rounded-3xl border-2 border-dashed border-border bg-surface/50 px-6 py-14 text-center">
        <div className="animate-float mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-accent text-white shadow-xl shadow-primary/30">
          <Rocket size={28} aria-hidden />
        </div>
        <p className="text-lg font-extrabold text-fg">Your launchpad is ready</p>
        <p className="mt-1 text-sm font-medium text-muted">No topics yet. Add one above to get started.</p>
        <p className="mt-2 text-sm text-muted">
          New to PrepPilot?{' '}
          <Link to="/how-it-works" className="font-semibold text-primary">
            See how it works
          </Link>
        </p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {topics.map((topic, i) => (
        <TopicCard key={topic.id} topic={topic} index={i} onDelete={onDelete} isDeleting={deletingId === topic.id} />
      ))}
    </div>
  )
}

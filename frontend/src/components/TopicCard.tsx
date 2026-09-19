import { useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { X, Check, History } from 'lucide-react'
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
    <div className="group flex flex-col rounded-2xl border border-border bg-surface p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-md">
      <div className="mb-3.5 flex items-start justify-between">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-accent text-lg font-extrabold text-white">
          {initial}
        </div>
        <button
          onClick={handleDeleteClick}
          onBlur={() => setConfirming(false)}
          disabled={isDeleting}
          className={`flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
            confirming
              ? 'bg-danger-subtle text-danger'
              : 'text-muted opacity-0 hover:bg-danger-subtle hover:text-danger group-hover:opacity-100'
          }`}
        >
          {confirming ? (
            <>
              <Check size={13} /> Confirm
            </>
          ) : (
            <X size={15} />
          )}
        </button>
      </div>

      <h3 className="mb-0.5 truncate text-base font-bold text-fg">{topic.name}</h3>
      <p className="mb-4 text-xs text-muted">
        {new Date(topic.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
      </p>

      {topic.avgScore !== null && topic.avgScore !== undefined && (
        <div className="mb-4 inline-flex w-fit items-center rounded-full border border-primary/20 bg-primary-subtle px-3 py-1 text-xs font-semibold text-primary">
          Avg: {topic.avgScore.toFixed(1)}/60 ({topic.testCount} tests)
        </div>
      )}

      <div className="mt-auto flex flex-col gap-2.5">
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate(`/topics/${topic.id}/learn`)}
            className="flex-1 rounded-lg bg-primary py-2 text-xs font-bold text-primary-fg transition-colors hover:bg-primary-hover"
          >
            Learn
          </button>
          <button
            onClick={() => navigate(`/topics/${topic.id}/test`)}
            className="flex-1 rounded-lg bg-primary py-2 text-xs font-bold text-primary-fg transition-colors hover:bg-primary-hover"
          >
            Test
          </button>
          <button
            onClick={() => navigate(`/topics/${topic.id}/interviews`)}
            className="flex-1 rounded-lg border border-border py-2 text-xs font-semibold text-fg transition-colors hover:bg-surface-hover"
          >
            Mock
          </button>
        </div>

        {/* Always shown: a hidden-until-you-have-history link is invisible exactly when
            someone goes looking for it. Both destinations have their own empty state. */}
        <div className="flex items-center gap-1 text-[11px] font-semibold text-muted">
          <History size={12} className="shrink-0" />
          <button
            onClick={() => navigate(`/topics/${topic.id}/tests`)}
            className="rounded px-1 py-0.5 transition-colors hover:bg-surface-hover hover:text-fg"
          >
            Test history
          </button>
          <span aria-hidden className="text-border">
            |
          </span>
          <button
            onClick={() => navigate(`/topics/${topic.id}/interviews/history`)}
            className="rounded px-1 py-0.5 transition-colors hover:bg-surface-hover hover:text-fg"
          >
            Interview history
          </button>
        </div>
      </div>
    </div>
  )
}

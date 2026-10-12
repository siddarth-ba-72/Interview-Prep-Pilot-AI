import { useNavigate } from 'react-router-dom'
import { useState, type MouseEvent } from 'react'
import { X, Check, History, BookOpen, ClipboardCheck, Mic, ArrowRight } from 'lucide-react'
import type { Topic } from '../api/topics'

interface TopicCardProps {
  topic: Topic
  onDelete: (topicId: string) => void
  isDeleting: boolean
  /** Position in the list, used to stagger the entrance animation. */
  index?: number
}

// Literal class names so Tailwind generates them; a topic keeps its colours across visits.
const PALETTES = [
  { gradient: 'from-indigo-500 to-violet-500', glow: 'hover:shadow-indigo-500/20' },
  { gradient: 'from-sky-500 to-cyan-400', glow: 'hover:shadow-sky-500/20' },
  { gradient: 'from-emerald-500 to-teal-400', glow: 'hover:shadow-emerald-500/20' },
  { gradient: 'from-amber-500 to-orange-500', glow: 'hover:shadow-amber-500/20' },
  { gradient: 'from-rose-500 to-pink-500', glow: 'hover:shadow-rose-500/20' },
  { gradient: 'from-fuchsia-500 to-purple-500', glow: 'hover:shadow-fuchsia-500/20' },
]

function paletteFor(name: string) {
  let hash = 0
  for (const char of name) hash = (hash * 31 + char.charCodeAt(0)) | 0
  return PALETTES[Math.abs(hash) % PALETTES.length]
}

const MAX_SCORE = 60

export default function TopicCard({ topic, onDelete, isDeleting, index = 0 }: TopicCardProps) {
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

  function trackPointer(e: MouseEvent<HTMLDivElement>) {
    const rect = e.currentTarget.getBoundingClientRect()
    e.currentTarget.style.setProperty('--spot-x', `${e.clientX - rect.left}px`)
    e.currentTarget.style.setProperty('--spot-y', `${e.clientY - rect.top}px`)
  }

  const initial = topic.name.charAt(0).toUpperCase()
  const palette = paletteFor(topic.name)
  const hasScore = topic.avgScore !== null && topic.avgScore !== undefined

  return (
    <div
      onMouseMove={trackPointer}
      style={{ animationDelay: `${Math.min(index, 12) * 60}ms` }}
      className={`spotlight animate-rise-in group relative flex flex-col overflow-hidden rounded-2xl border border-border bg-surface p-5 pt-6 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-primary/30 hover:shadow-xl ${palette.glow} ${
        isDeleting ? 'scale-95 opacity-50' : ''
      }`}
    >
      <span aria-hidden className={`absolute inset-x-0 top-0 h-1.5 bg-gradient-to-r ${palette.gradient}`} />
      <span
        aria-hidden
        className={`pointer-events-none absolute -right-10 -top-10 h-32 w-32 rounded-full bg-gradient-to-br ${palette.gradient} opacity-10 blur-2xl transition-opacity duration-500 group-hover:opacity-30`}
      />

      <div className="relative mb-3.5 flex items-start justify-between">
        <div
          className={`flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br ${palette.gradient} text-xl font-black text-white shadow-lg transition-transform duration-300 group-hover:-rotate-6 group-hover:scale-110`}
        >
          {initial}
        </div>
        <button
          onClick={handleDeleteClick}
          onBlur={() => setConfirming(false)}
          disabled={isDeleting}
          aria-label={confirming ? 'Confirm' : `Delete ${topic.name}`}
          className={`flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
            confirming
              ? 'bg-danger-subtle text-danger'
              : 'text-muted opacity-0 hover:bg-danger-subtle hover:text-danger focus-visible:opacity-100 group-hover:opacity-100'
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

      <h3 className="relative mb-0.5 truncate text-lg font-extrabold text-fg" title={topic.name}>
        {topic.name}
      </h3>
      <p className="relative mb-4 text-xs text-muted">
        Added{' '}
        {new Date(topic.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
      </p>

      {hasScore ? (
        <div className="relative mb-4" data-clarity-mask="True">
          <div className="mb-1.5 flex items-baseline justify-between text-xs">
            <span className="font-semibold text-muted">
              Avg over {topic.testCount} {topic.testCount === 1 ? 'test' : 'tests'}
            </span>
            <span className="font-extrabold text-fg">
              {topic.avgScore!.toFixed(1)}
              <span className="font-semibold text-muted">/{MAX_SCORE}</span>
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-surface-hover">
            <div
              className={`h-full origin-left rounded-full bg-gradient-to-r ${palette.gradient} animate-grow-x`}
              style={{
                width: `${Math.min(100, Math.max(0, (topic.avgScore! / MAX_SCORE) * 100))}%`,
                animationDuration: '1s',
              }}
            />
          </div>
        </div>
      ) : (
        <p className="relative mb-4 inline-flex w-fit items-center gap-1 rounded-full bg-surface-hover px-2.5 py-1 text-[11px] font-semibold text-muted">
          No tests yet: take one to see your score
        </p>
      )}

      <div className="relative mt-auto flex flex-col gap-2.5">
        <div className="flex items-center gap-2">
          <ModeButton onClick={() => navigate(`/topics/${topic.id}/learn`)} icon={<BookOpen size={14} />} label="Learn" />
          <ModeButton
            onClick={() => navigate(`/topics/${topic.id}/test`)}
            icon={<ClipboardCheck size={14} />}
            label="Test"
          />
        </div>

        <button
          onClick={() => navigate(`/topics/${topic.id}/interviews`)}
          className={`group/mock flex w-full items-center justify-center gap-1.5 rounded-xl bg-gradient-to-r ${palette.gradient} py-2.5 text-xs font-bold text-white shadow-md transition-all hover:shadow-lg hover:brightness-110 active:scale-[0.98]`}
        >
          <Mic size={14} aria-hidden />
          Mock Interview
          <ArrowRight size={14} aria-hidden className="transition-transform group-hover/mock:translate-x-1" />
        </button>

        {/* Always shown: a hidden-until-you-have-history link is invisible exactly when
            someone goes looking for it. Both destinations have their own empty state. */}
        <div className="flex items-center gap-2 text-xs font-semibold text-fg">
          <History size={14} className="shrink-0 text-muted" />
          <button
            onClick={() => navigate(`/topics/${topic.id}/tests`)}
            className="rounded px-1.5 py-0.5 transition-colors hover:bg-surface-hover hover:text-primary"
          >
            Test history
          </button>
          <span aria-hidden className="text-border">
            |
          </span>
          <button
            onClick={() => navigate(`/topics/${topic.id}/interviews/history`)}
            className="rounded px-1.5 py-0.5 transition-colors hover:bg-surface-hover hover:text-primary"
          >
            Interview history
          </button>
        </div>
      </div>
    </div>
  )
}

function ModeButton({ onClick, icon, label }: { onClick: () => void; icon: JSX.Element; label: string }) {
  return (
    <button
      onClick={onClick}
      className="flex flex-1 items-center justify-center gap-1.5 rounded-xl border border-border bg-surface py-2 text-xs font-bold text-fg transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:bg-primary-subtle hover:text-primary active:scale-95"
    >
      <span aria-hidden>{icon}</span>
      {label}
    </button>
  )
}

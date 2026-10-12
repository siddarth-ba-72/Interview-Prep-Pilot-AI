import { useEffect, useState } from 'react'
import { BookOpen, ClipboardCheck, FolderOpen, Gauge, Mic, type LucideIcon } from 'lucide-react'
import type { ActionUsage, Usage } from '../api/usage'
import { formatAvailableAt, isLocked } from '../api/usage'

interface UsageSummaryProps {
  usage: Usage
  topicCount: number
}

export default function UsageSummary({ usage, topicCount }: UsageSummaryProps) {
  const topicLimit = usage.topics.limit
  return (
    <section aria-label="Usage limits" className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-sm font-bold text-fg">
          <Gauge size={16} className="text-primary" aria-hidden />
          Today&apos;s fuel
        </h2>
        <p className="text-xs text-muted">
          Once you use up a limit, it comes back in full {usage.windowHours} hours after your last use.
        </p>
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {topicLimit !== null && (
          <Tile
            icon={FolderOpen}
            label="Topics"
            value={`${topicCount} / ${topicLimit}`}
            fraction={Math.max(0, topicLimit - topicCount) / topicLimit}
            hint={topicCount >= topicLimit ? 'Delete one to add another' : `${topicLimit - topicCount} more allowed`}
            exhausted={topicCount >= topicLimit}
          />
        )}
        <ActionTile icon={BookOpen} label="Learn messages" usage={usage.learnMessages} />
        <ActionTile icon={ClipboardCheck} label="Tests" usage={usage.tests} />
        <ActionTile icon={Mic} label="Mock interviews" usage={usage.mockInterviews} />
      </div>
    </section>
  )
}

function ActionTile({ icon, label, usage }: { icon: LucideIcon; label: string; usage: ActionUsage }) {
  const locked = isLocked(usage)
  const hint = !locked
    ? `of ${usage.limit} left`
    : usage.availableAt
      ? `Back ${formatAvailableAt(usage.availableAt)}`
      : 'Not available'
  return (
    <Tile
      icon={icon}
      label={label}
      value={locked ? '0' : String(usage.remaining)}
      fraction={locked || usage.limit === 0 ? 0 : usage.remaining / usage.limit}
      hint={hint}
      exhausted={locked}
    />
  )
}

const RADIUS = 20
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

function Tile({
  icon: Icon,
  label,
  value,
  fraction,
  hint,
  exhausted,
}: {
  icon: LucideIcon
  label: string
  value: string
  /** Share still available, 0-1; drawn as the ring. */
  fraction: number
  hint: string
  exhausted: boolean
}) {
  // Start empty and fill on mount so the ring animates in
  const [shown, setShown] = useState(0)
  useEffect(() => {
    const frame = requestAnimationFrame(() => setShown(Math.min(1, Math.max(0, fraction))))
    return () => cancelAnimationFrame(frame)
  }, [fraction])

  const low = !exhausted && fraction <= 0.34
  const ringColor = exhausted ? 'var(--danger)' : low ? 'var(--warning)' : 'var(--primary)'

  return (
    <div
      className={`group flex items-center gap-3 rounded-2xl border px-3 py-3 transition-all hover:-translate-y-0.5 hover:shadow-md sm:px-4 ${
        exhausted ? 'border-danger/30 bg-danger-subtle' : 'border-border bg-surface hover:border-primary/30'
      }`}
    >
      <div className="relative h-12 w-12 shrink-0">
        <svg viewBox="0 0 48 48" className="h-12 w-12 -rotate-90" aria-hidden>
          <circle cx="24" cy="24" r={RADIUS} fill="none" stroke="var(--border)" strokeWidth="5" />
          <circle
            cx="24"
            cy="24"
            r={RADIUS}
            fill="none"
            stroke={ringColor}
            strokeWidth="5"
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={CIRCUMFERENCE * (1 - shown)}
            className="transition-[stroke-dashoffset] duration-1000 ease-out motion-reduce:transition-none"
          />
        </svg>
        <Icon
          size={16}
          aria-hidden
          className={`absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 transition-transform group-hover:scale-125 ${
            exhausted ? 'text-danger' : 'text-muted'
          }`}
        />
      </div>
      <div className="min-w-0">
        <p className="truncate text-[11px] font-semibold uppercase tracking-wide text-muted">{label}</p>
        <p className={`mt-0.5 text-lg font-extrabold leading-none ${exhausted ? 'text-danger-fg' : 'text-fg'}`}>{value}</p>
        <p className={`mt-1 text-xs leading-snug ${exhausted ? 'text-danger-fg' : 'text-muted'}`}>{hint}</p>
      </div>
    </div>
  )
}

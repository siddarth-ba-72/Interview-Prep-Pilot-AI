import type { ActionUsage, Usage } from '../api/usage'
import { formatAvailableAt, isLocked } from '../api/usage'

interface UsageSummaryProps {
  usage: Usage
  topicCount: number
}

export default function UsageSummary({ usage, topicCount }: UsageSummaryProps) {
  const topicLimit = usage.topics.limit
  return (
    <section aria-label="Usage limits" className="flex flex-col gap-2">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {topicLimit !== null && (
          <Tile
            label="Topics"
            value={`${topicCount} / ${topicLimit}`}
            hint={topicCount >= topicLimit ? 'Delete one to add another' : `${topicLimit - topicCount} more allowed`}
            exhausted={topicCount >= topicLimit}
          />
        )}
        <ActionTile label="Learn messages" usage={usage.learnMessages} />
        <ActionTile label="Tests" usage={usage.tests} />
        <ActionTile label="Mock interviews" usage={usage.mockInterviews} />
      </div>
      <p className="text-xs text-muted">
        Once you use up a limit, it comes back in full {usage.windowHours} hours after your last use.
      </p>
    </section>
  )
}

function ActionTile({ label, usage }: { label: string; usage: ActionUsage }) {
  const locked = isLocked(usage)
  const hint = !locked
    ? `of ${usage.limit} left`
    : usage.availableAt
      ? `Back ${formatAvailableAt(usage.availableAt)}`
      : 'Not available'
  return <Tile label={label} value={locked ? '0' : String(usage.remaining)} hint={hint} exhausted={locked} />
}

function Tile({ label, value, hint, exhausted }: { label: string; value: string; hint: string; exhausted: boolean }) {
  return (
    <div
      className={`rounded-xl border px-4 py-3 ${
        exhausted ? 'border-danger/30 bg-danger-subtle' : 'border-border bg-surface'
      }`}
    >
      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">{label}</p>
      <p className={`mt-1 text-lg font-extrabold leading-none ${exhausted ? 'text-danger-fg' : 'text-fg'}`}>{value}</p>
      <p className={`mt-1 text-xs ${exhausted ? 'text-danger-fg' : 'text-muted'}`}>{hint}</p>
    </div>
  )
}

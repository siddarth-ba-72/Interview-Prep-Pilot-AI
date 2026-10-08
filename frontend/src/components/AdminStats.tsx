import type { SessionCounts } from '../api/admin'

/** A headline number for the admin overview, e.g. total users. */
export function StatTile({ label, value, detail }: { label: string; value: number | undefined; detail?: string }) {
  return (
    <div className="rounded-xl border border-border bg-surface px-4 py-3">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-1 text-2xl font-extrabold leading-none tabular-nums text-fg">{value ?? '…'}</p>
      {detail && <p className="mt-1.5 text-xs text-muted">{detail}</p>}
    </div>
  )
}

/** Tests or interviews as one tile: all sessions, split into active and completed. */
export function SessionTile({ label, counts }: { label: string; counts: SessionCounts | undefined }) {
  return (
    <StatTile
      label={label}
      value={counts ? counts.active + counts.completed : undefined}
      detail={counts ? `${counts.active} active · ${counts.completed} completed` : undefined}
    />
  )
}

/** Two-line table cell: completed, then active (highlighted while any are running). */
export function SessionCountsText({ counts }: { counts: SessionCounts | undefined }) {
  if (!counts) return <span className="text-muted">…</span>
  return (
    <div className="tabular-nums">
      <div className="font-semibold text-fg">{counts.completed} completed</div>
      <div className={`text-xs ${counts.active > 0 ? 'font-semibold text-primary' : 'text-muted'}`}>
        {counts.active} active
      </div>
    </div>
  )
}

import type { SessionCounts } from '../api/admin'

export type Kpi = { label: string; value: number | undefined; detail?: string }

/** Headline counts as one container split by rules: label over value, no tiles, no icons. */
export function KpiStrip({ items }: { items: Kpi[] }) {
  const columns = items.length === 4 ? 'sm:grid-cols-4' : items.length === 3 ? 'sm:grid-cols-3' : 'sm:grid-cols-2'
  return (
    <dl className={`grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-line bg-line ${columns}`}>
      {items.map((item, index) => (
        <div
          key={item.label}
          className={`bg-sheet px-5 py-4 ${items.length % 2 === 1 && index === items.length - 1 ? 'max-sm:col-span-2' : ''}`}
        >
          <dt className="type-label">{item.label}</dt>
          <dd className="figures mt-1 text-2xl font-medium tracking-[-0.01em] text-ink">
            {item.value !== undefined ? item.value.toLocaleString() : <span className="text-pencil">–</span>}
          </dd>
          {item.detail && <dd className="figures type-meta mt-0.5">{item.detail}</dd>}
        </div>
      ))}
    </dl>
  )
}

export function sessionKpi(label: string, counts: SessionCounts | undefined): Kpi {
  return {
    label,
    value: counts ? counts.active + counts.completed : undefined,
    detail: counts ? `${counts.completed.toLocaleString()} completed · ${counts.active.toLocaleString()} active` : undefined,
  }
}

/** Two-line numeric cell: completed, then active below it in grey. */
export function SessionCountsText({ counts }: { counts: SessionCounts | undefined }) {
  if (!counts) return <span className="text-pencil">–</span>
  return (
    <div className="figures text-right">
      <div className="text-ink">{counts.completed.toLocaleString()}</div>
      <div className="type-meta">{counts.active.toLocaleString()} active</div>
    </div>
  )
}

import type { ReactNode } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'

/** "21–40 of 57" with previous / next buttons, for a zero-based page of `size` items. */
export default function Pager({
  page,
  size,
  shown,
  total,
  onPage,
}: {
  page: number
  size: number
  /** Items on the current page. */
  shown: number
  total: number
  onPage: (page: number) => void
}) {
  const first = total > 0 ? page * size + 1 : 0
  const last = page * size + shown

  return (
    <div className="flex items-center justify-between gap-3">
      <p className="text-sm text-muted tabular-nums">
        {first}–{last} of {total}
      </p>
      <div className="flex gap-2">
        <PageButton label="Previous" disabled={page === 0} onClick={() => onPage(page - 1)}>
          <ChevronLeft size={16} />
        </PageButton>
        <PageButton label="Next" disabled={last >= total} onClick={() => onPage(page + 1)}>
          <ChevronRight size={16} />
        </PageButton>
      </div>
    </div>
  )
}

function PageButton({
  label,
  disabled,
  onClick,
  children,
}: {
  label: string
  disabled: boolean
  onClick: () => void
  children: ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border text-fg transition-colors hover:bg-surface-hover disabled:cursor-not-allowed disabled:opacity-40"
    >
      {children}
    </button>
  )
}

import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from './ui/Button'

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
      <p className="figures text-sm text-graphite">
        {first}–{last} of {total.toLocaleString()}
      </p>
      <div className="flex gap-1.5">
        <Button size="sm" aria-label="Previous" disabled={page === 0} onClick={() => onPage(page - 1)} className="w-8 px-0">
          <ChevronLeft size={16} />
        </Button>
        <Button size="sm" aria-label="Next" disabled={last >= total} onClick={() => onPage(page + 1)} className="w-8 px-0">
          <ChevronRight size={16} />
        </Button>
      </div>
    </div>
  )
}

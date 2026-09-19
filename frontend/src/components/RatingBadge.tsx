import { AlertTriangle, CheckCircle2, CircleDot } from 'lucide-react'
import type { Rating } from '../api/interviews'

const RATING_STYLES: Record<Rating, { label: string; className: string; Icon: typeof CheckCircle2 }> = {
  STRONG: {
    label: 'Strong',
    className: 'border-success/30 bg-success-subtle text-success-fg',
    Icon: CheckCircle2,
  },
  SATISFACTORY: {
    label: 'Satisfactory',
    className: 'border-warning/30 bg-warning-subtle text-warning-fg',
    Icon: CircleDot,
  },
  WEAK: {
    label: 'Needs work',
    className: 'border-danger/30 bg-danger-subtle text-danger-fg',
    Icon: AlertTriangle,
  },
}

export default function RatingBadge({ rating, size = 'md' }: { rating: Rating | null; size?: 'sm' | 'md' }) {
  if (!rating || !RATING_STYLES[rating]) {
    return (
      <span className="inline-flex items-center rounded-full border border-border px-2.5 py-1 text-xs font-semibold text-muted">
        Unrated
      </span>
    )
  }

  const { label, className, Icon } = RATING_STYLES[rating]
  const sizing = size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs'

  return (
    <span className={`inline-flex shrink-0 items-center gap-1.5 rounded-full border font-semibold ${sizing} ${className}`}>
      <Icon size={size === 'sm' ? 12 : 14} />
      {label}
    </span>
  )
}

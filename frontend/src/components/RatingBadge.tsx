import type { Rating } from '../api/interviews'
import StatusPill, { type PillTone } from './ui/StatusPill'

const RATINGS: Record<Rating, { label: string; tone: PillTone }> = {
  STRONG: { label: 'Strong', tone: 'positive' },
  SATISFACTORY: { label: 'Satisfactory', tone: 'warning' },
  WEAK: { label: 'Needs work', tone: 'negative' },
}

/** The interview rubric's verdict on one answer. The label text is exact: tests read it. */
export default function RatingBadge({ rating }: { rating: Rating | null }) {
  const entry = rating ? RATINGS[rating] : undefined
  if (!entry) return <StatusPill tone="neutral">Unrated</StatusPill>
  return <StatusPill tone={entry.tone}>{entry.label}</StatusPill>
}

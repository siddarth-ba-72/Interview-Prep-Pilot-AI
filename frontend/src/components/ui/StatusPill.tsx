import type { ReactNode } from 'react'

export type PillTone = 'positive' | 'negative' | 'warning' | 'neutral' | 'accent'

const TONES: Record<PillTone, string> = {
  positive: 'bg-tick-wash text-tick-ink',
  negative: 'bg-redpen-wash text-redpen-ink',
  warning: 'bg-marker-wash text-marker',
  neutral: 'bg-press text-graphite',
  accent: 'bg-ballpoint-wash text-ballpoint',
}

/** A pale tint with dark text of the same hue. Sits inside rows or beside a value, never above a heading. */
export default function StatusPill({ tone, children }: { tone: PillTone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex h-5 flex-none items-center whitespace-nowrap rounded-full px-2 text-xs font-medium ${TONES[tone]}`}
    >
      {children}
    </span>
  )
}

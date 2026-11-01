import type { ReactNode } from 'react'
import { AlertCircle, Info } from 'lucide-react'

const TONES = {
  error: 'border-redpen/25 bg-redpen-wash text-redpen-ink',
  warning: 'border-marker-line bg-marker-wash text-marker',
  info: 'border-line bg-sheet text-graphite',
}

/**
 * One sentence about what happened, inside the block it concerns. Errors are announced to screen
 * readers; the end-to-end tests also look for them by role.
 */
export default function Notice({
  tone = 'error',
  children,
  action,
  className = '',
}: {
  tone?: keyof typeof TONES
  children: ReactNode
  action?: ReactNode
  className?: string
}) {
  const Icon = tone === 'error' ? AlertCircle : Info
  return (
    <div
      role={tone === 'error' ? 'alert' : undefined}
      className={`flex items-start gap-2.5 rounded-md border px-3 py-2.5 text-sm ${TONES[tone]} ${className}`}
    >
      <Icon size={16} aria-hidden className="mt-0.5 shrink-0" />
      <div className="min-w-0 flex-1 text-pretty">{children}</div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  )
}

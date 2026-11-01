import type { ReactNode } from 'react'

/** An empty block keeps its frame: one sentence, and the next step where the data will appear. */
export default function EmptyState({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-start gap-3 rounded-lg border border-dashed border-edge px-5 py-6 sm:flex-row sm:items-center sm:justify-between">
      <p className="type-body text-graphite">{children}</p>
      {action}
    </div>
  )
}

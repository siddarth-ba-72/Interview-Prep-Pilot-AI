/**
 * PrepPilot's mark is its own score bar: a track, a filled part, and the pass-mark tick it clears.
 * Keep public/favicon.svg in step with it.
 */
export default function BrandMark({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden className="shrink-0">
      <rect x="1" y="9" width="22" height="6" rx="3" className="fill-edge" />
      <rect x="1" y="9" width="16" height="6" rx="3" className="fill-ballpoint" />
      <rect x="13.5" y="3.5" width="2" height="17" rx="1" className="fill-ink" />
    </svg>
  )
}

export function Wordmark() {
  return (
    <span className="flex items-center gap-2">
      <BrandMark />
      <span className="text-[15px] font-semibold tracking-[-0.01em] text-ink">PrepPilot</span>
    </span>
  )
}

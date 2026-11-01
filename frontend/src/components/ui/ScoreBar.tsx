/**
 * The bar: a score drawn against its pass mark. The filled part is the score at its true ratio in
 * the one data hue; the ink tick is the pass mark, so "did I clear it?" is seen before it is read.
 * Negative test scores draw an empty track. Decorative: the figures are always written beside it.
 */
export default function ScoreBar({
  score,
  max,
  pass,
  size = 'sm',
  className = '',
}: {
  score: number
  max: number
  pass: number
  size?: 'sm' | 'md'
  className?: string
}) {
  const ratio = max > 0 ? Math.min(1, Math.max(0, score / max)) : 0
  const passRatio = max > 0 ? Math.min(1, Math.max(0, pass / max)) : 0
  const track = size === 'md' ? 'h-2' : 'h-1.5'

  return (
    <div aria-hidden className={`relative ${className}`}>
      <div className={`${track} overflow-hidden rounded-full bg-press`}>
        <div className="animate-fill-in h-full rounded-full bg-ballpoint" style={{ width: `${ratio * 100}%` }} />
      </div>
      <span
        className="absolute -bottom-1 -top-1 w-px bg-ink"
        style={{ left: `calc(${passRatio * 100}% - 0.5px)` }}
      />
    </div>
  )
}

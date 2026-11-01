import { useEffect, useRef, useState } from 'react'
import RatingBadge from '../RatingBadge'
import ScoreBar from '../ui/ScoreBar'
import { LEARN_PROMPTS } from '../../features/howItWorks/content'
import { useInView, usePrefersReducedMotion } from '../../features/howItWorks/hooks'

/** A message box that types out example questions for the tutor, one after another. */
export function LearnPrompts() {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref)
  const reducedMotion = usePrefersReducedMotion()
  const [index, setIndex] = useState(0)
  const [typed, setTyped] = useState(0)
  const [deleting, setDeleting] = useState(false)
  const prompt = LEARN_PROMPTS[index]

  useEffect(() => {
    if (reducedMotion || !inView) return
    const full = typed === prompt.length
    const empty = typed === 0
    const delay = !deleting && full ? 1900 : deleting && empty ? 350 : deleting ? 14 : 38
    const timer = setTimeout(() => {
      if (!deleting && full) setDeleting(true)
      else if (deleting && empty) {
        setDeleting(false)
        setIndex((current) => (current + 1) % LEARN_PROMPTS.length)
      } else setTyped((current) => current + (deleting ? -1 : 1))
    }, delay)
    return () => clearTimeout(timer)
  }, [reducedMotion, inView, deleting, typed, prompt.length])

  return (
    <div ref={ref} className="max-w-3xl">
      <h3 className="type-section">Not sure what to ask? Try something like</h3>
      <div className="mt-3 flex items-center gap-3 rounded-md border border-edge bg-sheet py-2 pl-4 pr-2" aria-hidden>
        <span className="min-h-5 min-w-0 flex-1 truncate text-[15px] text-ink">
          {reducedMotion ? prompt : prompt.slice(0, typed)}
          <span className="animate-caret ml-0.5 inline-block h-4 w-0.5 translate-y-0.5 bg-ballpoint" />
        </span>
        <span className="inline-flex h-8 shrink-0 items-center rounded-md bg-action px-3 text-[13px] font-medium text-action-ink">Send</span>
      </div>
      <ul className="sr-only">
        {LEARN_PROMPTS.map((p) => (
          <li key={p}>{p}</li>
        ))}
      </ul>
    </div>
  )
}

const SCORING = [
  { label: 'Multiple choice, right', value: '+1' },
  { label: 'Multiple choice, wrong', value: '−1' },
  { label: 'Written answer, right', value: '+5' },
  { label: 'Written answer, wrong', value: '−5' },
  { label: 'Left blank', value: '0' },
]

/** The test's marking scheme, and the bar it adds up to. */
export function TestScoring() {
  return (
    <div className="grid gap-8 rounded-lg border border-line bg-sheet p-6 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] md:gap-12">
      <div>
        <h3 className="type-section">How a test is marked</h3>
        <table className="mt-3 w-full text-sm">
          <tbody>
            {SCORING.map((row) => (
              <tr key={row.label} className="border-b border-rule last:border-b-0">
                <td className="py-2 text-graphite">{row.label}</td>
                <td className="figures py-2 text-right font-medium text-ink">{row.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex flex-col justify-center">
        <p className="figures text-[40px] font-semibold leading-none tracking-[-0.02em] text-ink">
          36<span className="text-xl font-normal text-graphite"> of 60 to pass</span>
        </p>
        <ScoreBar score={42} max={60} pass={36} size="md" className="mt-5" />
        <p className="type-meta mt-2.5">The tick on every bar in the app is the pass mark. This one shows a 42.</p>
      </div>
    </div>
  )
}

const RATINGS = [
  { rating: 'STRONG' as const, points: 100, text: 'A clear, complete answer an interviewer would be happy with.' },
  { rating: 'SATISFACTORY' as const, points: 60, text: 'On the right track, but missing some depth or detail.' },
  { rating: 'WEAK' as const, points: 20, text: 'Vague or off the point. The feedback shows what to add.' },
]

/** The interview rubric, with the points each rating is worth. */
export function InterviewRatings() {
  return (
    <div className="rounded-lg border border-line bg-sheet p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="type-section">How each answer is rated</h3>
        <p className="type-meta">Your score is the average over your answers. 75 of 100 passes.</p>
      </div>
      <ul className="mt-3">
        {RATINGS.map(({ rating, points, text }) => (
          <li key={rating} className="grid grid-cols-[7.5rem_minmax(0,1fr)_auto] items-baseline gap-4 border-b border-rule py-3 last:border-b-0">
            <span>
              <RatingBadge rating={rating} />
            </span>
            <span className="type-body text-ink">{text}</span>
            <span className="figures text-sm text-graphite">{points} points</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

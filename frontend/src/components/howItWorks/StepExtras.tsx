import { useEffect, useRef, useState } from 'react'
import { Send, Target } from 'lucide-react'
import RatingBadge from '../RatingBadge'
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
    <div ref={ref} className="rounded-2xl border border-border bg-surface p-5 sm:p-6">
      <p className="text-xs font-bold uppercase tracking-[0.14em] text-muted">Not sure what to ask? Try something like</p>
      <div className="mt-3 flex items-center gap-3 rounded-xl border border-border bg-bg py-2 pl-4 pr-2" aria-hidden>
        <span className="min-h-5 min-w-0 flex-1 truncate text-sm text-fg">
          {reducedMotion ? prompt : prompt.slice(0, typed)}
          <span className="animate-caret ml-0.5 inline-block h-4 w-0.5 translate-y-0.5 bg-primary" />
        </span>
        <span className="inline-flex h-9 shrink-0 items-center gap-1.5 rounded-lg bg-primary px-3.5 text-xs font-bold text-primary-fg">
          <Send size={13} />
          Send
        </span>
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
  { label: 'Multiple choice', value: '+1 / −1', hint: 'right / wrong' },
  { label: 'Written answer', value: '+5 / −5', hint: 'right / wrong' },
  { label: 'Left blank', value: '0', hint: 'no penalty' },
  { label: 'Pass mark', value: '36 / 60', hint: 'out of a possible 60' },
]

export function TestScoring() {
  return (
    <div className="rounded-2xl border border-border bg-surface p-5 sm:p-6">
      <div className="flex items-center gap-2">
        <Target size={16} className="text-primary" aria-hidden />
        <h3 className="text-sm font-bold text-fg">How a test is scored</h3>
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {SCORING.map((item) => (
          <div key={item.label} className="rounded-xl border border-border bg-bg px-4 py-3">
            <dt className="text-[11px] font-semibold uppercase tracking-wide text-muted">{item.label}</dt>
            <dd className="mt-1">
              <span className="block text-xl font-extrabold text-fg">{item.value}</span>
              <span className="text-xs text-muted">{item.hint}</span>
            </dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

const RATINGS = [
  { rating: 'STRONG' as const, text: 'A clear, complete answer an interviewer would be happy with.' },
  { rating: 'SATISFACTORY' as const, text: 'On the right track, but missing some depth or detail.' },
  { rating: 'WEAK' as const, text: 'Vague or off the point. The feedback shows what to add.' },
]

export function InterviewRatings() {
  return (
    <div className="grid gap-4 rounded-2xl border border-border bg-surface p-5 sm:p-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,1fr)] lg:items-center">
      <div>
        <h3 className="text-sm font-bold text-fg">How each answer is rated</h3>
        <ul className="mt-4 grid gap-3 sm:grid-cols-3">
          {RATINGS.map(({ rating, text }) => (
            <li key={rating} className="rounded-xl border border-border bg-bg px-4 py-3">
              <RatingBadge rating={rating} size="sm" />
              <p className="mt-2 text-xs leading-relaxed text-muted">{text}</p>
            </li>
          ))}
        </ul>
      </div>
      <div className="flex items-center gap-4 rounded-xl bg-primary-subtle px-4 py-4 lg:flex-col lg:items-start lg:gap-1">
        <span className="text-3xl font-black text-primary">75</span>
        <p className="text-xs leading-relaxed text-fg">
          <span className="font-bold">out of 100 to pass.</span> Your score is the average across all your answers.
        </p>
      </div>
    </div>
  )
}

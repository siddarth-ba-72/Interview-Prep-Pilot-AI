import { useEffect, useRef, useState, type ReactNode } from 'react'
import { BookOpen, ClipboardCheck, FolderOpen, Mic, Sparkles, Trophy } from 'lucide-react'
import { usePrefersReducedMotion } from '../../features/howItWorks/hooks'

const TAGLINES = [
  'Pick a topic and make today count.',
  'Small daily reps beat last-minute cramming.',
  'Learn it, test it, then ace the interview.',
  'Every mock interview makes the real one easier.',
]

interface DashboardHeroProps {
  displayName?: string | null
  topicCount: number
  testCount: number
  /** Best average test score across topics, out of 60; null until a test is scored. */
  bestAvgScore: number | null
  children?: ReactNode
}

/** The dashboard's welcome banner: a greeting, headline stats and (as children) the new-topic form. */
export default function DashboardHero({ displayName, topicCount, testCount, bestAvgScore, children }: DashboardHeroProps) {
  const firstName = displayName?.trim().split(/\s+/)[0]

  return (
    <section className="relative overflow-hidden rounded-3xl border border-border bg-surface shadow-sm">
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 [background-image:radial-gradient(var(--border)_1px,transparent_1px)] [background-size:22px_22px] [mask-image:radial-gradient(ellipse_at_top_right,black_20%,transparent_70%)]" />
        <div className="animate-float absolute -left-24 -top-32 h-80 w-80 rounded-full bg-primary/20 blur-3xl" />
        <div className="animate-float absolute -bottom-40 right-0 h-96 w-96 rounded-full bg-accent/20 blur-3xl [animation-delay:-3.5s]" />
      </div>

      <div className="relative grid gap-8 p-6 sm:p-8 lg:grid-cols-[1.4fr_1fr] lg:items-center lg:p-10">
        <div className="animate-rise-in">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-primary/25 bg-primary-subtle px-3 py-1 text-xs font-bold text-primary">
            <Sparkles size={13} />
            {greeting()}
          </span>
          <p className="mt-4 text-3xl font-black leading-tight tracking-tight text-fg sm:text-4xl">
            {firstName ? (
              <>
                Hey <span data-clarity-mask="True">{firstName}</span>{' '}
              </>
            ) : (
              'Welcome back '
            )}
            <span aria-hidden className="animate-wave">
              👋
            </span>
          </p>
          <p className="mt-2 text-base text-muted">
            <RotatingTagline />
          </p>

          <div className="mt-6">{children}</div>
        </div>

        <div className="grid grid-cols-3 gap-3 lg:grid-cols-1" data-clarity-mask="True">
          <Stat icon={<FolderOpen size={18} />} label="Topics" value={topicCount} delay={100} />
          <Stat icon={<ClipboardCheck size={18} />} label="Tests taken" value={testCount} delay={200} />
          <Stat
            icon={<Trophy size={18} />}
            label="Best avg score"
            value={bestAvgScore}
            suffix="/60"
            decimals={1}
            delay={300}
          />
        </div>
      </div>

      <ModeStrip />
    </section>
  )
}

function greeting(): string {
  const hour = new Date().getHours()
  if (hour < 5) return 'Burning the midnight oil'
  if (hour < 12) return 'Good morning'
  if (hour < 17) return 'Good afternoon'
  return 'Good evening'
}

function RotatingTagline() {
  const reducedMotion = usePrefersReducedMotion()
  const [index, setIndex] = useState(0)

  useEffect(() => {
    if (reducedMotion) return
    const timer = setInterval(() => setIndex((current) => (current + 1) % TAGLINES.length), 4500)
    return () => clearInterval(timer)
  }, [reducedMotion])

  return (
    <span key={index} className="animate-word-in inline-block">
      {TAGLINES[index]}
    </span>
  )
}

function Stat({
  icon,
  label,
  value,
  suffix = '',
  decimals = 0,
  delay,
}: {
  icon: ReactNode
  label: string
  value: number | null
  suffix?: string
  decimals?: number
  delay: number
}) {
  const shown = useCountUp(value ?? 0)
  return (
    <div
      style={{ animationDelay: `${delay}ms` }}
      className="animate-rise-in group flex flex-col gap-2 rounded-2xl border border-border bg-surface/80 p-3 backdrop-blur-sm transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-lg hover:shadow-primary/10 sm:p-4 lg:flex-row lg:items-center lg:gap-4"
    >
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-accent text-white shadow-md shadow-primary/30 transition-transform group-hover:scale-110 group-hover:-rotate-6 lg:h-11 lg:w-11">
        {icon}
      </span>
      <div className="min-w-0">
        <p className="text-xl font-black leading-none text-fg sm:text-2xl">
          {value === null ? '—' : shown.toFixed(decimals)}
          {value !== null && suffix && <span className="text-sm font-bold text-muted">{suffix}</span>}
        </p>
        <p className="mt-1 text-[10px] font-semibold uppercase leading-tight tracking-wide text-muted sm:text-[11px]">{label}</p>
      </div>
    </div>
  )
}

/** Animates from the previous value to `target`; jumps straight there when motion is reduced. */
function useCountUp(target: number, duration = 900): number {
  const reducedMotion = usePrefersReducedMotion()
  const [value, setValue] = useState(reducedMotion ? target : 0)
  const current = useRef(value)

  useEffect(() => {
    if (reducedMotion) {
      current.current = target
      setValue(target)
      return
    }
    const from = current.current
    const start = performance.now()
    let frame = requestAnimationFrame(function step(now) {
      const t = Math.min(1, (now - start) / duration)
      current.current = from + (target - from) * (1 - Math.pow(1 - t, 3))
      setValue(current.current)
      if (t < 1) frame = requestAnimationFrame(step)
    })
    return () => cancelAnimationFrame(frame)
  }, [target, duration, reducedMotion])

  return value
}

const MODES = [
  { icon: BookOpen, title: 'Learn', text: 'Chat with an AI tutor that adapts to you' },
  { icon: ClipboardCheck, title: 'Test', text: 'Mixed questions, scored with a full report' },
  { icon: Mic, title: 'Mock Interview', text: 'One question at a time, rated as you go' },
]

function ModeStrip() {
  return (
    <div className="relative grid grid-cols-1 border-t border-border bg-surface-hover/40 sm:grid-cols-3">
      {MODES.map(({ icon: Icon, title, text }, i) => (
        <div
          key={title}
          className={`group flex items-center gap-3 px-6 py-4 transition-colors hover:bg-surface sm:px-8 ${
            i > 0 ? 'border-t border-border sm:border-l sm:border-t-0' : ''
          }`}
        >
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary-subtle text-primary transition-transform group-hover:scale-110">
            <Icon size={16} />
          </span>
          <div className="min-w-0">
            <p className="text-sm font-bold text-fg">{title}</p>
            <p className="text-xs text-muted">{text}</p>
          </div>
        </div>
      ))}
    </div>
  )
}

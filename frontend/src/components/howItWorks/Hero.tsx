import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowDown, ArrowRight, Sparkles } from 'lucide-react'
import { useTheme } from '../../features/theme/ThemeProvider'
import { shotUrl, type ShotName, type Step } from '../../features/howItWorks/content'
import { scrollToSection, usePrefersReducedMotion } from '../../features/howItWorks/hooks'
import RatingBadge from '../RatingBadge'

const TOPIC_EXAMPLES = ['Python', 'DBMS', 'Operating Systems', 'Data Structures', 'Java', 'Computer Networks', 'React']

export default function Hero({ steps, signedIn }: { steps: Step[]; signedIn: boolean }) {
  return (
    <section className="relative overflow-hidden border-b border-border">
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 [background-image:radial-gradient(var(--border)_1px,transparent_1px)] [background-size:22px_22px] [mask-image:radial-gradient(ellipse_at_top,black_30%,transparent_75%)]" />
        <div className="animate-float absolute -left-40 -top-40 h-[28rem] w-[28rem] rounded-full bg-primary/20 blur-3xl" />
        <div className="animate-float absolute -right-32 top-32 h-[30rem] w-[30rem] rounded-full bg-accent/20 blur-3xl [animation-delay:-3.5s]" />
      </div>

      <div className="relative mx-auto grid w-full max-w-6xl items-center gap-12 px-4 pb-10 pt-12 sm:px-6 sm:pt-16 lg:grid-cols-2 lg:px-8 lg:pt-20">
        <div>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-primary/25 bg-primary-subtle px-3 py-1 text-xs font-bold text-primary">
            <Sparkles size={13} />
            Your guide to PrepPilot
          </span>
          <h1 className="mt-5 text-4xl font-black leading-[1.05] tracking-tight text-fg sm:text-5xl lg:text-6xl">
            Learn it. Test it.
            <br />
            <span className="animate-flow bg-gradient-to-r from-primary via-accent to-primary bg-clip-text text-transparent">
              Ace the interview.
            </span>
          </h1>
          <p className="mt-5 max-w-xl text-lg leading-relaxed text-muted">
            PrepPilot is your AI interview coach. This guide walks you through every feature, step by step, with real
            screenshots from the app.
          </p>
          <p className="mt-4 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm font-semibold text-fg">
            Works for any topic, like <RotatingWord words={TOPIC_EXAMPLES} />
          </p>

          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              to={signedIn ? '/dashboard' : '/register'}
              className="group inline-flex h-11 items-center gap-2 rounded-xl bg-primary px-5 text-sm font-bold text-primary-fg shadow-lg shadow-primary/30 transition-colors hover:bg-primary-hover hover:no-underline"
            >
              {signedIn ? 'Go to your dashboard' : 'Create your account'}
              <ArrowRight size={16} className="transition-transform group-hover:translate-x-0.5" />
            </Link>
            <button
              type="button"
              onClick={() => scrollToSection(steps[0].id)}
              className="group inline-flex h-11 items-center gap-2 rounded-xl border border-border bg-surface px-5 text-sm font-bold text-fg transition-colors hover:bg-surface-hover"
            >
              Take the tour
              <ArrowDown size={16} className="transition-transform group-hover:translate-y-0.5" />
            </button>
          </div>
        </div>

        <HeroShowcase />
      </div>

      <Journey steps={steps} />
    </section>
  )
}

function RotatingWord({ words }: { words: string[] }) {
  const reducedMotion = usePrefersReducedMotion()
  const [index, setIndex] = useState(0)

  useEffect(() => {
    if (reducedMotion) return
    const timer = setInterval(() => setIndex((current) => (current + 1) % words.length), 2200)
    return () => clearInterval(timer)
  }, [reducedMotion, words.length])

  return (
    <>
      <span aria-hidden className="inline-flex overflow-hidden rounded-lg">
        <span key={index} className="animate-word-in inline-block rounded-lg bg-primary-subtle px-2.5 py-0.5 text-primary">
          {words[index]}
        </span>
      </span>
      <span className="sr-only">{words.join(', ')}</span>
    </>
  )
}

const SHOWCASE: Array<{ shot: ShotName; position: string; delay: string }> = [
  { shot: 'learn-followup', position: 'left-0 top-6 -rotate-6', delay: '0s' },
  { shot: 'test-report', position: 'right-0 top-0 rotate-3', delay: '-2.3s' },
  { shot: 'interview-report', position: 'bottom-0 left-[16%] -rotate-1', delay: '-4.6s' },
]

/** Three tilted screenshots that float gently; hovering one straightens and lifts it. */
function HeroShowcase() {
  const { theme } = useTheme()
  return (
    <div aria-hidden className="relative mx-auto hidden aspect-[5/4] w-full max-w-xl md:block">
      {SHOWCASE.map(({ shot, position, delay }) => (
        <div key={shot} className={`absolute w-[70%] transition-transform duration-500 hover:z-10 hover:rotate-0 ${position}`}>
          <div className="animate-float" style={{ animationDelay: delay }}>
            <div className="overflow-hidden rounded-xl border border-border bg-surface shadow-2xl shadow-primary/20 transition-transform duration-500 hover:scale-105">
              <div className="flex gap-1 border-b border-border bg-surface-hover/70 px-3 py-1.5">
                <span className="h-2 w-2 rounded-full bg-[#ff5f57]" />
                <span className="h-2 w-2 rounded-full bg-[#febc2e]" />
                <span className="h-2 w-2 rounded-full bg-[#28c840]" />
              </div>
              <img
                src={shotUrl(shot, theme)}
                alt=""
                width={1600}
                height={1000}
                className="aspect-[8/5] w-full object-cover object-top"
              />
            </div>
          </div>
        </div>
      ))}
      <div className="animate-float absolute -left-4 bottom-[30%] z-20 [animation-delay:-1.2s]">
        <div className="rounded-full bg-surface p-1 shadow-xl">
          <RatingBadge rating="STRONG" />
        </div>
      </div>
      <div className="animate-float absolute -right-3 bottom-[12%] z-20 [animation-delay:-3.1s]">
        <div className="flex items-center gap-2 rounded-2xl border border-border bg-surface px-3.5 py-2 shadow-xl">
          <span className="text-lg font-black text-primary">48/60</span>
          <span className="rounded-full bg-success-subtle px-2 py-0.5 text-[11px] font-bold text-success-fg">Passed</span>
        </div>
      </div>
    </div>
  )
}

/** The whole journey at a glance: each step jumps to its section. */
function Journey({ steps }: { steps: Step[] }) {
  return (
    <div className="relative mx-auto w-full max-w-6xl px-4 pb-14 sm:px-6 lg:px-8">
      <ol className="relative grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <span
          aria-hidden
          className="animate-flow absolute left-[8%] right-[8%] top-[2.1rem] hidden h-0.5 rounded-full bg-gradient-to-r from-primary/20 via-accent to-primary/20 lg:block"
        />
        {steps.map((step, i) => {
          const Icon = step.icon
          return (
            <li key={step.id} className="relative h-full">
              <button
                type="button"
                onClick={() => scrollToSection(step.id)}
                className="group flex h-full w-full flex-col items-center rounded-2xl border border-border bg-surface/80 px-3 py-4 text-center backdrop-blur-sm transition-all hover:-translate-y-1 hover:border-primary/40 hover:shadow-lg hover:shadow-primary/10"
              >
                <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-accent text-white shadow-md shadow-primary/30 transition-transform group-hover:scale-110">
                  <Icon size={17} />
                </span>
                <span className="mt-2.5 text-[11px] font-bold uppercase tracking-wider text-muted">Step {i + 1}</span>
                <span className="text-sm font-bold text-fg">{step.nav}</span>
                <span className="mt-0.5 text-xs leading-snug text-muted">{step.summary}</span>
              </button>
            </li>
          )
        })}
      </ol>
    </div>
  )
}

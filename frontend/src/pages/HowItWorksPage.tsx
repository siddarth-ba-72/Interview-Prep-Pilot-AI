import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  ArrowRight,
  ChevronDown,
  CircleHelp,
  ClipboardCheck,
  LayoutDashboard,
  MessagesSquare,
  Mic,
  Repeat,
} from 'lucide-react'
import { useAppSelector } from '../hooks'
import AppHeader from '../components/AppHeader'
import Hero from '../components/howItWorks/Hero'
import LimitsExplorer from '../components/howItWorks/LimitsExplorer'
import Lightbox from '../components/howItWorks/Lightbox'
import Reveal from '../components/howItWorks/Reveal'
import StepNav, { type NavItem } from '../components/howItWorks/StepNav'
import StepSection from '../components/howItWorks/StepSection'
import { InterviewRatings, LearnPrompts, TestScoring } from '../components/howItWorks/StepExtras'
import { FAQS, LIMITS_STEP, STEPS, type Scene } from '../features/howItWorks/content'
import { useActiveSection, useInView, usePrefersReducedMotion, useScrollProgress } from '../features/howItWorks/hooks'

const GUIDE = [...STEPS, LIMITS_STEP]

const NAV_ITEMS: NavItem[] = [
  ...GUIDE.map((step) => ({ id: step.id, label: step.nav, icon: step.icon })),
  { id: 'faq', label: 'FAQ', icon: CircleHelp },
]

const STEP_EXTRAS: Record<string, JSX.Element> = {
  learn: <LearnPrompts />,
  test: <TestScoring />,
  interview: <InterviewRatings />,
}

/**
 * A public, static walkthrough of PrepPilot for new users: every step from sign-up to mock interviews,
 * with real screenshots (light and dark) and the daily limits. It makes no API calls.
 */
export default function HowItWorksPage() {
  const { accessToken, status } = useAppSelector((state) => state.auth)
  const signedIn = Boolean(accessToken)
  const navigate = useNavigate()
  const guideRef = useRef<HTMLDivElement>(null)
  const active = useActiveSection(NAV_ITEMS.map((item) => item.id))
  const progress = useScrollProgress(guideRef)
  const [lightbox, setLightbox] = useState<{ scenes: Scene[]; index: number } | null>(null)

  const openLightbox = useCallback((scenes: Scene[], index: number) => setLightbox({ scenes, index }), [])
  const closeLightbox = useCallback(() => setLightbox(null), [])
  const showScene = useCallback(
    (index: number) => setLightbox((current) => (current ? { ...current, index } : current)),
    []
  )

  const headerActions =
    status === 'loading' ? null : signedIn ? (
      <button
        type="button"
        onClick={() => navigate('/dashboard')}
        className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border px-3 text-sm font-semibold text-muted transition-colors hover:bg-surface-hover hover:text-fg"
      >
        <LayoutDashboard size={15} />
        <span className="hidden sm:inline">Dashboard</span>
      </button>
    ) : (
      <>
        <Link
          to="/login"
          className="inline-flex h-9 items-center rounded-lg px-3 text-sm font-semibold text-muted transition-colors hover:bg-surface-hover hover:text-fg hover:no-underline"
        >
          Sign in
        </Link>
        <Link
          to="/register"
          className="hidden h-9 items-center rounded-lg bg-primary px-3.5 text-sm font-bold text-primary-fg transition-colors hover:bg-primary-hover hover:no-underline sm:inline-flex"
        >
          Create account
        </Link>
      </>
    )

  return (
    <div className="min-h-screen bg-bg">
      <AppHeader title="How it works" actions={headerActions} />

      <Hero steps={GUIDE} signedIn={signedIn} />

      <div ref={guideRef} className="relative">
        <StepNav items={NAV_ITEMS} active={active} progress={progress} />

        <div className="mx-auto flex w-full max-w-6xl flex-col gap-24 px-4 py-16 sm:gap-32 sm:px-6 sm:py-24 lg:px-8">
          {STEPS.map((step, i) => (
            <StepSection
              key={step.id}
              step={step}
              number={i + 1}
              reverse={i % 2 === 1}
              onOpen={openLightbox}
              extra={STEP_EXTRAS[step.id]}
            />
          ))}

          <StudyLoop />

          <StepSection
            step={LIMITS_STEP}
            number={GUIDE.length}
            reverse
            onOpen={openLightbox}
            extra={<LimitsExplorer />}
            extraFirst
          />

          <Faq />
        </div>
      </div>

      <FinalCta signedIn={signedIn} />

      {lightbox && (
        <Lightbox scenes={lightbox.scenes} index={lightbox.index} onIndexChange={showScene} onClose={closeLightbox} />
      )}
    </div>
  )
}

const LOOP = [
  { icon: MessagesSquare, title: 'Learn', body: 'Build your understanding with the tutor.' },
  { icon: ClipboardCheck, title: 'Test', body: 'Find your gaps with a 20-question test.' },
  { icon: Mic, title: 'Interview', body: 'Practise answering against the clock.' },
  { icon: Repeat, title: 'Revisit', body: 'Study your weak areas, then go again.' },
]

/** The recommended cycle through the three modes; the highlight walks around it while on screen. */
function StudyLoop() {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref)
  const reducedMotion = usePrefersReducedMotion()
  const [current, setCurrent] = useState(0)

  useEffect(() => {
    if (!inView || reducedMotion) return
    const timer = setInterval(() => setCurrent((i) => (i + 1) % LOOP.length), 1600)
    return () => clearInterval(timer)
  }, [inView, reducedMotion])

  return (
    <section aria-labelledby="loop-title">
      <Reveal>
        <div ref={ref} className="relative overflow-hidden rounded-3xl border border-border bg-surface p-6 sm:p-10">
          <div
            aria-hidden
            className="pointer-events-none absolute -right-20 -top-20 h-72 w-72 rounded-full bg-gradient-to-br from-primary/20 to-accent/20 blur-3xl"
          />
          <p className="relative text-xs font-bold uppercase tracking-[0.18em] text-primary">Put it all together</p>
          <h2 id="loop-title" className="relative mt-1.5 text-2xl font-extrabold tracking-tight text-fg sm:text-3xl">
            Your study loop
          </h2>
          <p className="relative mt-2 max-w-2xl text-base leading-relaxed text-muted">
            The fastest way to improve is a simple cycle. Repeat it for each topic until the interview feels easy.
          </p>

          <ol className="relative mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {LOOP.map(({ icon: Icon, title, body }, i) => {
              const lit = !reducedMotion && i === current
              return (
                <li
                  key={title}
                  className={`relative rounded-2xl border p-5 transition-all duration-500 ${
                    lit
                      ? '-translate-y-1 border-primary/50 bg-primary-subtle shadow-lg shadow-primary/15'
                      : 'border-border bg-bg'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span
                      className={`flex h-10 w-10 items-center justify-center rounded-xl transition-colors duration-500 ${
                        lit ? 'bg-primary text-primary-fg' : 'bg-surface-hover text-primary'
                      }`}
                    >
                      <Icon size={19} />
                    </span>
                    <span className="text-2xl font-black text-border">0{i + 1}</span>
                  </div>
                  <h3 className="mt-4 text-base font-bold text-fg">{title}</h3>
                  <p className="mt-1 text-sm leading-relaxed text-muted">{body}</p>
                  {i < LOOP.length - 1 && (
                    <ArrowRight
                      size={18}
                      aria-hidden
                      className="absolute -right-[1.05rem] top-1/2 z-10 hidden -translate-y-1/2 text-primary lg:block"
                    />
                  )}
                </li>
              )
            })}
          </ol>
        </div>
      </Reveal>
    </section>
  )
}

function Faq() {
  return (
    <section id="faq" aria-labelledby="faq-title" className="scroll-mt-32">
      <Reveal>
        <div className="flex items-start gap-4 sm:gap-5">
          <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-accent text-white shadow-lg shadow-primary/30 sm:h-14 sm:w-14">
            <CircleHelp size={24} />
          </span>
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary">FAQ</p>
            <h2 id="faq-title" className="mt-1.5 text-2xl font-extrabold tracking-tight text-fg sm:text-3xl">
              Questions students often ask
            </h2>
          </div>
        </div>
      </Reveal>
      <div className="mt-8 grid items-start gap-3 lg:grid-cols-2">
        {FAQS.map(({ q, a }, i) => (
          <Reveal key={q} delay={(i % 2) * 80}>
            <details className="group rounded-2xl border border-border bg-surface px-5 py-4 transition-colors open:border-primary/30 [&_summary::-webkit-details-marker]:hidden">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-sm font-bold text-fg">
                {q}
                <ChevronDown size={18} className="shrink-0 text-muted transition-transform duration-300 group-open:rotate-180" />
              </summary>
              <p className="mt-3 text-sm leading-relaxed text-muted">{a}</p>
            </details>
          </Reveal>
        ))}
      </div>
    </section>
  )
}

function FinalCta({ signedIn }: { signedIn: boolean }) {
  return (
    <section className="mx-auto w-full max-w-6xl px-4 pb-20 sm:px-6 lg:px-8">
      <Reveal>
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-primary via-primary to-accent px-6 py-12 text-center sm:px-12 sm:py-16">
          <div className="pointer-events-none absolute -left-24 -top-24 h-72 w-72 rounded-full bg-white/10 blur-3xl" />
          <div className="pointer-events-none absolute bottom-0 right-0 h-96 w-96 translate-x-1/3 translate-y-1/3 rounded-full bg-black/10 blur-3xl" />
          <div className="pointer-events-none absolute inset-0 [background-image:radial-gradient(rgba(255,255,255,0.16)_1px,transparent_1px)] [background-size:22px_22px]" />
          <h2 className="relative text-3xl font-extrabold tracking-tight text-white sm:text-4xl">Ready to start preparing?</h2>
          <p className="relative mx-auto mt-3 max-w-xl text-base text-white/80">
            Add your first topic and start your first lesson in under two minutes.
          </p>
          <div className="relative mt-8 flex flex-wrap justify-center gap-3">
            <Link
              to={signedIn ? '/dashboard' : '/register'}
              className="group inline-flex h-11 items-center gap-2 rounded-xl bg-white px-6 text-sm font-bold text-primary shadow-lg transition-transform hover:-translate-y-0.5 hover:no-underline"
            >
              {signedIn ? 'Go to your dashboard' : 'Create your account'}
              <ArrowRight size={16} className="transition-transform group-hover:translate-x-0.5" />
            </Link>
            {!signedIn && (
              <Link
                to="/login"
                className="inline-flex h-11 items-center rounded-xl border border-white/30 px-6 text-sm font-bold text-white transition-colors hover:bg-white/10 hover:no-underline"
              >
                I already have an account
              </Link>
            )}
          </div>
        </div>
      </Reveal>
    </section>
  )
}

import { useCallback, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronDown } from 'lucide-react'
import { useAppSelector } from '../hooks'
import AppHeader from '../components/AppHeader'
import PrepTrackExplorer from '../components/PrepTrackExplorer'
import Hero from '../components/howItWorks/Hero'
import Lightbox from '../components/howItWorks/Lightbox'
import Reveal from '../components/howItWorks/Reveal'
import StepNav, { type NavItem } from '../components/howItWorks/StepNav'
import StepSection from '../components/howItWorks/StepSection'
import { InterviewRatings, LearnPrompts, TestScoring } from '../components/howItWorks/StepExtras'
import { buttonClass } from '../components/ui/Button'
import { FAQS, STEPS, type Scene } from '../features/howItWorks/content'
import { trackFor } from '../features/prepTrack/tracks'
import { useActiveSection, useScrollProgress } from '../features/howItWorks/hooks'

const NAV_ITEMS: NavItem[] = [
  ...STEPS.map((step) => ({ id: step.id, label: step.nav })),
  { id: 'loop', label: 'The loop' },
  { id: 'faq', label: 'Questions' },
]

const STEP_EXTRAS: Record<string, JSX.Element> = {
  learn: <LearnPrompts />,
  test: <TestScoring />,
  interview: <InterviewRatings />,
}

/**
 * A public, static walkthrough of PrepPilot for new users: every step from sign-up to mock interviews,
 * with real screenshots (light and dark) and how the experience answer shapes each mode. It makes no API calls.
 */
export default function HowItWorksPage() {
  const { accessToken, user } = useAppSelector((state) => state.auth)
  const signedIn = Boolean(accessToken)
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

  return (
    <div className="min-h-screen">
      <AppHeader />

      <Hero steps={STEPS} signedIn={signedIn} />

      <div ref={guideRef}>
        <StepNav items={NAV_ITEMS} active={active} progress={progress} />

        <div className="mx-auto flex w-full max-w-[1200px] flex-col gap-28 px-4 py-20 sm:px-6 lg:gap-40 lg:px-8 lg:py-28">
          {STEPS.map((step, i) => (
            <StepSection
              key={step.id}
              step={step}
              reverse={i % 2 === 1}
              onOpen={openLightbox}
              extra={
                step.id === 'get-started' ? (
                  <PrepTrackExplorer wide current={user?.experienceLevel ? trackFor(user.experienceLevel) : undefined} />
                ) : (
                  STEP_EXTRAS[step.id]
                )
              }
            />
          ))}
        </div>

        <StudyLoop />

        <div className="mx-auto w-full max-w-[1200px] px-4 py-20 sm:px-6 lg:px-8 lg:py-28">
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
  { title: 'Learn', body: 'Build the understanding with the tutor, at your level.' },
  { title: 'Test', body: 'Twenty questions show where you stand against the pass mark.' },
  { title: 'Mock interview', body: 'Answer against the clock, one question at a time.' },
  { title: 'Revisit', body: 'Study the weak areas the reports name, then go round again.' },
]

/** The recommended cycle through the three modes, on a field of its own. */
function StudyLoop() {
  return (
    <section id="loop" aria-labelledby="loop-title" className="scroll-mt-28 border-y border-line bg-wash">
      <div className="mx-auto w-full max-w-[1200px] px-4 py-20 sm:px-6 lg:px-8 lg:py-24">
        <Reveal>
          <h2 id="loop-title" className="max-w-2xl text-[28px] font-semibold leading-[1.15] tracking-[-0.018em] text-ink text-balance sm:text-[32px]">
            Go round the loop until the interview feels easy.
          </h2>
        </Reveal>
        <Reveal>
          <ol className="mt-10 grid gap-x-10 gap-y-8 sm:grid-cols-2 lg:grid-cols-4">
            {LOOP.map(({ title, body }, i) => (
              <li key={title} className="border-t-2 border-ink pt-4">
                <h3 className="text-lg font-semibold text-ink">
                  {title}
                  {i < LOOP.length - 1 && (
                    <span aria-hidden className="ml-2 font-normal text-pencil">
                      →
                    </span>
                  )}
                </h3>
                <p className="type-body mt-1.5 text-[15px] text-graphite">{body}</p>
              </li>
            ))}
          </ol>
        </Reveal>
      </div>
    </section>
  )
}

function Faq() {
  return (
    <section id="faq" aria-labelledby="faq-title" className="grid scroll-mt-28 gap-10 lg:grid-cols-[minmax(0,4fr)_minmax(0,8fr)] lg:gap-16">
      <Reveal>
        <h2 id="faq-title" className="text-[28px] font-semibold leading-[1.15] tracking-[-0.018em] text-ink sm:text-[32px]">
          Questions people ask
        </h2>
        <p className="type-body mt-3 max-w-sm text-[15px] text-graphite">
          Something else? Sign in and use Feedback at the top of any screen.
        </p>
      </Reveal>
      <Reveal>
        <div className="border-t border-line">
          {FAQS.map(({ q, a }) => (
            <details key={q} className="group border-b border-line [&_summary::-webkit-details-marker]:hidden">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 py-4 text-[15px] font-medium text-ink">
                {q}
                <ChevronDown size={18} aria-hidden className="shrink-0 text-graphite transition-transform duration-200 group-open:rotate-180" />
              </summary>
              <p className="type-body -mt-1 max-w-[64ch] pb-5 text-[15px] text-graphite">{a}</p>
            </details>
          ))}
        </div>
      </Reveal>
    </section>
  )
}

/** The close: a field of ink, the name of the next step, one action. */
function FinalCta({ signedIn }: { signedIn: boolean }) {
  return (
    <section className="bg-action">
      <div className="mx-auto flex w-full max-w-[1200px] flex-col gap-8 px-4 py-20 sm:px-6 md:flex-row md:items-end md:justify-between lg:px-8 lg:py-24">
        <div>
          <h2 className="max-w-xl text-[32px] font-semibold leading-[1.1] tracking-[-0.02em] text-action-ink text-balance sm:text-[40px]">
            Add your first topic in under a minute.
          </h2>
          <p className="mt-4 max-w-md text-base text-action-ink/70">Free, with no daily limits on any mode.</p>
        </div>
        <div className="flex flex-wrap items-center gap-x-5 gap-y-3">
          <Link
            to={signedIn ? '/dashboard' : '/register'}
            className={buttonClass({ variant: 'ghost', size: 'lg', className: 'bg-paper' })}
          >
            {signedIn ? 'Go to your topics' : 'Create your account'}
          </Link>
          {!signedIn && (
            <Link to="/login" className="text-sm font-medium text-action-ink underline decoration-action-ink/40 underline-offset-4 hover:decoration-action-ink">
              I already have an account
            </Link>
          )}
        </div>
      </div>
    </section>
  )
}

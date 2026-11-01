import { Link } from 'react-router-dom'
import { useTheme } from '../../features/theme/ThemeProvider'
import { shotUrl, type Step } from '../../features/howItWorks/content'
import { scrollToSection } from '../../features/howItWorks/hooks'
import { buttonClass } from '../ui/Button'

/** The first screen: what PrepPilot is, one action, and the product itself at full size. */
export default function Hero({ steps, signedIn }: { steps: Step[]; signedIn: boolean }) {
  const { theme } = useTheme()

  return (
    <section className="border-b border-line">
      <div className="mx-auto grid w-full max-w-[1200px] items-center gap-10 px-4 pb-14 pt-12 sm:px-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)] lg:gap-14 lg:px-8 lg:pb-20 lg:pt-16">
        <div>
          <h1 className="text-[38px] font-semibold leading-[1.08] tracking-[-0.025em] text-ink text-balance sm:text-[44px]">
            Learn it, test it, then sit the interview.
          </h1>
          <p className="mt-6 max-w-md text-[17px] leading-[1.55] text-graphite text-pretty">
            PrepPilot is a free interview coach for any technical topic, with no daily limits. This guide walks through
            every screen, from signing up to your interview report.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-x-5 gap-y-3">
            <Link to={signedIn ? '/dashboard' : '/register'} className={buttonClass({ variant: 'primary', size: 'lg' })}>
              {signedIn ? 'Go to your topics' : 'Create your account'}
            </Link>
            <button
              type="button"
              onClick={() => scrollToSection(steps[0].id)}
              className="text-sm font-medium text-ink underline decoration-edge underline-offset-4 hover:decoration-ink"
            >
              Take the tour
            </button>
          </div>
        </div>

        <figure className="m-0">
          <img
            src={shotUrl('test-report', theme)}
            alt="A graded test report in PrepPilot: the score against the pass mark, then every question marked right or wrong"
            width={1600}
            height={1000}
            className="aspect-[8/5] w-full rounded-lg border border-line bg-sheet object-cover object-top"
          />
          <figcaption className="type-meta mt-2.5">A test report: the score against its pass mark, then every question marked.</figcaption>
        </figure>
      </div>
    </section>
  )
}

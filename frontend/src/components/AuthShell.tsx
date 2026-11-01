import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import ThemeToggle from './ThemeToggle'
import { Wordmark } from './BrandMark'
import ScoreBar from './ui/ScoreBar'
import StatusPill from './ui/StatusPill'

/**
 * Sign-in, registration and onboarding: the form on the left, and on wide screens a piece of the
 * product on the right, built from the same components the app uses (sample content).
 */
export default function AuthShell({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string
  subtitle?: string
  children: ReactNode
  footer?: ReactNode
}) {
  return (
    <div className="grid min-h-screen w-full lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)]">
      <div className="flex flex-col px-5 py-6 sm:px-10">
        <div className="flex items-center justify-between">
          <Link to="/how-it-works" className="no-underline hover:no-underline" aria-label="PrepPilot, how it works">
            <Wordmark />
          </Link>
          <ThemeToggle />
        </div>

        <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center py-12">
          <h1 className="type-title">{title}</h1>
          {subtitle && <p className="type-body mt-1.5 text-graphite">{subtitle}</p>}
          <div className="mt-7">{children}</div>
          {footer && <div className="mt-6 text-sm text-graphite">{footer}</div>}
        </div>
      </div>

      <aside aria-hidden className="hidden border-l border-line bg-wash lg:flex lg:flex-col lg:justify-center lg:px-14 xl:px-20">
        <div className="max-w-md">
          <p className="text-[28px] font-semibold leading-[1.2] tracking-[-0.015em] text-ink">
            Clear the bar before the real interview.
          </p>
          <p className="type-body mt-3 text-[15px] text-graphite">
            Add any topic. Learn it with a tutor, take a 20-question test, then sit a timed mock interview. Every score is
            drawn against its pass mark.
          </p>
        </div>

        <ProductSample />

        <Link
          to="/how-it-works"
          tabIndex={-1}
          className="mt-8 w-fit text-sm font-medium text-ink underline decoration-edge underline-offset-4 hover:decoration-ink"
        >
          See how it works
        </Link>
      </aside>
    </div>
  )
}

/** A graded test and an interview question, as they appear in the app. */
function ProductSample() {
  return (
    <div className="mt-10 max-w-md rounded-lg border border-line bg-sheet">
      <div className="px-5 py-4">
        <p className="type-meta">Kubernetes · Test, attempt #3</p>
        <div className="mt-1.5 flex items-center gap-3">
          <p className="figures text-2xl font-semibold text-ink">
            42<span className="text-base font-normal text-graphite"> / 60</span>
          </p>
          <StatusPill tone="positive">Passed</StatusPill>
        </div>
        <ScoreBar score={42} max={60} pass={36} size="md" className="mt-3" />
        <p className="type-meta mt-2">Pass mark 36</p>
      </div>
      <div className="border-t border-rule px-5 py-4">
        <div className="flex items-center justify-between gap-3">
          <p className="type-meta">Mock interview · Deployments</p>
          <StatusPill tone="positive">Strong</StatusPill>
        </div>
        <p className="type-question mt-1.5 text-[17px] leading-[1.45] text-ink">
          A release doubles your error rate. How do you roll it back without downtime?
        </p>
      </div>
    </div>
  )
}

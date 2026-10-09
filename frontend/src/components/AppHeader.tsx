import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, LogOut } from 'lucide-react'
import ThemeToggle from './ThemeToggle'
import FeedbackButton from './FeedbackButton'
import { useAppSelector } from '../hooks'

type AppHeaderProps = {
  onBack?: () => void
  title?: string
  subtitle?: string
  actions?: ReactNode
  userName?: string | null
  onLogout?: () => void
}

export default function AppHeader({ onBack, title, subtitle, actions, userName, onLogout }: AppHeaderProps) {
  const navigate = useNavigate()
  // The header also shows on the public How it works page
  const signedIn = useAppSelector((state) => Boolean(state.auth.accessToken && state.auth.user))

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-surface/85 backdrop-blur-md">
      <div className="mx-auto flex h-16 w-full max-w-[1400px] items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        {/* A size container: on narrow screens with many buttons the wordmark hides and the logo stays */}
        <div className="@container flex min-w-0 flex-1 items-center gap-3">
          {onBack ? (
            <button
              type="button"
              onClick={onBack}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg px-2 text-sm font-semibold text-muted transition-colors hover:bg-surface-hover hover:text-fg"
            >
              <ArrowLeft size={16} />
              <span className="hidden sm:inline">Back</span>
            </button>
          ) : (
            <button
              type="button"
              onClick={() => navigate('/dashboard')}
              className="flex items-center gap-2"
            >
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-accent text-sm font-black text-white">
                P
              </span>
              <span className="text-base font-extrabold tracking-tight text-fg @max-[7.5rem]:hidden">PrepPilot</span>
            </button>
          )}

          {(title || subtitle) && (
            <div className="min-w-0 border-l border-border pl-3">
              {title && <p className="truncate text-sm font-bold text-fg sm:text-base">{title}</p>}
              {subtitle && (
                <p className="truncate text-[11px] font-medium uppercase tracking-wide text-muted">{subtitle}</p>
              )}
            </div>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-2 sm:gap-3">
          {actions}
          {signedIn && <FeedbackButton />}
          <ThemeToggle />
          {userName && (
            <span className="hidden text-sm font-semibold text-muted md:inline" data-clarity-mask="True">
              {userName}
            </span>
          )}
          {onLogout && (
            <button
              type="button"
              onClick={onLogout}
              aria-label="Sign out"
              title="Sign out"
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border px-3 text-sm font-semibold text-muted transition-colors hover:bg-surface-hover hover:text-fg"
            >
              <LogOut size={15} />
              <span className="hidden lg:inline">Sign out</span>
            </button>
          )}
        </div>
      </div>
    </header>
  )
}

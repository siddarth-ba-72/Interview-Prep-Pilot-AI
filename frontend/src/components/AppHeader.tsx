import { useEffect, useRef, useState, type ReactNode } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { Menu, X } from 'lucide-react'
import ThemeToggle from './ThemeToggle'
import FeedbackButton from './FeedbackButton'
import { Wordmark } from './BrandMark'
import { buttonClass } from './ui/Button'
import { useAppSelector } from '../hooks'
import { useSignOut } from '../features/auth/useSignOut'

type NavItem = { to: string; label: string; end?: boolean }

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `inline-flex h-8 items-center rounded-md px-2.5 text-sm no-underline transition-colors duration-150 hover:no-underline ${
    isActive ? 'bg-press font-medium text-ink' : 'text-graphite hover:bg-wash hover:text-ink'
  }`

/**
 * The one top bar, the same on every screen: the product, where you can go, and your account.
 * It sits on the page ground with a 1px rule; below the medium breakpoint the links fold into a menu.
 */
export default function AppHeader({ actions }: { actions?: ReactNode }) {
  const { accessToken, user, status } = useAppSelector((state) => state.auth)
  const signedIn = Boolean(accessToken && user)
  const signOut = useSignOut()
  const [menuOpen, setMenuOpen] = useState(false)
  const { pathname } = useLocation()
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => setMenuOpen(false), [pathname])

  useEffect(() => {
    if (!menuOpen) return
    const onKeyDown = (event: KeyboardEvent) => event.key === 'Escape' && setMenuOpen(false)
    const onPointerDown = (event: PointerEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) setMenuOpen(false)
    }
    window.addEventListener('keydown', onKeyDown)
    window.addEventListener('pointerdown', onPointerDown)
    return () => {
      window.removeEventListener('keydown', onKeyDown)
      window.removeEventListener('pointerdown', onPointerDown)
    }
  }, [menuOpen])

  const nav: NavItem[] = signedIn
    ? [
        { to: '/dashboard', label: 'Topics', end: true },
        { to: '/how-it-works', label: 'How it works' },
        ...(user?.role === 'ADMIN' ? [{ to: '/admin', label: 'Admin' }] : []),
      ]
    : [{ to: '/how-it-works', label: 'How it works' }]

  const firstName = user?.displayName?.trim().split(/\s+/)[0]

  return (
    <header className="sticky top-0 z-30 border-b border-line bg-paper">
      <div ref={menuRef} className="relative mx-auto flex h-13 w-full max-w-[1200px] items-center gap-6 px-4 sm:px-6 lg:px-8">
        <Link to={signedIn ? '/dashboard' : '/how-it-works'} className="no-underline hover:no-underline" aria-label="PrepPilot home">
          <Wordmark />
        </Link>

        <nav aria-label="Main" className="hidden items-center gap-1 md:flex">
          {nav.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className={navLinkClass}>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-1.5">
          {actions}
          {signedIn && <FeedbackButton />}
          <ThemeToggle />

          {signedIn && (
            <div className="hidden items-center gap-1.5 md:flex">
              <NavLink to="/onboarding" title="Profile" aria-label="Profile" className={navLinkClass}>
                <span data-clarity-mask="True" className="max-w-36 truncate">
                  {firstName || 'Profile'}
                </span>
              </NavLink>
              <button type="button" onClick={signOut} className={buttonClass({ variant: 'quiet', size: 'sm' })}>
                Sign out
              </button>
            </div>
          )}

          {!signedIn && status !== 'loading' && (
            <div className="flex items-center gap-1.5">
              <Link to="/login" className={buttonClass({ variant: 'quiet', size: 'sm' })}>
                Sign in
              </Link>
              <Link to="/register" className={buttonClass({ variant: 'primary', size: 'sm', className: 'hidden sm:inline-flex' })}>
                Create account
              </Link>
            </div>
          )}

          {signedIn && (
            <button
              type="button"
              onClick={() => setMenuOpen((open) => !open)}
              aria-expanded={menuOpen}
              aria-controls="main-menu"
              aria-label={menuOpen ? 'Close menu' : 'Open menu'}
              className={buttonClass({ variant: 'quiet', size: 'sm', className: 'w-8 px-0 md:hidden' })}
            >
              {menuOpen ? <X size={18} /> : <Menu size={18} />}
            </button>
          )}
        </div>

        {menuOpen && signedIn && (
          <div
            id="main-menu"
            className="animate-menu-in absolute inset-x-3 top-[calc(100%+6px)] rounded-lg border border-line bg-sheet p-2 shadow-[0_12px_32px_-12px_rgba(0,0,0,0.25)] md:hidden"
          >
            <nav aria-label="Main" className="flex flex-col">
              {nav.map((item) => (
                <NavLink key={item.to} to={item.to} end={item.end} className={menuLinkClass}>
                  {item.label}
                </NavLink>
              ))}
              <NavLink to="/onboarding" className={menuLinkClass}>
                Profile
              </NavLink>
            </nav>
            <div className="mt-1 border-t border-rule pt-1">
              <button type="button" onClick={signOut} className={`${menuLinkClass({ isActive: false })} w-full`}>
                Sign out
              </button>
            </div>
          </div>
        )}
      </div>
    </header>
  )
}

const menuLinkClass = ({ isActive }: { isActive: boolean }) =>
  `flex h-11 items-center rounded-md px-3 text-[15px] no-underline hover:no-underline ${
    isActive ? 'bg-press font-medium text-ink' : 'text-ink hover:bg-wash'
  }`

import { ArrowUpRight, Heart } from 'lucide-react'

const PORTFOLIO_URL = 'https://siddarth-ba-72.github.io/siddarth-ba-72-portfolio/'

export default function Footer() {
  return (
    <footer className="border-t border-border bg-surface">
      <div className="mx-auto flex w-full max-w-[1400px] flex-col items-center justify-between gap-3 px-4 py-4 text-sm text-muted sm:h-16 sm:flex-row sm:px-6 sm:py-0 lg:px-8">
        <span className="text-fg">PrepPilot</span>

        <p className="flex items-center gap-1.5">
          Made with
          <Heart size={14} className="animate-pulse fill-danger text-danger" aria-hidden />
          by
          <a
            href={PORTFOLIO_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="group inline-flex items-center gap-1 rounded-full bg-primary-subtle px-3 py-1 font-semibold text-primary transition-colors hover:bg-primary hover:text-primary-fg hover:no-underline"
          >
            Siddarth Ambannavar
            <ArrowUpRight size={14} className="transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
          </a>
        </p>
      </div>
    </footer>
  )
}

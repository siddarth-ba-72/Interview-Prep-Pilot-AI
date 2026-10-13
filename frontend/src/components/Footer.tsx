const PORTFOLIO_URL = 'https://siddarth-ba-72.vercel.app/'

export default function Footer() {
  return (
    <footer className="border-t border-border bg-surface">
      <p className="mx-auto w-full max-w-[1400px] px-4 py-5 text-center text-sm text-muted sm:px-6 lg:px-8">
        Built by{' '}
        <a
          href={PORTFOLIO_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="font-semibold text-fg underline underline-offset-4 transition-colors hover:text-primary"
        >
          Siddarth Ambannavar
        </a>
      </p>
    </footer>
  )
}

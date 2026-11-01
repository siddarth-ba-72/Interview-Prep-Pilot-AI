const PORTFOLIO_URL = 'https://siddarth-ba-72.vercel.app/'

export default function Footer() {
  return (
    <footer className="border-t border-line">
      <p className="mx-auto flex h-12 w-full max-w-[1200px] items-center px-4 text-[13px] text-graphite sm:px-6 lg:px-8">
        Built by&nbsp;
        <a
          href={PORTFOLIO_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="font-medium text-ink underline underline-offset-4 hover:text-ballpoint"
        >
          Siddarth Ambannavar
        </a>
      </p>
    </footer>
  )
}

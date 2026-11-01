import { Link } from 'react-router-dom'

/** Switches the History tab between the topic's tests and its mock interviews. */
export default function HistorySwitch({ topicId, current }: { topicId: string; current: 'tests' | 'interviews' }) {
  const options = [
    { key: 'tests', label: 'Tests', to: `/topics/${topicId}/tests` },
    { key: 'interviews', label: 'Mock interviews', to: `/topics/${topicId}/interviews/history` },
  ] as const

  return (
    <nav aria-label="History" className="inline-grid grid-cols-2 rounded-md bg-wash p-0.5 text-[13px]">
      {options.map((option) => {
        const active = option.key === current
        return (
          <Link
            key={option.key}
            to={option.to}
            aria-current={active ? 'page' : undefined}
            className={`flex h-8 items-center justify-center rounded-[5px] px-3.5 no-underline transition-colors duration-150 hover:no-underline ${
              active ? 'bg-sheet font-medium text-ink shadow-[0_0_0_1px_var(--line)]' : 'text-graphite hover:text-ink'
            }`}
          >
            {option.label}
          </Link>
        )
      })}
    </nav>
  )
}

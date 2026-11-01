import { NavLink } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { feedbackPageQuery } from '../features/admin/queries'

/** Switches between the admin sections. The Feedback tab shows how many messages there are. */
export default function AdminTabs() {
  const feedbackTotal = useQuery(feedbackPageQuery(0)).data?.total

  return (
    <nav aria-label="Admin sections" className="flex gap-5 border-b border-line">
      <Tab to="/admin" end>
        Users
      </Tab>
      <Tab to="/admin/feedback">
        Feedback
        {feedbackTotal !== undefined && <span className="figures text-pencil">{feedbackTotal.toLocaleString()}</span>}
      </Tab>
    </nav>
  )
}

function Tab({ to, end, children }: { to: string; end?: boolean; children: React.ReactNode }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `-mb-px inline-flex items-center gap-1.5 border-b-2 pb-2.5 pt-1 text-sm no-underline transition-colors duration-150 hover:no-underline ${
          isActive ? 'border-ink font-medium text-ink' : 'border-transparent text-graphite hover:text-ink'
        }`
      }
    >
      {children}
    </NavLink>
  )
}

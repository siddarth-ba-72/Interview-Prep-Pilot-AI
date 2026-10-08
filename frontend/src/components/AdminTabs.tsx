import { NavLink } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Inbox, Users } from 'lucide-react'
import { feedbackPageQuery } from '../features/admin/queries'

/** Switches between the admin sections. The Feedback tab shows how many messages there are. */
export default function AdminTabs() {
  const feedbackTotal = useQuery(feedbackPageQuery(0)).data?.total

  return (
    <nav aria-label="Admin sections" className="flex gap-1 border-b border-border">
      <Tab to="/admin" end>
        <Users size={15} />
        Users
      </Tab>
      <Tab to="/admin/feedback">
        <Inbox size={15} />
        Feedback
        {feedbackTotal !== undefined && (
          <span className="rounded-full bg-primary-subtle px-2 py-0.5 text-[11px] font-bold tabular-nums text-primary">
            {feedbackTotal}
          </span>
        )}
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
        `-mb-px inline-flex items-center gap-2 border-b-2 px-3 py-2.5 text-sm font-semibold no-underline transition-colors hover:no-underline ${
          isActive ? 'border-primary text-fg' : 'border-transparent text-muted hover:text-fg'
        }`
      }
    >
      {children}
    </NavLink>
  )
}

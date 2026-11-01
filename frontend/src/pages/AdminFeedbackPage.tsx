import { useState } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import AdminTabs from '../components/AdminTabs'
import AppHeader from '../components/AppHeader'
import PageContainer from '../components/PageContainer'
import Pager from '../components/Pager'
import EmptyState from '../components/ui/EmptyState'
import Notice from '../components/ui/Notice'
import type { AdminFeedback } from '../api/admin'
import { formatDateTime } from '../features/admin/format'
import { feedbackPageQuery } from '../features/admin/queries'

export default function AdminFeedbackPage() {
  const [page, setPage] = useState(0)
  const feedbackQuery = useQuery({ ...feedbackPageQuery(page), placeholderData: keepPreviousData })
  const list = feedbackQuery.data

  return (
    <div className="min-h-screen">
      <AppHeader />

      <PageContainer mask className="flex flex-col gap-6">
        <div>
          <h1 className="type-title">Admin</h1>
          <p className="type-body mt-1 max-w-2xl text-graphite">What users sent from the Feedback button, newest first.</p>
        </div>

        <AdminTabs />

        {feedbackQuery.isLoading && <div aria-label="Loading feedback" className="h-48 max-w-4xl rounded-lg border border-line bg-sheet" />}
        {feedbackQuery.isError && <Notice>Could not load feedback.</Notice>}

        {list && list.feedback.length === 0 && (
          <div className="max-w-4xl">
            <EmptyState>No feedback yet.</EmptyState>
          </div>
        )}

        {list && list.feedback.length > 0 && (
          <div className="flex max-w-4xl flex-col gap-4">
            <ul className="divide-y divide-rule rounded-lg border border-line bg-sheet">
              {list.feedback.map((item) => (
                <FeedbackItem key={item.id} item={item} />
              ))}
            </ul>
            <Pager page={list.page} size={list.size} shown={list.feedback.length} total={list.total} onPage={setPage} />
          </div>
        )}
      </PageContainer>
    </div>
  )
}

function FeedbackItem({ item }: { item: AdminFeedback }) {
  return (
    <li className="px-5 py-4">
      <div className="flex flex-col gap-0.5 sm:flex-row sm:items-baseline sm:justify-between sm:gap-4">
        <p className="min-w-0 truncate text-sm">
          <Link to={`/admin/users/${encodeURIComponent(item.userId)}`} className="text-ink underline-offset-4 hover:underline">
            {item.displayName || item.email}
          </Link>
          <span className="text-pencil"> · {item.email}</span>
        </p>
        <time dateTime={item.createdAt ?? undefined} className="type-meta shrink-0">
          {formatDateTime(item.createdAt)}
        </time>
      </div>
      <p className="type-body mt-2 max-w-[72ch] whitespace-pre-wrap break-words text-ink">{item.message}</p>
    </li>
  )
}

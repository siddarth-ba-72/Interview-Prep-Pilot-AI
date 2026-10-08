import { useState } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import AdminTabs from '../components/AdminTabs'
import AppHeader from '../components/AppHeader'
import PageContainer from '../components/PageContainer'
import Pager from '../components/Pager'
import type { AdminFeedback } from '../api/admin'
import { formatDateTime } from '../features/admin/format'
import { feedbackPageQuery } from '../features/admin/queries'

export default function AdminFeedbackPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(0)

  const feedbackQuery = useQuery({ ...feedbackPageQuery(page), placeholderData: keepPreviousData })
  const list = feedbackQuery.data

  return (
    <div className="min-h-screen bg-bg">
      <AppHeader onBack={() => navigate('/dashboard')} title="Admin" subtitle="Read-only" />

      <PageContainer className="flex flex-col gap-7">
        <AdminTabs />

        <div className="max-w-4xl">
          <h1 className="text-2xl font-extrabold tracking-tight text-fg sm:text-3xl">User feedback</h1>
          <p className="mt-1 text-sm text-muted">What users sent from the Feedback button, newest first.</p>
        </div>

        {feedbackQuery.isLoading && <p className="text-sm text-muted">Loading feedback…</p>}
        {feedbackQuery.isError && <p className="text-sm font-medium text-danger">Could not load feedback.</p>}

        {list && list.feedback.length === 0 && (
          <div className="max-w-4xl rounded-2xl border border-dashed border-border bg-surface/50 px-6 py-12 text-center">
            <p className="text-sm font-medium text-muted">No feedback yet.</p>
          </div>
        )}

        {list && list.feedback.length > 0 && (
          <div className="flex max-w-4xl flex-col gap-7">
            <ul className="flex flex-col gap-3">
              {list.feedback.map((item) => (
                <FeedbackCard key={item.id} item={item} />
              ))}
            </ul>
            <Pager
              page={list.page}
              size={list.size}
              shown={list.feedback.length}
              total={list.total}
              onPage={setPage}
            />
          </div>
        )}
      </PageContainer>
    </div>
  )
}

function FeedbackCard({ item }: { item: AdminFeedback }) {
  return (
    <li className="rounded-2xl border border-border bg-surface p-4 sm:p-5">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
        <div className="min-w-0">
          <Link
            to={`/admin/users/${encodeURIComponent(item.userId)}`}
            className="block truncate font-semibold text-fg hover:text-primary hover:underline"
          >
            {item.displayName || item.email}
          </Link>
          <p className="truncate text-xs text-muted">{item.email}</p>
        </div>
        <time dateTime={item.createdAt ?? undefined} className="shrink-0 text-xs text-muted">
          {formatDateTime(item.createdAt)}
        </time>
      </div>
      <p className="mt-3 whitespace-pre-wrap break-words text-sm leading-relaxed text-fg">{item.message}</p>
    </li>
  )
}

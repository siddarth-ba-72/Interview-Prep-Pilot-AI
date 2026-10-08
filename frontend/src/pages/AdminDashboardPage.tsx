import { useEffect, useState } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Inbox, Search } from 'lucide-react'
import AppHeader from '../components/AppHeader'
import PageContainer from '../components/PageContainer'
import Pager from '../components/Pager'
import { SessionCountsText, SessionTile, StatTile } from '../components/AdminStats'
import { getActivitySummary, getAdminUserStats, getUsersActivity, listAdminUsers } from '../api/admin'
import type { AdminUser, UserActivity } from '../api/admin'
import { experienceLabel, formatDate } from '../features/admin/format'

const PAGE_SIZE = 20

export default function AdminDashboardPage() {
  const navigate = useNavigate()
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)

  // Search once typing pauses, from the first page
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim())
      setPage(0)
    }, 300)
    return () => clearTimeout(timer)
  }, [searchInput])

  const userStatsQuery = useQuery({ queryKey: ['admin', 'userStats'], queryFn: getAdminUserStats })
  const summaryQuery = useQuery({ queryKey: ['admin', 'summary'], queryFn: getActivitySummary })
  const usersQuery = useQuery({
    queryKey: ['admin', 'users', search, page],
    queryFn: () => listAdminUsers({ q: search, page, size: PAGE_SIZE }),
    placeholderData: keepPreviousData,
  })

  // Counts for just the users on this page, joined by id
  const userIds = usersQuery.data?.users.map((user) => user.id) ?? []
  const activityQuery = useQuery({
    queryKey: ['admin', 'usersActivity', userIds],
    queryFn: () => getUsersActivity(userIds),
    enabled: userIds.length > 0,
    placeholderData: keepPreviousData,
  })
  const activityById = new Map((activityQuery.data ?? []).map((activity) => [activity.userId, activity]))

  const summary = summaryQuery.data
  const usersPage = usersQuery.data

  return (
    <div className="min-h-screen bg-bg">
      <AppHeader
        onBack={() => navigate('/dashboard')}
        title="Admin"
        subtitle="Read-only"
        actions={
          <button
            type="button"
            onClick={() => navigate('/admin/feedback')}
            aria-label="User feedback"
            title="User feedback"
            className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border px-3 text-sm font-semibold text-muted transition-colors hover:bg-surface-hover hover:text-fg"
          >
            <Inbox size={15} />
            <span className="hidden lg:inline">User feedback</span>
          </button>
        }
      />

      <PageContainer className="flex flex-col gap-7">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-fg sm:text-3xl">Admin dashboard</h1>
          <p className="mt-1 text-sm text-muted">
            Users, their topics, and how many tests and mock interviews they have taken. Counts only: no scores,
            answers or chats.
          </p>
        </div>

        <section aria-label="Overview" className="flex flex-col gap-2">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatTile label="Users" value={userStatsQuery.data?.totalUsers} />
            <StatTile label="Topics" value={summary?.topics} />
            <SessionTile label="Tests" counts={summary?.tests} />
            <SessionTile label="Mock interviews" counts={summary?.interviews} />
          </div>
          {(userStatsQuery.isError || summaryQuery.isError) && (
            <p className="text-sm font-medium text-danger">Could not load the overview.</p>
          )}
        </section>

        <section aria-label="Users" className="flex flex-col gap-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <h2 className="text-lg font-extrabold tracking-tight text-fg">Users</h2>
            <label className="flex w-full items-center gap-2 rounded-xl border border-border bg-surface px-3 sm:w-80">
              <Search size={15} className="shrink-0 text-muted" />
              <input
                type="search"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
                placeholder="Search name or email"
                aria-label="Search users by name or email"
                className="h-10 min-w-0 flex-1 bg-transparent text-sm text-fg outline-none placeholder:text-muted"
              />
            </label>
          </div>

          {usersQuery.isLoading && <p className="text-sm text-muted">Loading users…</p>}
          {usersQuery.isError && <p className="text-sm font-medium text-danger">Could not load users.</p>}
          {activityQuery.isError && (
            <p className="text-sm font-medium text-danger">Could not load topic and session counts.</p>
          )}

          {usersPage && usersPage.users.length === 0 && (
            <div className="rounded-2xl border border-dashed border-border bg-surface/50 px-6 py-12 text-center">
              <p className="text-sm font-medium text-muted">
                {search ? `No users match “${search}”.` : 'No users yet.'}
              </p>
            </div>
          )}

          {usersPage && usersPage.users.length > 0 && (
            <>
              <UsersTable
                users={usersPage.users}
                activityById={activityById}
                onOpen={(id) => navigate(`/admin/users/${id}`)}
              />

              <Pager
                page={usersPage.page}
                size={usersPage.size}
                shown={usersPage.users.length}
                total={usersPage.total}
                onPage={setPage}
              />
            </>
          )}
        </section>
      </PageContainer>
    </div>
  )
}

function UsersTable({
  users,
  activityById,
  onOpen,
}: {
  users: AdminUser[]
  activityById: Map<string, UserActivity>
  onOpen: (id: string) => void
}) {
  return (
    <>
      <div className="hidden overflow-hidden rounded-2xl border border-border md:block">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="bg-surface-hover text-xs font-semibold uppercase tracking-wide text-muted">
              <th className="px-4 py-3">User</th>
              <th className="px-4 py-3">Experience</th>
              <th className="px-4 py-3">Joined</th>
              <th className="px-4 py-3 text-right">Topics</th>
              <th className="px-4 py-3">Tests</th>
              <th className="px-4 py-3">Mock interviews</th>
              <th className="px-4 py-3 text-right">
                <span className="sr-only">Action</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => {
              const activity = activityById.get(user.id)
              return (
                <tr key={user.id} className="border-t border-border bg-surface transition-colors hover:bg-surface-hover">
                  <td className="max-w-72 px-4 py-3.5">
                    <UserName user={user} />
                  </td>
                  <td className="px-4 py-3.5 text-muted">{experienceLabel(user.experienceLevel)}</td>
                  <td className="whitespace-nowrap px-4 py-3.5 text-muted">{formatDate(user.createdAt)}</td>
                  <td className="px-4 py-3.5 text-right font-semibold tabular-nums text-fg">
                    {activity ? activity.topics : '…'}
                  </td>
                  <td className="px-4 py-3.5">
                    <SessionCountsText counts={activity?.tests} />
                  </td>
                  <td className="px-4 py-3.5">
                    <SessionCountsText counts={activity?.interviews} />
                  </td>
                  <td className="px-4 py-3.5 text-right">
                    <button
                      type="button"
                      onClick={() => onOpen(user.id)}
                      className="rounded-lg border border-border px-3 py-1.5 text-xs font-bold text-fg transition-colors hover:bg-surface-hover"
                    >
                      View
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="flex flex-col gap-3 md:hidden">
        {users.map((user) => {
          const activity = activityById.get(user.id)
          return (
            <button
              key={user.id}
              type="button"
              onClick={() => onOpen(user.id)}
              className="flex flex-col gap-3 rounded-2xl border border-border bg-surface p-4 text-left transition-colors hover:bg-surface-hover"
            >
              <div className="flex w-full items-start justify-between gap-3">
                <UserName user={user} />
                <span className="shrink-0 text-xs text-muted">{formatDate(user.createdAt)}</span>
              </div>
              <div className="grid w-full grid-cols-3 gap-2 text-sm">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">Topics</p>
                  <p className="font-semibold tabular-nums text-fg">{activity ? activity.topics : '…'}</p>
                </div>
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">Tests</p>
                  <SessionCountsText counts={activity?.tests} />
                </div>
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">Interviews</p>
                  <SessionCountsText counts={activity?.interviews} />
                </div>
              </div>
            </button>
          )
        })}
      </div>
    </>
  )
}

function UserName({ user }: { user: AdminUser }) {
  return (
    <div className="min-w-0">
      <div className="flex items-center gap-2">
        <span className="truncate font-semibold text-fg">{user.displayName || user.email}</span>
        {user.role === 'ADMIN' && (
          <span className="shrink-0 rounded-full bg-primary-subtle px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-primary">
            Admin
          </span>
        )}
      </div>
      <div className="truncate text-xs text-muted">{user.email}</div>
    </div>
  )
}

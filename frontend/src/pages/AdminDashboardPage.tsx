import { useEffect, useState } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import AdminTabs from '../components/AdminTabs'
import AppHeader from '../components/AppHeader'
import PageContainer from '../components/PageContainer'
import Pager from '../components/Pager'
import { KpiStrip, SessionCountsText, sessionKpi } from '../components/AdminStats'
import { Button } from '../components/ui/Button'
import EmptyState from '../components/ui/EmptyState'
import Notice from '../components/ui/Notice'
import StatusPill from '../components/ui/StatusPill'
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
    <div className="min-h-screen">
      <AppHeader />

      <PageContainer mask className="flex flex-col gap-6">
        <div>
          <h1 className="type-title">Admin</h1>
          <p className="type-body mt-1 max-w-2xl text-graphite">
            Read-only. Profiles, topic names, and how many tests and mock interviews each user has taken. No scores,
            answers or chats.
          </p>
        </div>

        <AdminTabs />

        <section aria-label="Overview" className="flex flex-col gap-2">
          <KpiStrip
            items={[
              { label: 'Users', value: userStatsQuery.data?.totalUsers },
              { label: 'Topics', value: summary?.topics },
              sessionKpi('Tests', summary?.tests),
              sessionKpi('Mock interviews', summary?.interviews),
            ]}
          />
          {(userStatsQuery.isError || summaryQuery.isError) && <Notice>Could not load the overview.</Notice>}
        </section>

        <section aria-labelledby="users-title" className="flex flex-col gap-3">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <h2 id="users-title" className="type-section">
              Users
              {usersPage && <span className="figures ml-2 font-normal text-pencil">{usersPage.total.toLocaleString()}</span>}
            </h2>
            <label className="flex h-9 w-full items-center gap-2 rounded-md border border-edge bg-sheet px-3 focus-within:border-ink focus-within:ring-1 focus-within:ring-ink sm:w-72">
              <Search size={15} aria-hidden className="shrink-0 text-pencil" />
              <input
                type="search"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
                placeholder="Search name or email"
                aria-label="Search users by name or email"
                className="min-w-0 flex-1 bg-transparent text-base text-ink outline-none placeholder:text-pencil sm:text-sm"
              />
            </label>
          </div>

          {usersQuery.isLoading && <div aria-label="Loading users" className="h-48 rounded-lg border border-line bg-sheet" />}
          {usersQuery.isError && <Notice>Could not load users.</Notice>}
          {activityQuery.isError && <Notice>Could not load topic and session counts.</Notice>}

          {usersPage && usersPage.users.length === 0 && (
            <EmptyState>{search ? `No users match “${search}”.` : 'No users yet.'}</EmptyState>
          )}

          {usersPage && usersPage.users.length > 0 && (
            <>
              <UsersTable users={usersPage.users} activityById={activityById} onOpen={(id) => navigate(`/admin/users/${id}`)} />
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
      <div className="hidden overflow-hidden rounded-lg border border-line bg-sheet md:block">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="text-xs text-graphite">
              <th className="px-5 py-3 font-normal">User</th>
              <th className="px-5 py-3 font-normal">Experience</th>
              <th className="px-5 py-3 font-normal">Joined</th>
              <th className="px-5 py-3 text-right font-normal">Topics</th>
              <th className="px-5 py-3 text-right font-normal">Tests</th>
              <th className="px-5 py-3 text-right font-normal">Mock interviews</th>
              <th className="px-5 py-3">
                <span className="sr-only">Open</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => {
              const activity = activityById.get(user.id)
              return (
                <tr key={user.id} className="border-t border-rule">
                  <td className="max-w-72 px-5 py-3">
                    <UserName user={user} />
                  </td>
                  <td className="px-5 py-3 text-graphite">{experienceLabel(user.experienceLevel)}</td>
                  <td className="whitespace-nowrap px-5 py-3 text-graphite">{formatDate(user.createdAt)}</td>
                  <td className="figures px-5 py-3 text-right text-ink">
                    {activity ? activity.topics.toLocaleString() : <span className="text-pencil">–</span>}
                  </td>
                  <td className="px-5 py-3">
                    <SessionCountsText counts={activity?.tests} />
                  </td>
                  <td className="px-5 py-3">
                    <SessionCountsText counts={activity?.interviews} />
                  </td>
                  <td className="px-5 py-3 text-right">
                    <Button size="sm" onClick={() => onOpen(user.id)}>
                      View
                    </Button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <ul className="divide-y divide-rule rounded-lg border border-line bg-sheet md:hidden">
        {users.map((user) => {
          const activity = activityById.get(user.id)
          return (
            <li key={user.id}>
              <button
                type="button"
                onClick={() => onOpen(user.id)}
                className="flex w-full items-start justify-between gap-4 px-4 py-3.5 text-left hover:bg-wash"
              >
                <UserName user={user} />
                <span className="figures type-meta shrink-0 text-right">
                  {activity
                    ? `${activity.topics} topics · ${activity.tests.completed} tests · ${activity.interviews.completed} interviews`
                    : '–'}
                </span>
              </button>
            </li>
          )
        })}
      </ul>
    </>
  )
}

function UserName({ user }: { user: AdminUser }) {
  return (
    <div className="min-w-0">
      <div className="flex items-center gap-2">
        <span className="truncate text-ink">{user.displayName || user.email}</span>
        {user.role === 'ADMIN' && <StatusPill tone="neutral">Admin</StatusPill>}
      </div>
      <div className="type-meta truncate">{user.email}</div>
    </div>
  )
}

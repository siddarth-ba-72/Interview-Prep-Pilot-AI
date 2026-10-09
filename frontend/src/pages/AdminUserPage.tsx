import { useQuery } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import AppHeader from '../components/AppHeader'
import PageContainer from '../components/PageContainer'
import { SessionTile, StatTile } from '../components/AdminStats'
import { getAdminUser, getUserActivity } from '../api/admin'
import type { AdminUser, SessionCounts } from '../api/admin'
import { experienceLabel, formatDate, providerLabel } from '../features/admin/format'

export default function AdminUserPage() {
  const { userId = '' } = useParams<{ userId: string }>()
  const navigate = useNavigate()

  const userQuery = useQuery({ queryKey: ['admin', 'user', userId], queryFn: () => getAdminUser(userId) })
  const activityQuery = useQuery({ queryKey: ['admin', 'userActivity', userId], queryFn: () => getUserActivity(userId) })

  const user = userQuery.data
  const activity = activityQuery.data
  const notFound = (userQuery.error as { response?: { status?: number } } | null)?.response?.status === 404

  return (
    <div className="min-h-screen bg-bg">
      <AppHeader
        onBack={() => navigate('/admin')}
        title={user ? user.displayName || user.email : 'User'}
        subtitle="Admin · Read-only"
      />

      <PageContainer mask maxWidth="max-w-5xl" className="flex flex-col gap-7">
        {userQuery.isLoading && <p className="text-sm text-muted">Loading user…</p>}
        {userQuery.isError && (
          <p className="text-sm font-medium text-danger">{notFound ? 'User not found.' : 'Could not load this user.'}</p>
        )}
        {user && <ProfileCard user={user} />}

        {!notFound && (
          <section aria-label="Activity" className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <StatTile label="Topics" value={activity?.topics.length} />
            <SessionTile label="Tests" counts={activity?.tests} />
            <SessionTile label="Mock interviews" counts={activity?.interviews} />
          </section>
        )}

        {activityQuery.isError && !notFound && (
          <p className="text-sm font-medium text-danger">Could not load topics and session counts.</p>
        )}

        {activity && (
          <section aria-label="Topics" className="flex flex-col gap-4">
            <h2 className="text-lg font-extrabold tracking-tight text-fg">Topics</h2>
            {activity.topics.length === 0 && !activity.deletedTopics ? (
              <div className="rounded-2xl border border-dashed border-border bg-surface/50 px-6 py-12 text-center">
                <p className="text-sm font-medium text-muted">No topics yet.</p>
              </div>
            ) : (
              <div className="overflow-x-auto rounded-2xl border border-border">
                <table className="w-full min-w-[560px] text-left text-sm">
                  <thead>
                    <tr className="bg-surface-hover text-xs font-semibold uppercase tracking-wide text-muted">
                      <th rowSpan={2} className="px-4 py-3 align-bottom">
                        Topic
                      </th>
                      <th colSpan={2} className="border-l border-border px-4 pb-1 pt-3 text-center">
                        Tests
                      </th>
                      <th colSpan={2} className="border-l border-border px-4 pb-1 pt-3 text-center">
                        Mock interviews
                      </th>
                    </tr>
                    <tr className="bg-surface-hover text-[11px] font-semibold uppercase tracking-wide text-muted">
                      <th className="border-l border-border px-4 pb-3 pt-1 text-right">Active</th>
                      <th className="px-4 pb-3 pt-1 text-right">Completed</th>
                      <th className="border-l border-border px-4 pb-3 pt-1 text-right">Active</th>
                      <th className="px-4 pb-3 pt-1 text-right">Completed</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activity.topics.map((topic, index) => (
                      <TopicRow key={`${topic.name}-${index}`} name={topic.name} tests={topic.tests} interviews={topic.interviews} />
                    ))}
                    {activity.deletedTopics && (
                      <TopicRow
                        name="Deleted topics"
                        muted
                        tests={activity.deletedTopics.tests}
                        interviews={activity.deletedTopics.interviews}
                      />
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        )}
      </PageContainer>
    </div>
  )
}

function ProfileCard({ user }: { user: AdminUser }) {
  const initial = (user.displayName || user.email).charAt(0).toUpperCase()
  return (
    <section aria-label="Profile" className="rounded-2xl border border-border bg-surface p-5">
      <div className="flex items-center gap-4">
        <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary-subtle text-lg font-extrabold text-primary">
          {initial}
        </span>
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="truncate text-xl font-extrabold tracking-tight text-fg">{user.displayName || user.email}</h1>
            {user.role === 'ADMIN' && (
              <span className="rounded-full bg-primary-subtle px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-primary">
                Admin
              </span>
            )}
          </div>
          <p className="truncate text-sm text-muted">{user.email}</p>
        </div>
      </div>
      <dl className="mt-5 grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
        <ProfileField label="Experience" value={experienceLabel(user.experienceLevel)} />
        <ProfileField label="Domain" value={user.preferredDomain || 'Not answered'} />
        <ProfileField label="Sign-in" value={providerLabel(user.authProvider)} />
        <ProfileField label="Joined" value={formatDate(user.createdAt)} />
      </dl>
    </section>
  )
}

function ProfileField({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-[11px] font-semibold uppercase tracking-wide text-muted">{label}</dt>
      <dd className="mt-0.5 truncate font-medium text-fg">{value}</dd>
    </div>
  )
}

function TopicRow({
  name,
  tests,
  interviews,
  muted = false,
}: {
  name: string
  tests: SessionCounts
  interviews: SessionCounts
  muted?: boolean
}) {
  const nameClass = muted ? 'italic text-muted' : 'font-semibold text-fg'
  return (
    <tr className="border-t border-border bg-surface">
      <td className={`max-w-xs truncate px-4 py-3.5 ${nameClass}`}>{name}</td>
      <CountCell value={tests.active} highlight divider />
      <CountCell value={tests.completed} />
      <CountCell value={interviews.active} highlight divider />
      <CountCell value={interviews.completed} />
    </tr>
  )
}

function CountCell({ value, highlight = false, divider = false }: { value: number; highlight?: boolean; divider?: boolean }) {
  const color = value === 0 ? 'text-muted' : highlight ? 'font-semibold text-primary' : 'font-semibold text-fg'
  return <td className={`px-4 py-3.5 text-right tabular-nums ${divider ? 'border-l border-border' : ''} ${color}`}>{value}</td>
}

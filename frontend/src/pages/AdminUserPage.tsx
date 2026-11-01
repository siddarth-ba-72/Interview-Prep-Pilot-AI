import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import AppHeader from '../components/AppHeader'
import PageContainer from '../components/PageContainer'
import { KpiStrip, SessionCountsText, sessionKpi } from '../components/AdminStats'
import EmptyState from '../components/ui/EmptyState'
import Notice from '../components/ui/Notice'
import StatusPill from '../components/ui/StatusPill'
import { getAdminUser, getUserActivity } from '../api/admin'
import type { AdminUser, SessionCounts } from '../api/admin'
import { experienceLabel, formatDate, providerLabel } from '../features/admin/format'

export default function AdminUserPage() {
  const { userId = '' } = useParams<{ userId: string }>()

  const userQuery = useQuery({ queryKey: ['admin', 'user', userId], queryFn: () => getAdminUser(userId) })
  const activityQuery = useQuery({ queryKey: ['admin', 'userActivity', userId], queryFn: () => getUserActivity(userId) })

  const user = userQuery.data
  const activity = activityQuery.data
  const notFound = (userQuery.error as { response?: { status?: number } } | null)?.response?.status === 404

  return (
    <div className="min-h-screen">
      <AppHeader />

      <PageContainer mask maxWidth="max-w-5xl" className="flex flex-col gap-6">
        <div>
          <Link to="/admin" className="type-meta text-graphite no-underline hover:text-ink hover:underline">
            Admin · Users
          </Link>
          {userQuery.isLoading && <div className="mt-1 h-7 w-56 rounded bg-press" aria-label="Loading user" />}
          {user && <ProfileHeading user={user} />}
          {userQuery.isError && (
            <Notice className="mt-3">{notFound ? 'User not found.' : 'Could not load this user.'}</Notice>
          )}
        </div>

        {user && <ProfileFields user={user} />}

        {!notFound && (
          <section aria-label="Activity">
            <KpiStrip
              items={[
                { label: 'Topics', value: activity?.topics.length },
                sessionKpi('Tests', activity?.tests),
                sessionKpi('Mock interviews', activity?.interviews),
              ]}
            />
          </section>
        )}

        {activityQuery.isError && !notFound && <Notice>Could not load topics and session counts.</Notice>}

        {activity && (
          <section aria-labelledby="topics-title" className="flex flex-col gap-3">
            <h2 id="topics-title" className="type-section">
              Topics
            </h2>
            {activity.topics.length === 0 && !activity.deletedTopics ? (
              <EmptyState>No topics yet.</EmptyState>
            ) : (
              <div className="overflow-x-auto rounded-lg border border-line bg-sheet">
                <table className="w-full min-w-[520px] text-left text-sm">
                  <thead>
                    <tr className="text-xs text-graphite">
                      <th className="px-5 py-3 font-normal">Topic</th>
                      <th className="px-5 py-3 text-right font-normal">Tests</th>
                      <th className="px-5 py-3 text-right font-normal">Mock interviews</th>
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

function ProfileHeading({ user }: { user: AdminUser }) {
  return (
    <div className="mt-0.5">
      <div className="flex flex-wrap items-center gap-2">
        <h1 className="type-title truncate">{user.displayName || user.email}</h1>
        {user.role === 'ADMIN' && <StatusPill tone="neutral">Admin</StatusPill>}
      </div>
      <p className="type-body truncate text-graphite">{user.email}</p>
    </div>
  )
}

function ProfileFields({ user }: { user: AdminUser }) {
  const fields = [
    { label: 'Experience', value: experienceLabel(user.experienceLevel) },
    { label: 'Domain', value: user.preferredDomain || 'Not answered' },
    { label: 'Sign-in', value: providerLabel(user.authProvider) },
    { label: 'Joined', value: formatDate(user.createdAt) },
  ]
  return (
    <dl aria-label="Profile" className="grid grid-cols-2 gap-x-6 gap-y-4 rounded-lg border border-line bg-sheet px-5 py-4 sm:grid-cols-4">
      {fields.map((field) => (
        <div key={field.label} className="min-w-0">
          <dt className="type-label">{field.label}</dt>
          <dd className="mt-0.5 truncate text-sm text-ink">{field.value}</dd>
        </div>
      ))}
    </dl>
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
  return (
    <tr className="border-t border-rule">
      <td className={`max-w-xs truncate px-5 py-3 ${muted ? 'text-graphite' : 'text-ink'}`}>{name}</td>
      <td className="px-5 py-3">
        <SessionCountsText counts={tests} />
      </td>
      <td className="px-5 py-3">
        <SessionCountsText counts={interviews} />
      </td>
    </tr>
  )
}

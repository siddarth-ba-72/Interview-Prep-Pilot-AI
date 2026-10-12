import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { useAppSelector, useAppDispatch } from '../hooks'
import { clearCredentials } from '../features/auth/authSlice'
import api from '../api/axiosInstance'
import { useNavigate } from 'react-router-dom'
import { CircleHelp, Search, ShieldCheck, UserRoundPen, X } from 'lucide-react'
import { createTopic, deleteTopic, extractErrorMessage, listTopics } from '../api/topics'
import { USAGE_QUERY_KEY } from '../api/usage'
import { useUsage } from '../features/usage/useUsage'
import { trackEvent } from '../features/analytics/clarity'
import NewTopicForm from '../components/NewTopicForm'
import UsageSummary from '../components/UsageSummary'
import TopicList from '../components/TopicList'
import AppHeader from '../components/AppHeader'
import PageContainer from '../components/PageContainer'
import DashboardHero from '../components/dashboard/DashboardHero'

const TOPIC_IDEAS = ['System Design', 'Data Structures', 'Java', 'Python', 'SQL', 'React', 'Operating Systems', 'Docker']

/** Above this many topics the list gets a search box. */
const SEARCH_THRESHOLD = 4

export default function DashboardPage() {
  const user = useAppSelector((state) => state.auth.user)
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [createError, setCreateError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [search, setSearch] = useState('')

  const topicsQuery = useQuery({ queryKey: ['topics'], queryFn: listTopics })
  const usageQuery = useUsage()

  const createMutation = useMutation({
    mutationFn: createTopic,
    onSuccess: () => {
      setCreateError(null)
      trackEvent('topic_created')
      queryClient.invalidateQueries({ queryKey: ['topics'] })
      queryClient.invalidateQueries({ queryKey: USAGE_QUERY_KEY })
    },
    onError: (error) => setCreateError(extractErrorMessage(error, 'Could not create topic')),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteTopic,
    onMutate: (topicId) => setDeletingId(topicId),
    onSettled: () => setDeletingId(null),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['topics'] })
      queryClient.invalidateQueries({ queryKey: USAGE_QUERY_KEY })
    },
  })

  async function handleLogout() {
    await api.post('/auth/logout').catch(() => null)
    dispatch(clearCredentials())
    navigate('/login')
  }

  const topics = topicsQuery.data
  const topicCount = topics?.length ?? 0
  const topicLimit = usageQuery.data?.topics.limit ?? null
  const atTopicLimit = topicLimit !== null && topics !== undefined && topicCount >= topicLimit

  const stats = useMemo(() => {
    let testCount = 0
    let bestAvgScore: number | null = null
    for (const topic of topics ?? []) {
      testCount += topic.testCount ?? 0
      if (topic.avgScore !== null && topic.avgScore !== undefined) {
        bestAvgScore = Math.max(bestAvgScore ?? 0, topic.avgScore)
      }
    }
    return { testCount, bestAvgScore }
  }, [topics])

  const suggestions = useMemo(() => {
    const taken = new Set((topics ?? []).map((topic) => topic.name.toLowerCase()))
    return TOPIC_IDEAS.filter((idea) => !taken.has(idea.toLowerCase())).slice(0, 5)
  }, [topics])

  const query = search.trim().toLowerCase()
  const visibleTopics = query ? topics?.filter((topic) => topic.name.toLowerCase().includes(query)) : topics

  return (
    <div className="min-h-screen bg-bg">
      <AppHeader
        userName={user?.displayName}
        onLogout={handleLogout}
        actions={
          <>
            {user?.role === 'ADMIN' && (
              <button
                type="button"
                onClick={() => navigate('/admin')}
                aria-label="Admin"
                title="Admin"
                className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border px-3 text-sm font-semibold text-muted transition-colors hover:bg-surface-hover hover:text-fg"
              >
                <ShieldCheck size={15} />
                <span className="hidden lg:inline">Admin</span>
              </button>
            )}
            <button
              type="button"
              onClick={() => navigate('/how-it-works')}
              aria-label="How it works"
              title="How it works"
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border px-3 text-sm font-semibold text-muted transition-colors hover:bg-surface-hover hover:text-fg"
            >
              <CircleHelp size={15} />
              <span className="hidden lg:inline">How it works</span>
            </button>
            <button
              type="button"
              onClick={() => navigate('/onboarding')}
              aria-label="Profile"
              title="Profile"
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border px-3 text-sm font-semibold text-muted transition-colors hover:bg-surface-hover hover:text-fg"
            >
              <UserRoundPen size={15} />
              <span className="hidden lg:inline">Profile</span>
            </button>
          </>
        }
      />

      <PageContainer className="flex flex-col gap-8">
        <DashboardHero
          displayName={user?.displayName}
          topicCount={topicCount}
          testCount={stats.testCount}
          bestAvgScore={stats.bestAvgScore}
        >
          <NewTopicForm
            onCreate={async (name) => {
              await createMutation.mutateAsync(name).catch(() => null)
            }}
            isSubmitting={createMutation.isPending}
            error={createError}
            disabledReason={
              atTopicLimit ? `You can have up to ${topicLimit} topics. Delete a topic to add a new one.` : null
            }
            suggestions={topics ? suggestions : []}
          />
        </DashboardHero>

        {usageQuery.data && <UsageSummary usage={usageQuery.data} topicCount={topicCount} />}

        <section className="flex flex-col gap-5">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-extrabold tracking-tight text-fg sm:text-3xl">Your Topics</h1>
              <span className="rounded-full bg-gradient-to-r from-primary to-accent px-2.5 py-0.5 text-xs font-bold text-white shadow-md shadow-primary/30">
                {topicCount}
              </span>
            </div>
            {topicCount > SEARCH_THRESHOLD && (
              <div className="flex h-10 w-full items-center gap-2 rounded-xl border border-border bg-surface px-3 transition-all focus-within:border-primary/50 focus-within:ring-4 focus-within:ring-primary/10 sm:w-64">
                <Search size={15} className="shrink-0 text-muted" aria-hidden />
                <input
                  type="search"
                  aria-label="Search topics"
                  placeholder="Search topics"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="min-w-0 flex-1 bg-transparent text-sm text-fg outline-none placeholder:text-muted [&::-webkit-search-cancel-button]:hidden"
                />
                {search && (
                  <button
                    type="button"
                    onClick={() => setSearch('')}
                    aria-label="Clear search"
                    className="rounded p-0.5 text-muted transition-colors hover:text-fg"
                  >
                    <X size={14} />
                  </button>
                )}
              </div>
            )}
          </div>

          {topicsQuery.isLoading && <TopicSkeletons />}
          {topicsQuery.isError && <p className="text-sm font-medium text-danger">Could not load topics.</p>}
          {visibleTopics && topics && topics.length > 0 && visibleTopics.length === 0 ? (
            <p className="rounded-2xl border border-dashed border-border px-6 py-10 text-center text-sm text-muted">
              No topics match &ldquo;{search.trim()}&rdquo;.
            </p>
          ) : (
            visibleTopics && (
              <TopicList topics={visibleTopics} onDelete={(id) => deleteMutation.mutate(id)} deletingId={deletingId} />
            )
          )}
        </section>
      </PageContainer>
    </div>
  )
}

function TopicSkeletons() {
  return (
    <div aria-label="Loading topics" className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="h-64 animate-pulse rounded-2xl border border-border bg-surface">
          <div className="m-5 h-12 w-12 rounded-2xl bg-surface-hover" />
          <div className="mx-5 h-4 w-2/3 rounded bg-surface-hover" />
          <div className="mx-5 mt-2 h-3 w-1/3 rounded bg-surface-hover" />
        </div>
      ))}
    </div>
  )
}

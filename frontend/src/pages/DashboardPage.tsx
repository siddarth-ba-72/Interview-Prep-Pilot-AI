import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Search, X } from 'lucide-react'
import { useAppSelector } from '../hooks'
import { createTopic, deleteTopic, extractErrorMessage, listTopics, type Topic } from '../api/topics'
import { EXPERIENCE_OPTIONS } from '../api/profile'
import { trackFor } from '../features/prepTrack/tracks'
import { trackEvent } from '../features/analytics/clarity'
import NewTopicForm from '../components/NewTopicForm'
import PrepTrackExplorer from '../components/PrepTrackExplorer'
import TopicList from '../components/TopicList'
import { TEST_MAX, TEST_PASS } from '../components/TopicRow'
import AppHeader from '../components/AppHeader'
import PageContainer from '../components/PageContainer'
import Notice from '../components/ui/Notice'
import { Button } from '../components/ui/Button'

const TOPIC_IDEAS = ['System Design', 'Data Structures', 'Java', 'Python', 'SQL', 'React', 'Operating Systems', 'Docker']

/** Above this many topics the list gets a search box. */
const SEARCH_THRESHOLD = 4

export default function DashboardPage() {
  const user = useAppSelector((state) => state.auth.user)
  const queryClient = useQueryClient()
  const [createError, setCreateError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [search, setSearch] = useState('')

  const topicsQuery = useQuery({ queryKey: ['topics'], queryFn: listTopics })

  const createMutation = useMutation({
    mutationFn: createTopic,
    onSuccess: () => {
      setCreateError(null)
      trackEvent('topic_created')
      queryClient.invalidateQueries({ queryKey: ['topics'] })
    },
    onError: (error) => setCreateError(extractErrorMessage(error, 'Could not create topic')),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteTopic,
    onMutate: (topicId) => setDeletingId(topicId),
    onSettled: () => setDeletingId(null),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['topics'] })
    },
  })

  const topics = topicsQuery.data
  const topicCount = topics?.length ?? 0
  const experienceLabel = EXPERIENCE_OPTIONS.find((option) => option.value === user?.experienceLevel)?.label
  const profileChips = [experienceLabel, user?.preferredDomain].filter((chip): chip is string => Boolean(chip))

  const suggestions = useMemo(() => {
    const taken = new Set((topics ?? []).map((topic) => topic.name.toLowerCase()))
    return TOPIC_IDEAS.filter((idea) => !taken.has(idea.toLowerCase())).slice(0, 5)
  }, [topics])

  const query = search.trim().toLowerCase()
  const visibleTopics = query ? topics?.filter((topic) => topic.name.toLowerCase().includes(query)) : topics

  return (
    <div className="min-h-screen">
      <AppHeader />

      <PageContainer>
        <div className="max-w-3xl">
          <h1 className="type-title">Your topics</h1>
          <p className="type-body mt-1 text-graphite" data-clarity-mask="True">
            {topics ? summarise(topics) : ' '}
          </p>
        </div>

        <div className="mt-6 grid items-start gap-8 lg:grid-cols-[minmax(0,1fr)_320px]">
          <section aria-label="Topics" className="flex min-w-0 flex-col gap-4">
            <NewTopicForm
              onCreate={async (name) => {
                await createMutation.mutateAsync(name).catch(() => null)
              }}
              isSubmitting={createMutation.isPending}
              error={createError}
              suggestions={topics ? suggestions : []}
            />

            <div className="mt-2 flex min-h-9 flex-wrap items-center justify-between gap-3">
              <p className="type-meta">
                Average test score out of {TEST_MAX}. The tick marks the pass mark, {TEST_PASS}.
              </p>
              {topicCount > SEARCH_THRESHOLD && (
                <div className="flex h-9 w-full items-center gap-2 rounded-md border border-edge bg-sheet px-3 focus-within:border-ink focus-within:ring-1 focus-within:ring-ink sm:w-60">
                  <Search size={15} className="shrink-0 text-pencil" aria-hidden />
                  <input
                    type="search"
                    aria-label="Search topics"
                    placeholder="Search topics"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="min-w-0 flex-1 bg-transparent text-base text-ink outline-none placeholder:text-pencil sm:text-sm [&::-webkit-search-cancel-button]:hidden"
                  />
                  {search && (
                    <button type="button" onClick={() => setSearch('')} aria-label="Clear search" className="text-pencil hover:text-ink">
                      <X size={14} />
                    </button>
                  )}
                </div>
              )}
            </div>

            {topicsQuery.isLoading && <TopicSkeletons />}
            {topicsQuery.isError && (
              <Notice
                action={
                  <Button size="sm" variant="ghost" onClick={() => topicsQuery.refetch()}>
                    Retry
                  </Button>
                }
              >
                Could not load your topics.
              </Notice>
            )}
            {visibleTopics && topics && topics.length > 0 && visibleTopics.length === 0 ? (
              <p className="rounded-lg border border-dashed border-edge px-5 py-6 text-sm text-graphite">
                No topics match “{search.trim()}”.
              </p>
            ) : (
              visibleTopics && (
                <TopicList topics={visibleTopics} onDelete={(id) => deleteMutation.mutate(id)} deletingId={deletingId} />
              )
            )}
          </section>

          <aside className="flex flex-col gap-4 lg:sticky lg:top-[calc(52px+2rem)]">
            <PrepTrackExplorer current={trackFor(user?.experienceLevel)} profileChips={profileChips} showProfileLink />
            <ScoringKey />
          </aside>
        </div>
      </PageContainer>
    </div>
  )
}

/** The line under the title: what the list says, with the topics under the pass mark named. */
function summarise(topics: Topic[]): string {
  if (topics.length === 0) return 'Add a topic to start. Each one gets Learn, Test and Mock interview.'
  const tested = topics.filter((topic) => topic.avgScore !== null && topic.avgScore !== undefined)
  const tests = topics.reduce((sum, topic) => sum + (topic.testCount ?? 0), 0)
  const count = `${topics.length} ${topics.length === 1 ? 'topic' : 'topics'}`
  if (tested.length === 0) return `${count}, no tests taken yet. A test shows where you stand against the pass mark.`

  const below = tested.filter((topic) => topic.avgScore! < TEST_PASS).sort((a, b) => a.avgScore! - b.avgScore!)
  const testsTaken = `${tests} ${tests === 1 ? 'test' : 'tests'} taken`
  if (below.length === 0) return `${count}, ${testsTaken}. Every tested topic averages above the pass mark.`
  const names = below
    .slice(0, 3)
    .map((topic) => `${topic.name} (${topic.avgScore!.toFixed(1)})`)
    .join(', ')
  return `${count}, ${testsTaken}. Under the pass mark: ${names}${below.length > 3 ? ` and ${below.length - 3} more` : ''}.`
}

/** The two bars every score in the app is drawn against. */
function ScoringKey() {
  const rows = [
    { mode: 'Test', detail: '20 questions', max: TEST_MAX, pass: TEST_PASS },
    { mode: 'Mock interview', detail: 'Rated per answer', max: 100, pass: 75 },
  ]
  return (
    <section aria-label="How scores work" className="rounded-lg border border-line bg-sheet px-5 py-4">
      <h2 className="type-section">Pass marks</h2>
      <table className="mt-2 w-full text-sm">
        <tbody>
          {rows.map((row) => (
            <tr key={row.mode} className="border-b border-rule last:border-b-0">
              <td className="py-2.5">
                <span className="text-ink">{row.mode}</span>
                <span className="block text-xs text-pencil">{row.detail}</span>
              </td>
              <td className="figures py-2.5 text-right">
                <span className="font-medium text-ink">{row.pass}</span>
                <span className="text-graphite"> of {row.max}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}

function TopicSkeletons() {
  return (
    <ul aria-label="Loading topics" className="divide-y divide-rule rounded-lg border border-line bg-sheet">
      {[0, 1, 2].map((i) => (
        <li key={i} className="grid gap-3 px-5 py-4 md:grid-cols-[minmax(0,1fr)_200px_auto] md:items-center">
          <div>
            <div className="h-4 w-40 rounded bg-press" />
            <div className="mt-2 h-3 w-56 rounded bg-wash" />
          </div>
          <div className="h-1.5 rounded-full bg-press" />
          <div className="h-8 w-64 rounded-md bg-wash" />
        </li>
      ))}
    </ul>
  )
}

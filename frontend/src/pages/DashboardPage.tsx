import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useAppSelector, useAppDispatch } from '../hooks'
import { clearCredentials } from '../features/auth/authSlice'
import api from '../api/axiosInstance'
import { useNavigate } from 'react-router-dom'
import { createTopic, deleteTopic, extractErrorMessage, listTopics } from '../api/topics'
import NewTopicForm from '../components/NewTopicForm'
import TopicList from '../components/TopicList'
import AppHeader from '../components/AppHeader'
import PageContainer from '../components/PageContainer'

export default function DashboardPage() {
  const user = useAppSelector((state) => state.auth.user)
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [createError, setCreateError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const topicsQuery = useQuery({ queryKey: ['topics'], queryFn: listTopics })

  const createMutation = useMutation({
    mutationFn: createTopic,
    onSuccess: () => {
      setCreateError(null)
      queryClient.invalidateQueries({ queryKey: ['topics'] })
    },
    onError: (error) => setCreateError(extractErrorMessage(error, 'Could not create topic')),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteTopic,
    onMutate: (topicId) => setDeletingId(topicId),
    onSettled: () => setDeletingId(null),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['topics'] }),
  })

  async function handleLogout() {
    await api.post('/auth/logout').catch(() => null)
    dispatch(clearCredentials())
    navigate('/login')
  }

  const topicCount = topicsQuery.data?.length ?? 0

  return (
    <div className="min-h-screen bg-bg">
      <AppHeader userName={user?.displayName} onLogout={handleLogout} />

      <PageContainer className="flex flex-col gap-7">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight text-fg sm:text-3xl">Your Topics</h1>
            <p className="mt-1 text-sm text-muted">Create a topic, then learn, test, or mock-interview yourself on it.</p>
          </div>
          <div className="flex min-w-16 flex-col items-center rounded-xl border border-primary/20 bg-primary-subtle px-4 py-2">
            <span className="text-xl font-extrabold leading-none text-primary">{topicCount}</span>
            <span className="mt-1 text-[11px] font-semibold uppercase tracking-wide text-primary">
              {topicCount === 1 ? 'Topic' : 'Topics'}
            </span>
          </div>
        </div>

        <NewTopicForm
          onCreate={async (name) => {
            await createMutation.mutateAsync(name).catch(() => null)
          }}
          isSubmitting={createMutation.isPending}
          error={createError}
        />

        {topicsQuery.isLoading && <p className="text-sm text-muted">Loading topics...</p>}
        {topicsQuery.isError && <p className="text-sm font-medium text-danger">Could not load topics.</p>}
        {topicsQuery.data && (
          <TopicList topics={topicsQuery.data} onDelete={(id) => deleteMutation.mutate(id)} deletingId={deletingId} />
        )}
      </PageContainer>
    </div>
  )
}

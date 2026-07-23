import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useAppSelector, useAppDispatch } from '../hooks'
import { clearCredentials } from '../features/auth/authSlice'
import api from '../api/axiosInstance'
import { useNavigate } from 'react-router-dom'
import { createTopic, deleteTopic, extractErrorMessage, listTopics } from '../api/topics'
import NewTopicForm from '../components/NewTopicForm'
import TopicList from '../components/TopicList'

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

  return (
    <div className="dashboard-shell">
      <header className="dashboard-header">
        <div>
          <h1>Welcome, {user?.displayName}!</h1>
          <p className="muted-text">{user?.email}</p>
        </div>
        <button onClick={handleLogout} className="secondary-button dashboard-logout">
          Logout
        </button>
      </header>

      <section className="card dashboard-card">
        <h2>Your Topics</h2>
        <NewTopicForm
          onCreate={async (name) => {
            await createMutation.mutateAsync(name).catch(() => null)
          }}
          isSubmitting={createMutation.isPending}
          error={createError}
        />

        {topicsQuery.isLoading && <p className="muted-text">Loading topics...</p>}
        {topicsQuery.isError && <p className="error-text">Could not load topics.</p>}
        {topicsQuery.data && (
          <TopicList topics={topicsQuery.data} onDelete={(id) => deleteMutation.mutate(id)} deletingId={deletingId} />
        )}
      </section>
    </div>
  )
}

import api from './axiosInstance'
import { withRetryTime } from './usage'

export interface Topic {
  id: string
  name: string
  createdAt: string
  testCount?: number
  avgScore?: number | null
}

export async function listTopics(): Promise<Topic[]> {
  const { data } = await api.get<Topic[]>('/topics')
  return data
}

export async function createTopic(name: string): Promise<Topic> {
  const { data } = await api.post<Topic>('/topics', { name })
  return data
}

export async function getTopic(topicId: string): Promise<Topic> {
  const { data } = await api.get<Topic>(`/topics/${topicId}`)
  return data
}

export async function deleteTopic(topicId: string): Promise<void> {
  await api.delete(`/topics/${topicId}`)
}

export function extractErrorMessage(error: unknown, fallback: string): string {
  const apiError = (error as { response?: { data?: { error?: { message?: string; retryAt?: string | null } } } })
    ?.response?.data?.error
  return apiError?.message ? withRetryTime(apiError.message, apiError.retryAt) : fallback
}

import api from './axiosInstance'

export interface Topic {
  id: string
  name: string
  createdAt: string
}

export async function listTopics(): Promise<Topic[]> {
  const { data } = await api.get<Topic[]>('/topics')
  return data
}

export async function createTopic(name: string): Promise<Topic> {
  const { data } = await api.post<Topic>('/topics', { name })
  return data
}

export async function deleteTopic(topicId: string): Promise<void> {
  await api.delete(`/topics/${topicId}`)
}

export function extractErrorMessage(error: unknown, fallback: string): string {
  const message = (error as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error
    ?.message
  return message ?? fallback
}

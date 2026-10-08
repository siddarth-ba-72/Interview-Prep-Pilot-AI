import api from './axiosInstance'

/** Matches the backend's limit. */
export const FEEDBACK_MAX_LENGTH = 2000

/** Saved with the sender's name and email; only admins can read it. */
export async function submitFeedback(message: string): Promise<{ id: string; createdAt: string | null }> {
  const { data } = await api.post<{ id: string; createdAt: string | null }>('/users/me/feedback', { message })
  return data
}

import api from './axiosInstance'

export interface ChatMessage {
  role: 'USER' | 'AI'
  content: string
  timestamp: string
}

export interface ChatSession {
  topicId: string
  messages: ChatMessage[]
}

export async function getChatSession(topicId: string): Promise<ChatSession> {
  const { data } = await api.get<ChatSession>(`/topics/${topicId}/chat`)
  return data
}

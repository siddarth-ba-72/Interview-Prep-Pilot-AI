import api from './axiosInstance'

export interface ChatMessage {
  role: 'USER' | 'AI'
  content: string
  timestamp: string
}

export interface ChatSession {
  topicId: string
  messages: ChatMessage[]
  hasMore: boolean
}

export interface PagedMessages {
  messages: ChatMessage[]
  hasMore: boolean
}

export async function getChatSession(topicId: string): Promise<ChatSession> {
  const { data } = await api.get<ChatSession>(`/topics/${topicId}/chat`)
  return data
}

export async function getOlderMessages(topicId: string, before: string): Promise<PagedMessages> {
  const { data } = await api.get<PagedMessages>(`/topics/${topicId}/chat/messages`, {
    params: { before },
  })
  return data
}

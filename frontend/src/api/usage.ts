import api from './axiosInstance'

/** `availableAt` is set only while the action is locked (`remaining` is then 0). */
export interface ActionUsage {
  used: number
  limit: number
  remaining: number
  availableAt: string | null
}

export interface Usage {
  tier: 'STUDENT' | 'STANDARD'
  windowHours: number
  /** `limit` is null when the user's tier has no topic limit. */
  topics: { used: number; limit: number | null }
  learnMessages: ActionUsage
  tests: ActionUsage
  mockInterviews: ActionUsage
}

export const USAGE_QUERY_KEY = ['usage']

export async function getUsage(): Promise<Usage> {
  const { data } = await api.get<Usage>('/usage')
  return data
}

/** True while the action is used up and its lock has not lifted yet. */
export function isLocked(usage: ActionUsage | undefined): boolean {
  if (!usage || usage.remaining > 0) return false
  return usage.availableAt === null || new Date(usage.availableAt) > new Date()
}

/** "today at 6:00 PM" / "tomorrow at 6:00 PM", in the viewer's own time zone. */
export function formatAvailableAt(iso: string): string {
  const at = new Date(iso)
  const time = at.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
  const now = new Date()
  if (at.toDateString() === now.toDateString()) return `today at ${time}`
  const tomorrow = new Date(now)
  tomorrow.setDate(now.getDate() + 1)
  if (at.toDateString() === tomorrow.toDateString()) return `tomorrow at ${time}`
  return at.toLocaleString(undefined, { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
}

/** Adds when the user can try again to a usage-limit error message. */
export function withRetryTime(message: string, retryAt?: string | null): string {
  return retryAt ? `${message} You can try again ${formatAvailableAt(retryAt)}.` : message
}

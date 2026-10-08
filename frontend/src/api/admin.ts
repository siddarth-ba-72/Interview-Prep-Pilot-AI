import api from './axiosInstance'
import type { ProfileExperience, Role } from './profile'

/** Read-only admin views. Users come from user-service, activity counts from topic-service. */

export interface AdminUser {
  id: string
  email: string
  displayName: string | null
  authProvider: 'LOCAL' | 'GOOGLE'
  experienceLevel: ProfileExperience | null
  preferredDomain: string | null
  role: Role
  createdAt: string | null
}

export interface AdminUserPage {
  users: AdminUser[]
  page: number
  size: number
  /** Every user matching the search, across all pages. */
  total: number
}

/** `completed` includes interviews whose time ran out. */
export interface SessionCounts {
  active: number
  completed: number
}

export interface ActivitySummary {
  topics: number
  tests: SessionCounts
  interviews: SessionCounts
}

export interface UserActivity {
  userId: string
  topics: number
  tests: SessionCounts
  interviews: SessionCounts
}

export interface TopicActivity {
  name: string
  tests: SessionCounts
  interviews: SessionCounts
}

export interface UserActivityDetail {
  userId: string
  topics: TopicActivity[]
  /** Sessions of topics the user has deleted; null when there are none. */
  deletedTopics: { tests: SessionCounts; interviews: SessionCounts } | null
  /** Totals over all sessions, deleted topics included. */
  tests: SessionCounts
  interviews: SessionCounts
}

export async function listAdminUsers(params: { q: string; page: number; size: number }): Promise<AdminUserPage> {
  const { data } = await api.get<AdminUserPage>('/admin/users', {
    params: { q: params.q || undefined, page: params.page, size: params.size },
  })
  return data
}

export async function getAdminUser(userId: string): Promise<AdminUser> {
  const { data } = await api.get<AdminUser>(`/admin/users/${encodeURIComponent(userId)}`)
  return data
}

export async function getAdminUserStats(): Promise<{ totalUsers: number }> {
  const { data } = await api.get<{ totalUsers: number }>('/admin/users/stats')
  return data
}

export async function getActivitySummary(): Promise<ActivitySummary> {
  const { data } = await api.get<ActivitySummary>('/admin/activity/summary')
  return data
}

export async function getUsersActivity(userIds: string[]): Promise<UserActivity[]> {
  const { data } = await api.get<UserActivity[]>('/admin/activity/users', { params: { ids: userIds.join(',') } })
  return data
}

export async function getUserActivity(userId: string): Promise<UserActivityDetail> {
  const { data } = await api.get<UserActivityDetail>(`/admin/activity/users/${encodeURIComponent(userId)}`)
  return data
}

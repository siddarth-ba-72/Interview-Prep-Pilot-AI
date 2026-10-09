import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import Clarity from '@microsoft/clarity'
import { getClarityProjectId } from '../../api/config'
import { useAppSelector } from '../../hooks'

// Clarity's methods call window.clarity directly, so nothing is called unless init ran
let enabled = false

export function initClarity(): void {
  const projectId = getClarityProjectId()
  if (!projectId) return
  Clarity.init(projectId)
  enabled = true
}

export type ClarityEvent =
  | 'topic_created'
  | 'learn_message_sent'
  | 'test_started'
  | 'test_submitted'
  | 'interview_started'
  | 'interview_completed'
  | 'feedback_sent'
  | 'usage_limit_reached'
  | 'topic_limit_reached'

export function trackEvent(name: ClarityEvent): void {
  if (enabled) Clarity.event(name)
}

/** Records the API error codes for hitting a usage limit; any other code is ignored. */
export function trackLimitError(code: unknown): void {
  if (code === 'USAGE_LIMIT_REACHED') trackEvent('usage_limit_reached')
  else if (code === 'TOPIC_LIMIT_REACHED') trackEvent('topic_limit_reached')
}

/** Ties recordings to the signed-in user. Sends the user id and tags only, never name or email.
 * Clarity wants identify on every page, so it runs again on each route change. */
export function ClarityIdentify(): null {
  const { pathname } = useLocation()
  const user = useAppSelector((state) => state.auth.user)
  const userId = user?.id
  const experience = user?.experienceLevel ?? 'UNKNOWN'
  const role = user?.role

  useEffect(() => {
    if (!enabled || !userId || !role) return
    Clarity.identify(userId)
    Clarity.setTag('experience', experience)
    Clarity.setTag('role', role)
  }, [pathname, userId, experience, role])

  return null
}

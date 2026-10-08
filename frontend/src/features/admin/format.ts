import type { AdminUser } from '../../api/admin'
import { EXPERIENCE_OPTIONS } from '../../api/profile'

export function experienceLabel(level: AdminUser['experienceLevel']): string {
  if (!level) return 'Not answered'
  return EXPERIENCE_OPTIONS.find((option) => option.value === level)?.label ?? level
}

export function providerLabel(provider: AdminUser['authProvider']): string {
  return provider === 'GOOGLE' ? 'Google' : 'Email'
}

export function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

export function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

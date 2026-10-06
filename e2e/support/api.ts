import { expect, type APIRequestContext } from '@playwright/test'

export const API = '/api/v1'

export interface Account {
  email: string
  password: string
  displayName: string
}

export type ExperienceLevel = 'STUDENT' | 'YEARS_0_3' | 'YEARS_3_5' | 'YEARS_5_8' | 'YEARS_8_13' | 'YEARS_13_PLUS'

/** A fresh, unique account. Test accounts use example.com, which can never receive mail. */
export function newAccount(label: string): Account {
  const id = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 7)}`
  return {
    email: `e2e-${label}-${id}@example.com`,
    password: 'Loadtest-password-1',
    displayName: `E2E ${label} ${id}`,
  }
}

/**
 * Registers the account and answers the onboarding questionnaire through the API, so the account
 * lands straight on the dashboard. The browser then signs in through the real login form.
 * Not a STUDENT by default: students may only create 2 topics.
 */
export async function createOnboardedAccount(
  request: APIRequestContext,
  account: Account,
  experienceLevel: ExperienceLevel = 'YEARS_3_5',
): Promise<void> {
  const register = await request.post(`${API}/auth/register`, { data: account })
  expect(register.status(), `register ${account.email}: ${await register.text()}`).toBe(201)

  const login = await request.post(`${API}/auth/login`, {
    data: { email: account.email, password: account.password },
  })
  expect(login.ok(), `login ${account.email}: ${await login.text()}`).toBeTruthy()
  const { accessToken } = (await login.json()) as { accessToken: string }

  const profile = await request.put(`${API}/users/me/profile`, {
    data: { preferredDomain: 'Backend', experienceLevel },
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  expect(profile.ok(), `onboarding ${account.email}: ${await profile.text()}`).toBeTruthy()
}

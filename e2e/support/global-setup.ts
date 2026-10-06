import type { FullConfig } from '@playwright/test'

/** Fails fast with a useful message when the stack isn't up, instead of 40 timed-out tests. */
export default async function globalSetup(config: FullConfig) {
  const baseURL = config.projects[0].use.baseURL ?? 'http://localhost:3000'
  try {
    const response = await fetch(new URL('/api/v1/auth/refresh', baseURL), { method: 'POST' })
    // Without a refresh cookie the backend answers 401: that proves the frontend proxy, the
    // gateway and user-service are all reachable.
    if (response.status >= 500) {
      throw new Error(`the backend answered ${response.status}`)
    }
  } catch (error) {
    throw new Error(
      `PrepPilot is not reachable at ${baseURL} (${(error as Error).message}).\n` +
        'Start the isolated test stack first:\n' +
        '  docker compose -f loadtest/docker-compose.yml up --build -d --wait\n' +
        'or point E2E_BASE_URL at a running frontend.',
    )
  }
}

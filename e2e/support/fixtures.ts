import { test as base, expect, type Page } from '@playwright/test'
import { createOnboardedAccount, newAccount, type Account } from './api'
import { signIn } from './app'

/** Timings a test records; the timing reporter aggregates them across all tests and workers. */
export class Metrics {
  readonly values: Record<string, number[]> = {}

  record(name: string, ms: number): void {
    ;(this.values[name] ??= []).push(Math.round(ms))
  }

  async time<T>(name: string, action: () => Promise<T>): Promise<T> {
    const started = Date.now()
    const result = await action()
    this.record(name, Date.now() - started)
    return result
  }
}

type TestFixtures = {
  /** A page already signed in (through the login form) as this worker's account. */
  signedInPage: Page
  metrics: Metrics
}

type WorkerFixtures = {
  /** One onboarded account per worker, created through the API. */
  account: Account
}

export const test = base.extend<TestFixtures, WorkerFixtures>({
  account: [
    async ({ playwright }, use, workerInfo) => {
      const request = await playwright.request.newContext({ baseURL: workerInfo.project.use.baseURL })
      const account = newAccount(`w${workerInfo.workerIndex}`)
      await createOnboardedAccount(request, account)
      await request.dispose()
      await use(account)
    },
    { scope: 'worker' },
  ],

  signedInPage: async ({ page, account }, use) => {
    // Every test signs in fresh: the refresh token rotates on each use, so a saved session
    // would be stale by the second test.
    await signIn(page, account)
    await use(page)
  },

  metrics: async ({}, use, testInfo) => {
    const metrics = new Metrics()
    await use(metrics)
    if (Object.keys(metrics.values).length > 0) {
      await testInfo.attach('metrics', { body: JSON.stringify(metrics.values), contentType: 'application/json' })
    }
  },
})

export { expect }

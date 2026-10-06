import { defineConfig, devices } from '@playwright/test'

/**
 * Two projects share the same helpers:
 * - e2e:  functional tests of every user flow (`npm test`)
 * - load: realistic user journeys that record timings, meant to run with many workers
 *         (`npm run load -- --workers=10 --repeat-each=5`); the timing reporter prints p50/p95.
 *
 * Both expect a running stack, by default the isolated one in loadtest/docker-compose.yml.
 */
const baseURL = process.env.E2E_BASE_URL ?? 'http://localhost:3000'

export default defineConfig({
  globalSetup: './support/global-setup.ts',
  // AI steps are slow on purpose: the fake LLM answers at real gpt-4o-mini speed, and generating
  // a 20-question test takes 30-50 seconds.
  timeout: 4 * 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [
    ['list'],
    ['html', { open: 'never' }],
    ['./support/timing-reporter.ts', { outputFile: 'load-results/summary.json' }],
  ],
  use: {
    ...devices['Desktop Chrome'],
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'e2e',
      testDir: './tests',
    },
    {
      name: 'load',
      testDir: './load',
      retries: 0,
      timeout: 10 * 60_000,
      // Recording costs CPU on the load generator and skews its timings.
      use: { trace: 'off', screenshot: 'off', video: 'off' },
    },
  ],
})

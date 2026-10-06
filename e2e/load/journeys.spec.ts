/**
 * Browser load test: real users going through Learn, Test and Mock Interview, with pauses to read
 * and type. Every worker is one concurrent user with its own account; each test is one session.
 *
 *   npm run load -- --workers=10 --repeat-each=5
 *
 * The timing reporter prints p50/p90/p95/max per step at the end and writes
 * load-results/summary.json. Pair it with a protocol-level tool (Locust, k6) for higher load:
 * a browser per virtual user is expensive, so this measures what users experience while the
 * other tool provides the volume.
 */
import { test } from '../support/fixtures'
import {
  LONG_ANSWER,
  SHORT_ANSWER,
  answerAllTestQuestions,
  answerInterviewQuestion,
  createTopic,
  endInterview,
  goToNextInterviewQuestion,
  openLearn,
  openTest,
  sendChatMessage,
  signIn,
  startInterview,
  submitTest,
  uniqueTopic,
} from '../support/app'
import type { Page } from '@playwright/test'

const THINK_TIME_MS = Number(process.env.LOAD_THINK_TIME_MS ?? 2000)

const LEARN_MESSAGES = [
  'A deep dive please, focused on interview questions.',
  'Can you show me a code example?',
  'What is the difference between the two approaches you mentioned?',
  'Quiz me on what we just covered.',
]

test.beforeAll(({}, testInfo) => {
  // Every journey makes several AI calls. Against a deployment that uses the real LLM, a load
  // test spends real money, so only local targets are allowed unless explicitly overridden.
  const host = new URL(testInfo.project.use.baseURL ?? 'http://localhost:3000').hostname
  if (!['localhost', '127.0.0.1', '[::1]'].includes(host) && process.env.E2E_ALLOW_REMOTE !== '1') {
    throw new Error(
      `Refusing to load-test ${host}. Set E2E_ALLOW_REMOTE=1 only if that deployment's ai-service uses the fake LLM.`,
    )
  }
})

/** A human pause between actions: 0.5x to 1.5x the configured think time. */
async function think(page: Page): Promise<void> {
  await page.waitForTimeout(THINK_TIME_MS * (0.5 + Math.random()))
}

test('learner studies a topic in Learn Mode', async ({ page, account, metrics }) => {
  await metrics.time('auth.sign_in', () => signIn(page, account))
  const card = await metrics.time('topic.create', () => createTopic(page, uniqueTopic('Load Learn')))
  await metrics.time('learn.open', () => openLearn(page, card))

  for (const message of LEARN_MESSAGES) {
    await think(page)
    const { firstTokenMs, replyMs } = await sendChatMessage(page, message)
    metrics.record('learn.first_token', firstTokenMs)
    metrics.record('learn.full_reply', replyMs)
  }
})

test('candidate takes a test', async ({ page, account, metrics }) => {
  await metrics.time('auth.sign_in', () => signIn(page, account))
  const card = await metrics.time('topic.create', () => createTopic(page, uniqueTopic('Load Test')))
  await metrics.time('test.generate', () => openTest(page, card))

  await think(page)
  await answerAllTestQuestions(page)
  await metrics.time('test.grade', () => submitTest(page))
})

test('candidate does a mock interview', async ({ page, account, metrics }) => {
  await metrics.time('auth.sign_in', () => signIn(page, account))
  const card = await metrics.time('topic.create', () => createTopic(page, uniqueTopic('Load Interview')))
  await metrics.time('interview.start', () => startInterview(page, card))

  for (const answer of [LONG_ANSWER, SHORT_ANSWER, LONG_ANSWER]) {
    await think(page)
    await metrics.time('interview.turn', () => answerInterviewQuestion(page, answer))
    await goToNextInterviewQuestion(page)
  }
  await metrics.time('interview.report', () => endInterview(page))
})

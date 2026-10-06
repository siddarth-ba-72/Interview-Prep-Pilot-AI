import { expect, type Locator, type Page } from '@playwright/test'
import type { Account } from './api'

/** Ceiling for anything that waits on the AI. Generating a test at realistic speed takes 30-50s. */
export const AI_TIMEOUT = Number(process.env.E2E_AI_TIMEOUT_MS ?? 120_000)

export const LONG_ANSWER =
  'I would start from the requirement and the failure modes. Concretely, I would keep each component focused on ' +
  'one responsibility, validate input at the boundary, and make retried operations idempotent so a repeat is ' +
  'safe. For example, in a payment flow I would store an idempotency key per request. I would cover the logic ' +
  'with unit tests, the database boundary with integration tests, and watch latency percentiles and error rates ' +
  'in production so a regression shows up within minutes. The main trade-off is extra upfront design.'

export const SHORT_ANSWER = "I'm not sure, no idea."

/** A topic name no other test or worker will use. */
export function uniqueTopic(base: string): string {
  return `${base} ${Math.random().toString(36).slice(2, 7)}`
}

/** Throws with the page's error message if one is showing. */
async function failOnAlert(page: Page, what: string): Promise<void> {
  const alert = page.getByRole('alert')
  if ((await alert.count()) > 0) {
    throw new Error(`${what}: ${(await alert.first().innerText()).trim()}`)
  }
}

export async function signIn(page: Page, account: Account): Promise<void> {
  // On load the app tries a silent refresh. Wait for it to fail before submitting: a refresh
  // that answers after a successful login would sign the user straight back out.
  const silentRefresh = page.waitForResponse((r) => r.url().includes('/auth/refresh'))
  await page.goto('/login')
  await silentRefresh

  await page.getByLabel('Email').fill(account.email)
  await page.getByLabel('Password').fill(account.password)
  await page.getByRole('button', { name: 'Sign In' }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
  await expect(page.getByRole('heading', { name: 'Your Topics' })).toBeVisible()
}

export function topicCard(page: Page, name: string): Locator {
  // The card is the element that directly contains the topic's heading.
  return page.getByRole('heading', { name, exact: true }).locator('..')
}

export async function createTopic(page: Page, name: string): Promise<Locator> {
  const input = page.getByPlaceholder('e.g. Spring Boot, Python, DevOps')
  await input.fill(name)
  await input.press('Enter')
  const card = topicCard(page, name)
  await expect(card).toBeVisible()
  return card
}

// ------------------------------------------------------------------------------- Learn Mode

export function chatInput(page: Page): Locator {
  return page.getByPlaceholder('Type your message...')
}

export function aiMessages(page: Page): Locator {
  return page.getByTestId('chat-message-ai')
}

/** Opens Learn Mode and waits for the AI's opening clarifying questions. */
export async function openLearn(page: Page, card: Locator): Promise<void> {
  await card.getByRole('button', { name: 'Learn', exact: true }).click()
  await expect(page).toHaveURL(/\/learn$/)
  await expect(aiMessages(page).first().or(page.getByRole('alert'))).toBeVisible({ timeout: AI_TIMEOUT })
  await failOnAlert(page, 'Opening Learn Mode failed')
  await expect(chatInput(page)).toBeEnabled()
}

/**
 * Sends a Learn message and waits for the full streamed reply. Returns the time until the first
 * token was on screen and the time until the reply was complete, both as the user saw them.
 * Fails straight away with the on-screen error if the reply fails.
 */
export async function sendChatMessage(page: Page, text: string): Promise<{ firstTokenMs: number; replyMs: number }> {
  const repliesBefore = await aiMessages(page).count()
  const sentBefore = await page.getByTestId('chat-message-user').count()
  const input = chatInput(page)
  await input.fill(text)

  const started = Date.now()
  await input.press('Enter')
  await expect(page.getByTestId('chat-message-user')).toHaveCount(sentBefore + 1)
  await page.waitForFunction(
    (count) => {
      const streaming = document.querySelector('[data-testid="chat-message-streaming"]')
      if (streaming) return !streaming.textContent?.includes('Thinking...')
      // The stream is already over: a very fast reply, or an error.
      return (
        document.querySelectorAll('[data-testid="chat-message-ai"]').length > count ||
        document.querySelector('[role="alert"]') !== null
      )
    },
    repliesBefore,
    { timeout: AI_TIMEOUT },
  )
  const firstTokenMs = Date.now() - started

  // The input unlocks when the stream ends, whether the reply arrived or failed.
  await expect(input).toBeEnabled({ timeout: AI_TIMEOUT })
  await failOnAlert(page, 'Learn reply failed')
  await expect(aiMessages(page)).toHaveCount(repliesBefore + 1)
  return { firstTokenMs, replyMs: Date.now() - started }
}

/** The "N of M Learn messages left" counter, as a number. */
export async function learnMessagesLeft(page: Page): Promise<number> {
  const counter = page.getByText(/\d+ of \d+ Learn messages left/)
  await expect(counter).toBeVisible()
  return Number((await counter.textContent())!.match(/(\d+) of/)![1])
}

// -------------------------------------------------------------------------------- Test Mode

/** Opens Test Mode and waits until the AI has generated the questions. */
export async function openTest(page: Page, card: Locator): Promise<void> {
  await card.getByRole('button', { name: 'Test', exact: true }).click()
  await expect(page).toHaveURL(/\/test$/)
  const ready = page.getByText(/^Attempt #\d+$/)
  await expect(ready.or(page.getByRole('alert'))).toBeVisible({ timeout: AI_TIMEOUT })
  await failOnAlert(page, 'Test generation failed')
}

/**
 * Answers every question, so submitting doesn't open a confirm() dialog. Picks varied MCQ options
 * and alternates long and short subjective answers, so the report has strengths and weaknesses.
 */
export async function answerAllTestQuestions(page: Page): Promise<void> {
  const questions = page.getByRole('heading', { name: /^Question \d+$/ }).locator('..')
  await expect(questions).toHaveCount(20)

  for (let i = 0; i < 20; i++) {
    const question = questions.nth(i)
    const options = question.getByRole('radio')
    if ((await options.count()) > 0) {
      await options.nth(i % 4).check()
    } else {
      await question.getByPlaceholder('Enter your answer here...').fill(i % 2 === 0 ? LONG_ANSWER : 'It depends.')
    }
  }
  await expect(page.getByText('20 of 20 questions answered')).toBeVisible()
}

/** Submits the test and waits for the AI to grade it. */
export async function submitTest(page: Page): Promise<void> {
  await page.getByRole('button', { name: 'Submit Test' }).click()
  const results = page.getByRole('heading', { name: 'Test Results' })
  await expect(results.or(page.getByRole('alert'))).toBeVisible({ timeout: AI_TIMEOUT })
  await failOnAlert(page, 'Grading the test failed')
}

// --------------------------------------------------------------------------- Mock Interview

export function interviewAnswerBox(page: Page): Locator {
  return page.getByPlaceholder('Answer as you would out loud in a real interview…')
}

/** Starts an interview with the default setup and waits for the opening question. */
export async function startInterview(page: Page, card: Locator): Promise<void> {
  await card.getByRole('button', { name: 'Mock Interview' }).click()
  await expect(page.getByRole('heading', { name: 'Choose your interview setup' })).toBeVisible()
  const start = page.getByRole('button', { name: /^(Start interview|Start a new interview)$/ })
  await expect(start).toBeEnabled()
  await start.click()
  await expect(interviewAnswerBox(page)).toBeVisible({ timeout: AI_TIMEOUT })
}

/** Submits an answer and waits for the AI's rating. Returns the rating label shown. */
export async function answerInterviewQuestion(page: Page, answer: string): Promise<string> {
  await interviewAnswerBox(page).fill(answer)
  await page.getByRole('button', { name: 'Submit answer' }).click()
  const feedback = page.getByRole('heading', { name: 'Feedback on your answer' }).locator('..')
  await expect(feedback).toBeVisible({ timeout: AI_TIMEOUT })
  const rating = feedback.getByText(/^(Strong|Satisfactory|Needs work)$/)
  await expect(rating).toBeVisible()
  return (await rating.textContent())!.trim()
}

export async function goToNextInterviewQuestion(page: Page): Promise<void> {
  await page.getByRole('button', { name: 'Next question' }).click()
  await expect(interviewAnswerBox(page)).toBeVisible()
}

/** Ends the interview early and waits for the AI-written report. */
export async function endInterview(page: Page): Promise<void> {
  await page.getByRole('button', { name: 'End interview' }).click()
  await page.getByRole('button', { name: 'Yes, end it' }).click()
  await expect(page).toHaveURL(/\/interviews\/[^/]+\/report$/, { timeout: AI_TIMEOUT })
  await expect(page.getByRole('heading', { name: 'Overall assessment' })).toBeVisible()
}

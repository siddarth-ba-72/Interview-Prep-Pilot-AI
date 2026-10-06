import { test, expect } from '../support/fixtures'
import { answerAllTestQuestions, createTopic, openTest, submitTest, topicCard, uniqueTopic } from '../support/app'

test('a generated test can be answered, graded and reviewed', async ({ signedInPage: page }) => {
  const name = uniqueTopic('Java')
  const card = await createTopic(page, name)
  await openTest(page, card)

  await expect(page.getByText('Attempt #1')).toBeVisible()
  await expect(page.getByRole('radio')).toHaveCount(40)
  await expect(page.getByPlaceholder('Enter your answer here...')).toHaveCount(10)

  await answerAllTestQuestions(page)
  await submitTest(page)

  const results = page.getByRole('heading', { name: 'Test Results' }).locator('..')
  // Wrong MCQ answers cost points, so a score can be negative.
  await expect(results.getByText(/^-?\d+ \/ \d+$/).first()).toBeVisible()

  await results.getByRole('button', { name: 'View Full Report' }).click()
  await expect(page.getByRole('heading', { name: 'Score Summary' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Question Breakdown' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Strengths' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Areas for Improvement' })).toBeVisible()
})

test('a finished test shows up in the history and its report survives a reload', async ({ signedInPage: page }) => {
  const name = uniqueTopic('TypeScript')
  const card = await createTopic(page, name)
  await openTest(page, card)
  await answerAllTestQuestions(page)
  await submitTest(page)
  await page.getByRole('button', { name: 'Dismiss' }).click()

  await page.goto('/dashboard')
  await topicCard(page, name).getByRole('button', { name: 'Test history' }).click()
  await expect(page.getByRole('cell', { name: /\/60/ })).toHaveCount(1)
  await page.getByRole('button', { name: 'View Report' }).click()
  await expect(page.getByRole('heading', { name: 'Score Summary' })).toBeVisible()

  // Loaded from the server this time, not from the in-memory copy the test page left behind.
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Score Summary' })).toBeVisible({ timeout: 30_000 })
})

test('a re-test focuses on the weak areas of the previous attempt', async ({ signedInPage: page }) => {
  const name = uniqueTopic('Rust')
  const card = await createTopic(page, name)
  await openTest(page, card)
  await answerAllTestQuestions(page)
  await submitTest(page)

  await page.goto('/dashboard')
  await openTest(page, topicCard(page, name))
  await expect(page.getByText('Attempt #2')).toBeVisible()
  await expect(page.getByText('Focused on your weak areas from last attempt')).toBeVisible()
})

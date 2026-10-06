import { test, expect } from '../support/fixtures'
import {
  LONG_ANSWER,
  SHORT_ANSWER,
  answerInterviewQuestion,
  createTopic,
  endInterview,
  goToNextInterviewQuestion,
  interviewAnswerBox,
  startInterview,
  topicCard,
  uniqueTopic,
} from '../support/app'

test('a mock interview grades each answer and ends with a report', async ({ signedInPage: page }) => {
  const card = await createTopic(page, uniqueTopic('Spring Boot'))
  await startInterview(page, card)

  const firstQuestion = await page.getByTestId('interview-question').textContent()
  expect(firstQuestion?.trim().length).toBeGreaterThan(20)

  expect(await answerInterviewQuestion(page, LONG_ANSWER)).toBe('Strong')
  await goToNextInterviewQuestion(page)
  // A strong answer earns a follow-up on the same theme.
  await expect(page.getByText('Follow-up', { exact: true })).toBeVisible()

  expect(await answerInterviewQuestion(page, SHORT_ANSWER)).toBe('Needs work')
  await goToNextInterviewQuestion(page)
  await expect(page.getByText('2 answered')).toBeVisible()

  await endInterview(page)
  await expect(page.getByRole('heading', { name: 'Areas to improve' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'How a stronger candidate would have answered' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Question breakdown' })).toBeVisible()
})

test('an interview in progress can be resumed after leaving the page', async ({ signedInPage: page }) => {
  const name = uniqueTopic('Terraform')
  const card = await createTopic(page, name)
  await startInterview(page, card)
  const question = (await page.getByTestId('interview-question').textContent())?.trim()

  await page.goto('/dashboard')
  await topicCard(page, name).getByRole('button', { name: 'Mock Interview' }).click()
  await expect(page.getByText('You have an interview in progress')).toBeVisible()
  await page.getByRole('button', { name: 'Resume interview' }).click()

  await expect(interviewAnswerBox(page)).toBeVisible()
  await expect(page.getByTestId('interview-question')).toHaveText(question!)
})

test('ending an interview before answering still produces a report', async ({ signedInPage: page }) => {
  const card = await createTopic(page, uniqueTopic('Elasticsearch'))
  await startInterview(page, card)
  await endInterview(page)
})

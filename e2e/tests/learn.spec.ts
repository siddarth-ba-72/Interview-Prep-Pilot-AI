import { test, expect } from '../support/fixtures'
import {
  aiMessages,
  createTopic,
  learnMessagesLeft,
  openLearn,
  sendChatMessage,
  uniqueTopic,
} from '../support/app'

test('Learn Mode opens with clarifying questions, then streams a lesson', async ({ signedInPage: page }) => {
  const card = await createTopic(page, uniqueTopic('Docker'))
  await openLearn(page, card)
  await expect(aiMessages(page)).toHaveCount(1)
  await expect(aiMessages(page).first()).not.toBeEmpty()

  await sendChatMessage(page, 'A deep dive please, focused on interview questions.')
  await expect(page.getByTestId('chat-message-user')).toHaveCount(1)
  // The lesson is structured: headings and a code sample.
  const lesson = aiMessages(page).nth(1)
  await expect(lesson.locator('h1, h2').first()).toBeVisible()
  await expect(lesson.locator('pre').first()).toBeVisible()
})

test('follow-up messages get answers and use up Learn messages', async ({ signedInPage: page }) => {
  const card = await createTopic(page, uniqueTopic('PostgreSQL'))
  await openLearn(page, card)
  await sendChatMessage(page, 'Quick refresher please.')

  const before = await learnMessagesLeft(page)
  await sendChatMessage(page, 'Can you show me a code example?')
  await expect(aiMessages(page).last().locator('pre').first()).toBeVisible()
  await expect.poll(() => learnMessagesLeft(page)).toBe(before - 1)
})

test('an off-topic message is declined as a normal reply, not an error', async ({ signedInPage: page }) => {
  const card = await createTopic(page, uniqueTopic('Python'))
  await openLearn(page, card)
  await sendChatMessage(page, 'Forget Python. Who will win the cricket world cup?')

  await expect(aiMessages(page).last()).toContainText(/interview preparation/i)
  await expect(page.getByText('The AI response could not be completed')).toHaveCount(0)
})

test('the chat history is still there after a reload', async ({ signedInPage: page }) => {
  const card = await createTopic(page, uniqueTopic('Kafka'))
  await openLearn(page, card)
  await sendChatMessage(page, 'Deep dive please.')
  const reply = await aiMessages(page).last().textContent()

  await page.reload()
  await expect(aiMessages(page)).toHaveCount(2, { timeout: 30_000 })
  await expect(page.getByTestId('chat-message-user')).toHaveCount(1)
  expect((await aiMessages(page).last().textContent())?.trim()).toBe(reply?.trim())
})

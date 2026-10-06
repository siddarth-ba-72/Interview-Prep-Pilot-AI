import { test, expect } from '../support/fixtures'
import { createTopic, topicCard, uniqueTopic } from '../support/app'

test('the dashboard shows usage limits', async ({ signedInPage: page }) => {
  const usage = page.getByRole('region', { name: 'Usage limits' })
  await expect(usage).toBeVisible()
})

test('a topic can be created and deleted', async ({ signedInPage: page }) => {
  const name = uniqueTopic('Kubernetes')
  const card = await createTopic(page, name)
  await expect(card.getByRole('button', { name: 'Learn', exact: true })).toBeVisible()
  await expect(card.getByRole('button', { name: 'Test', exact: true })).toBeVisible()
  await expect(card.getByRole('button', { name: 'Mock Interview' })).toBeVisible()

  // Deleting takes two clicks: the X, then Confirm.
  await card.getByRole('button').first().click()
  await card.getByRole('button', { name: 'Confirm' }).click()
  await expect(topicCard(page, name)).toHaveCount(0)
})

test('a topic name can only be used once', async ({ signedInPage: page }) => {
  const name = uniqueTopic('Redis')
  await createTopic(page, name)

  const input = page.getByPlaceholder('e.g. Spring Boot, Python, DevOps')
  await input.fill(name)
  await input.press('Enter')
  await expect(page.locator('p.text-danger')).toBeVisible()
  await expect(page.getByRole('heading', { name, exact: true })).toHaveCount(1)
})

test('topics persist across sessions', async ({ signedInPage: page }) => {
  const name = uniqueTopic('GraphQL')
  await createTopic(page, name)
  await page.reload()
  await expect(topicCard(page, name)).toBeVisible()
})

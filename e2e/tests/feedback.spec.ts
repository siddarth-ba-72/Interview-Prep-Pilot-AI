import { test, expect } from '../support/fixtures'

test('feedback can be sent from the header, more than once', async ({ signedInPage: page }) => {
  await page.getByRole('button', { name: 'Send feedback' }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog.getByRole('heading', { name: 'Send feedback' })).toBeVisible()

  const send = dialog.getByRole('button', { name: 'Send', exact: true })
  await expect(send).toBeDisabled()
  await dialog.getByLabel('Your feedback').fill('   ')
  await expect(send).toBeDisabled()

  for (const message of ['The interview timer feels too short.', 'Dark mode looks great.']) {
    await dialog.getByLabel('Your feedback').fill(message)
    const saved = page.waitForResponse((r) => r.url().endsWith('/users/me/feedback') && r.request().method() === 'POST')
    await send.click()
    expect((await saved).status()).toBe(201)
    await expect(dialog.getByRole('heading', { name: 'Thanks for your feedback' })).toBeVisible()
    await dialog.getByRole('button', { name: 'Send more' }).click()
    await expect(dialog.getByLabel('Your feedback')).toHaveValue('')
  }

  await dialog.getByRole('button', { name: 'Cancel' }).click()
  await expect(dialog).toHaveCount(0)
})

test('a draft survives closing the feedback modal', async ({ signedInPage: page }) => {
  await page.getByRole('button', { name: 'Send feedback' }).click()
  await page.getByRole('dialog').getByLabel('Your feedback').fill('Half-written thought')
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toHaveCount(0)

  await page.getByRole('button', { name: 'Send feedback' }).click()
  await expect(page.getByRole('dialog').getByLabel('Your feedback')).toHaveValue('Half-written thought')
})

test('only admins can open the feedback inbox', async ({ signedInPage: page }) => {
  await page.goto('/admin/feedback')
  await expect(page).toHaveURL(/\/dashboard$/)
})

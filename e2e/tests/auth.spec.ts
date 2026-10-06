import { test, expect } from '../support/fixtures'
import { newAccount } from '../support/api'
import { signIn } from '../support/app'

test('a new user registers, answers onboarding and reaches the dashboard', async ({ page }) => {
  const account = newAccount('register')

  await page.goto('/register')
  await page.getByLabel('Display name').fill(account.displayName)
  await page.getByLabel('Email').fill(account.email)
  await page.getByLabel('Password').fill(account.password)
  await page.getByRole('button', { name: 'Register' }).click()

  await expect(page).toHaveURL(/\/onboarding$/)
  await expect(page.getByRole('heading', { name: 'Tell us about yourself' })).toBeVisible()
  const continueButton = page.getByRole('button', { name: 'Continue' })
  await expect(continueButton).toBeDisabled()

  await page.getByRole('button', { name: 'Backend', exact: true }).click()
  await page.getByRole('button', { name: /^3-5 years/ }).click()
  await continueButton.click()

  await expect(page).toHaveURL(/\/dashboard$/)
  await expect(page.getByRole('heading', { name: 'Your Topics' })).toBeVisible()
  await expect(page.getByText('No topics yet. Add one above to get started.')).toBeVisible()
})

test('registering an email twice is refused', async ({ page, account }) => {
  await page.goto('/register')
  await page.getByLabel('Display name').fill('Someone Else')
  await page.getByLabel('Email').fill(account.email)
  await page.getByLabel('Password').fill('Another-password-1')
  await page.getByRole('button', { name: 'Register' }).click()

  await expect(page).toHaveURL(/\/register$/)
  await expect(page.locator('form p.text-danger')).toBeVisible()
})

test('a wrong password shows an error and stays on the login page', async ({ page, account }) => {
  await page.goto('/login')
  await page.getByLabel('Email').fill(account.email)
  await page.getByLabel('Password').fill('definitely-wrong-password')
  await page.getByRole('button', { name: 'Sign In' }).click()

  await expect(page.getByText('Invalid email or password.')).toBeVisible()
  await expect(page).toHaveURL(/\/login$/)
})

test('the session survives a page reload', async ({ signedInPage: page }) => {
  // The access token lives only in memory; the reload recovers it from the refresh cookie.
  await page.reload()
  await expect(page).toHaveURL(/\/dashboard$/)
  await expect(page.getByRole('heading', { name: 'Your Topics' })).toBeVisible()
})

test('signing out ends the session', async ({ signedInPage: page, account }) => {
  await page.getByRole('button', { name: 'Sign out' }).click()
  await expect(page).toHaveURL(/\/login$/)

  await page.goto('/dashboard')
  await expect(page).toHaveURL(/\/login$/)

  // And signing back in still works.
  await signIn(page, account)
})

test('protected pages redirect to login when signed out', async ({ page }) => {
  await page.goto('/dashboard')
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByRole('heading', { name: 'Sign in to PrepPilot' })).toBeVisible()
})

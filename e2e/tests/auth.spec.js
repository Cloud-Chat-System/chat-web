import { expect, test } from '@playwright/test'
import { randomUUID } from 'node:crypto'

function uniqueUser(prefix) {
  const id = `${Date.now()}-${randomUUID()}`
  return {
    name: `${prefix} User`,
    email: `${prefix.toLowerCase()}-${id}@example.com`,
    password: 'password123',
  }
}

test('user can register, log in, and log out through the UI', async ({ page }) => {
  const user = uniqueUser('Auth')

  await page.goto('/chat')
  await expect(page).toHaveURL(/\/login$/)

  await page.goto('/register')
  await page.getByTestId('register-name').fill(user.name)
  await page.getByTestId('register-email').fill(user.email)
  await page.getByTestId('register-password').fill(user.password)
  await page.getByTestId('register-confirm-password').fill(user.password)
  await expect(page.getByTestId('register-submit')).toBeEnabled()
  await page.getByTestId('register-submit').click()

  await expect(page).toHaveURL(/\/login$/)

  await page.getByTestId('login-email').fill(user.email)
  await page.getByTestId('login-password').fill(user.password)
  await expect(page.getByTestId('login-submit')).toBeEnabled()
  await page.getByTestId('login-submit').click()

  await expect(page).toHaveURL(/\/chat$/)
  await expect(page.getByText(user.email)).toBeVisible()

  await page.getByTestId('logout-button').click()
  await expect(page).toHaveURL(/\/login$/)
})

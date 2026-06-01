import { expect, test } from '@playwright/test'
import { randomUUID } from 'node:crypto'

const backendUrl = process.env.E2E_BACKEND_URL || 'http://127.0.0.1:8000'

function uniqueUser(prefix) {
  const id = `${Date.now()}-${randomUUID()}`
  return {
    username: `${prefix.toLowerCase()}_${id}`.replaceAll('-', '_'),
    name: `${prefix} User ${id}`,
    email: `${prefix.toLowerCase()}-${id}@example.com`,
    password: 'password123',
  }
}

async function registerUser(request, user) {
  const response = await request.post(`${backendUrl}/auth/register`, {
    data: {
      username: user.username,
      display_name: user.name,
      email: user.email,
      password: user.password,
    },
  })
  expect(response.status()).toBe(201)
}

async function login(page, user) {
  await page.goto('/login')
  await page.getByTestId('login-email').fill(user.email)
  await page.getByTestId('login-password').fill(user.password)
  await page.getByTestId('login-submit').click()
  await expect(page).toHaveURL(/\/chat$/)
}

async function createDirectChat(page, user) {
  await page.getByTestId('new-chat-button').click()
  await expect(page.getByTestId('new-chat-modal')).toBeVisible()
  await page.getByTestId('user-search-input').fill(user.email)

  const result = page.getByTestId('user-search-result').filter({ hasText: user.email })
  await expect(result).toBeVisible()
  await result.click()

  await page.getByTestId('new-chat-modal').locator('button').last().click()
  await expect(page.getByTestId('new-chat-modal')).toBeHidden()
}

test('user can create a direct chat and send a message', async ({ page, request }) => {
  const alice = uniqueUser('Alice')
  const bob = uniqueUser('Bob')
  const message = `hello from e2e ${Date.now()}`

  await registerUser(request, alice)
  await registerUser(request, bob)

  await login(page, alice)
  await createDirectChat(page, bob)

  const bobRoom = page.getByTestId('chat-room-item').filter({ hasText: bob.name })
  await expect(bobRoom).toBeVisible()
  await bobRoom.click()

  await expect(page.getByTestId('active-chat-name')).toContainText(bob.name)
  await page.getByTestId('message-input').fill(message)
  await page.getByTestId('send-button').click()

  await expect(page.getByTestId('message-bubble').filter({ hasText: message })).toBeVisible()
})

test('recipient can log in and read a direct message', async ({ page, request }) => {
  const alice = uniqueUser('Alice')
  const bob = uniqueUser('Bob')
  const message = `persisted direct message ${Date.now()}`

  await registerUser(request, alice)
  await registerUser(request, bob)

  await login(page, alice)
  await createDirectChat(page, bob)
  await page.getByTestId('chat-room-item').filter({ hasText: bob.name }).click()
  await page.getByTestId('message-input').fill(message)
  await page.getByTestId('send-button').click()
  await expect(page.getByTestId('message-bubble').filter({ hasText: message })).toBeVisible()

  await page.getByTestId('logout-button').click()
  await expect(page).toHaveURL(/\/login$/)

  await login(page, bob)
  const aliceRoom = page.getByTestId('chat-room-item').filter({ hasText: alice.name })
  await expect(aliceRoom).toBeVisible()
  await aliceRoom.click()

  await expect(page.getByTestId('active-chat-name')).toContainText(alice.name)
  await expect(page.getByTestId('message-bubble').filter({ hasText: message })).toBeVisible()
})

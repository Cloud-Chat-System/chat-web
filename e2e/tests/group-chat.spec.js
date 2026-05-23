import { expect, test } from '@playwright/test'

const backendUrl = process.env.E2E_BACKEND_URL || 'http://127.0.0.1:8000'

function uniqueUser(prefix) {
  const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
  return {
    username: `${prefix.toLowerCase()}_${id}`.replace(/-/g, '_'),
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

async function selectUserInModal(page, user) {
  await page.getByTestId('user-search-input').fill(user.email)
  const result = page.getByTestId('user-search-result').filter({ hasText: user.email })
  await expect(result).toBeVisible()
  await result.click()
}

test('user can create a group chat and send a group message', async ({ page, request }) => {
  const alice = uniqueUser('Alice')
  const bob = uniqueUser('Bob')
  const charlie = uniqueUser('Charlie')
  const groupName = `E2E Group ${Date.now()}`
  const message = `hello group ${Date.now()}`

  await registerUser(request, alice)
  await registerUser(request, bob)
  await registerUser(request, charlie)

  await login(page, alice)

  await page.getByTestId('new-chat-button').click()
  await expect(page.getByTestId('new-chat-modal')).toBeVisible()
  await page.getByTestId('group-chat-tab').click()
  await page.getByTestId('group-name-input').fill(groupName)
  await selectUserInModal(page, bob)
  await selectUserInModal(page, charlie)

  await page.getByTestId('new-chat-modal').locator('button').last().click()
  await expect(page.getByTestId('new-chat-modal')).toBeHidden()

  const groupRoom = page.getByTestId('chat-room-item').filter({ hasText: groupName })
  await expect(groupRoom).toBeVisible()
  await groupRoom.click()

  await expect(page.getByTestId('active-chat-name')).toContainText(groupName)
  await page.getByTestId('message-input').fill(message)
  await page.getByTestId('send-button').click()

  await expect(page.getByTestId('message-bubble').filter({ hasText: message })).toBeVisible()
})

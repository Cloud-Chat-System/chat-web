import { beforeEach, describe, expect, it, vi } from 'vitest'

import api from '../utils/api'
import { useAuthStore } from './useAuthStore'

vi.mock('../utils/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

const initialState = useAuthStore.getState()

describe('useAuthStore', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    useAuthStore.setState(initialState, true)
  })

  it('initializes as logged out when no token exists', async () => {
    await useAuthStore.getState().initAuth()

    expect(api.get).not.toHaveBeenCalled()
    expect(useAuthStore.getState()).toMatchObject({
      user: null,
      isLoading: false,
      isInitialized: true,
    })
  })

  it('loads the current user when a token exists', async () => {
    localStorage.setItem('token', 'token-123')
    api.get.mockResolvedValueOnce({
      data: { id: 1, email: 'alice@example.com', username: 'alice' },
    })

    await useAuthStore.getState().initAuth()

    expect(api.get).toHaveBeenCalledWith('/auth/me')
    expect(useAuthStore.getState().user).toEqual({
      id: 1,
      email: 'alice@example.com',
      username: 'alice',
    })
  })

  it('stores token and user after successful login', async () => {
    api.post.mockResolvedValueOnce({
      data: {
        token: 'token-123',
        user: { id: 1, email: 'alice@example.com', username: 'alice' },
      },
    })

    const user = await useAuthStore.getState().login('alice@example.com', 'password123')

    expect(api.post).toHaveBeenCalledWith('/auth/login', {
      email: 'alice@example.com',
      password: 'password123',
    })
    expect(localStorage.getItem('token')).toBe('token-123')
    expect(user).toEqual({ id: 1, email: 'alice@example.com', username: 'alice' })
    expect(useAuthStore.getState().error).toBeNull()
  })

  it('sets an error and rethrows when login fails', async () => {
    api.post.mockRejectedValueOnce({
      response: { data: { detail: 'Invalid credentials' } },
    })

    await expect(
      useAuthStore.getState().login('alice@example.com', 'wrong-password')
    ).rejects.toThrow('Invalid credentials')

    expect(useAuthStore.getState()).toMatchObject({
      user: null,
      isLoading: false,
      error: 'Invalid credentials',
    })
  })

  it('clears local auth state on logout even if the API request fails', async () => {
    localStorage.setItem('token', 'token-123')
    useAuthStore.setState({
      user: { id: 1, email: 'alice@example.com' },
      error: 'previous error',
    })
    api.post.mockRejectedValueOnce(new Error('network down'))

    await useAuthStore.getState().logout()

    expect(api.post).toHaveBeenCalledWith('/auth/logout')
    expect(localStorage.getItem('token')).toBeNull()
    expect(useAuthStore.getState()).toMatchObject({
      user: null,
      error: null,
    })
  })
})

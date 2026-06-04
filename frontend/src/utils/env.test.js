import { afterEach, describe, expect, it, vi } from 'vitest'

describe('env utilities', () => {
  afterEach(() => {
    vi.resetModules()
    vi.unstubAllEnvs()
  })

  it('normalizes configured API and WebSocket URLs', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000/')
    vi.stubEnv('VITE_WS_URL', 'ws://localhost:8000/ws/')

    const env = await import('./env')

    expect(env.API_BASE_URL).toBe('http://localhost:8000')
    expect(env.WS_URL).toBe('ws://localhost:8000/ws')
  })

  it('derives a WebSocket URL from the API URL when one is not provided', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com/')
    vi.stubEnv('VITE_WS_URL', '')

    const env = await import('./env')

    expect(env.WS_URL).toBe('wss://api.example.com/ws')
  })

  it('throws when the API URL is missing', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '')

    await expect(import('./env')).rejects.toThrow('Missing required environment variable')
  })
})

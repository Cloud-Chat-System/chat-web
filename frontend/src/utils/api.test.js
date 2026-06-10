import { afterEach, describe, expect, it, vi } from 'vitest'

describe('api client', () => {
  afterEach(() => {
    localStorage.clear()
    vi.resetModules()
    vi.unstubAllEnvs()
  })

  it('creates an axios client with the configured base URL', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000/')

    const { default: api } = await import('./api')

    expect(api.defaults.baseURL).toBe('http://localhost:8000')
    expect(api.defaults.headers['Content-Type']).toBe('application/json')
  })

  it('adds a bearer token to outgoing requests', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
    localStorage.setItem('token', 'token-123')

    const { default: api } = await import('./api')
    const handler = api.interceptors.request.handlers[0].fulfilled
    const config = handler({ headers: {} })

    expect(config.headers.Authorization).toBe('Bearer token-123')
  })

  it('removes the token on unauthorized responses', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
    localStorage.setItem('token', 'token-123')

    const { default: api } = await import('./api')
    const handler = api.interceptors.response.handlers[0].rejected

    await expect(handler({ response: { status: 401 } })).rejects.toMatchObject({
      response: { status: 401 },
    })
    expect(localStorage.getItem('token')).toBeNull()
  })
})

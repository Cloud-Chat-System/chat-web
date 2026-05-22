function requireEnv(name) {
  const value = import.meta.env[name]
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`)
  }
  return value
}

export const API_BASE_URL = requireEnv('VITE_API_BASE_URL').replace(/\/$/, '')
export const WS_URL = (import.meta.env.VITE_WS_URL || `${API_BASE_URL.replace(/^http/, 'ws')}/ws`).replace(/\/$/, '')

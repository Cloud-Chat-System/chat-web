import { act, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import GoogleAuthButton from './GoogleAuthButton'

describe('GoogleAuthButton', () => {
  afterEach(() => {
    document.head.innerHTML = ''
    delete window.google
    vi.unstubAllEnvs()
  })

  it('renders a disabled fallback when no Google client id is configured', () => {
    vi.stubEnv('VITE_GOOGLE_CLIENT_ID', '')

    render(<GoogleAuthButton onCredential={vi.fn()} />)

    expect(screen.getByRole('button')).toBeDisabled()
  })

  it('initializes Google Identity Services and handles credentials', async () => {
    vi.stubEnv('VITE_GOOGLE_CLIENT_ID', 'client-id')
    const onCredential = vi.fn()
    const renderButton = vi.fn()
    window.google = {
      accounts: {
        id: {
          initialize: vi.fn(({ callback }) => callback({ credential: 'credential-123' })),
          renderButton,
        },
      },
    }

    render(<GoogleAuthButton onCredential={onCredential} mode="signup" />)

    await waitFor(() => expect(window.google.accounts.id.initialize).toHaveBeenCalled())
    expect(renderButton).toHaveBeenCalledWith(expect.any(HTMLDivElement), expect.objectContaining({
      text: 'signup_with',
    }))
    expect(onCredential).toHaveBeenCalledWith('credential-123')
  })

  it('shows an error when the Google script fails to load', async () => {
    vi.stubEnv('VITE_GOOGLE_CLIENT_ID', 'client-id')

    render(<GoogleAuthButton onCredential={vi.fn()} />)
    const script = document.getElementById('google-identity-services')

    await act(async () => {
      script.onerror()
    })

    expect(await screen.findByText(/Google/)).toBeInTheDocument()
  })
})

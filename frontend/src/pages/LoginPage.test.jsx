import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useAuthStore } from '../store/useAuthStore'
import LoginPage from './LoginPage'

describe('LoginPage', () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: null,
      isLoading: false,
      error: null,
      isInitialized: true,
      login: vi.fn().mockResolvedValue({ id: 1 }),
      clearError: vi.fn(),
    })
  })

  it('keeps submit disabled until the form is valid', () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    )

    expect(screen.getByTestId('login-submit')).toBeDisabled()

    fireEvent.change(screen.getByTestId('login-email'), { target: { value: 'alice@example.com' } })
    fireEvent.change(screen.getByTestId('login-password'), { target: { value: 'secret1' } })

    expect(screen.getByTestId('login-submit')).toBeEnabled()
  })

  it('submits login credentials and clears previous errors', async () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    )

    fireEvent.change(screen.getByTestId('login-email'), { target: { value: 'alice@example.com' } })
    fireEvent.change(screen.getByTestId('login-password'), { target: { value: 'secret1' } })
    fireEvent.click(screen.getByTestId('login-submit'))

    await waitFor(() =>
      expect(useAuthStore.getState().login).toHaveBeenCalledWith('alice@example.com', 'secret1')
    )
    expect(useAuthStore.getState().clearError).toHaveBeenCalled()
  })

  it('toggles password visibility', () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    )

    const password = screen.getByTestId('login-password')
    expect(password).toHaveAttribute('type', 'password')
    fireEvent.click(screen.getByRole('button', { name: '顯示密碼' }))
    expect(password).toHaveAttribute('type', 'text')
  })
})

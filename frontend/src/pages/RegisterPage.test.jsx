import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useAuthStore } from '../store/useAuthStore'
import RegisterPage from './RegisterPage'

describe('RegisterPage', () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: null,
      isLoading: false,
      error: null,
      isInitialized: true,
      register: vi.fn().mockResolvedValue({ name: 'Alice', email: 'alice@example.com' }),
      clearError: vi.fn(),
    })
  })

  it('keeps submit disabled until all fields are valid', () => {
    render(
      <MemoryRouter>
        <RegisterPage />
      </MemoryRouter>
    )

    expect(screen.getByTestId('register-submit')).toBeDisabled()

    fireEvent.change(screen.getByTestId('register-name'), { target: { value: 'Alice' } })
    fireEvent.change(screen.getByTestId('register-email'), { target: { value: 'alice@example.com' } })
    fireEvent.change(screen.getByTestId('register-password'), { target: { value: 'secret1' } })
    fireEvent.change(screen.getByTestId('register-confirm-password'), { target: { value: 'secret1' } })

    expect(screen.getByTestId('register-submit')).toBeEnabled()
  })

  it('submits registration details', async () => {
    render(
      <MemoryRouter>
        <RegisterPage />
      </MemoryRouter>
    )

    fireEvent.change(screen.getByTestId('register-name'), { target: { value: 'Alice' } })
    fireEvent.change(screen.getByTestId('register-email'), { target: { value: 'alice@example.com' } })
    fireEvent.change(screen.getByTestId('register-password'), { target: { value: 'secret1' } })
    fireEvent.change(screen.getByTestId('register-confirm-password'), { target: { value: 'secret1' } })
    fireEvent.click(screen.getByTestId('register-submit'))

    await waitFor(() =>
      expect(useAuthStore.getState().register).toHaveBeenCalledWith(
        'Alice',
        'alice@example.com',
        'secret1'
      )
    )
    expect(useAuthStore.getState().clearError).toHaveBeenCalled()
  })

  it('toggles both password fields between hidden and visible', () => {
    render(
      <MemoryRouter>
        <RegisterPage />
      </MemoryRouter>
    )

    expect(screen.getByTestId('register-password')).toHaveAttribute('type', 'password')
    expect(screen.getByTestId('register-confirm-password')).toHaveAttribute('type', 'password')

    fireEvent.click(screen.getAllByRole('button').find((button) => button.getAttribute('type') === 'button'))

    expect(screen.getByTestId('register-password')).toHaveAttribute('type', 'text')
    expect(screen.getByTestId('register-confirm-password')).toHaveAttribute('type', 'text')
  })
})

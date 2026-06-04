import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useChatStore } from '../../store/useChatStore'
import api from '../../utils/api'
import NewChatModal from './NewChatModal'

vi.mock('../../utils/api', () => ({
  default: {
    get: vi.fn(),
  },
}))

describe('NewChatModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useChatStore.setState({
      createChat: vi.fn(),
      createGroupChat: vi.fn(),
    })
  })

  it('searches users and creates a direct chat', async () => {
    const onClose = vi.fn()
    const createChat = vi.fn().mockResolvedValue({ id: 10 })
    useChatStore.setState({ createChat })
    api.get.mockResolvedValueOnce({
      data: [{ id: 2, username: 'alice', display_name: 'Alice', email: 'alice@example.com' }],
    })

    render(<NewChatModal onClose={onClose} />)
    fireEvent.change(screen.getByTestId('user-search-input'), { target: { value: 'alice' } })

    const result = await screen.findByTestId('user-search-result')
    fireEvent.click(result)
    fireEvent.click(screen.getAllByRole('button').at(-1))

    await waitFor(() => expect(createChat).toHaveBeenCalledWith(2))
    expect(onClose).toHaveBeenCalled()
  })

  it('creates a group chat with selected users and a group name', async () => {
    const onClose = vi.fn()
    const createGroupChat = vi.fn().mockResolvedValue({ id: 20 })
    useChatStore.setState({ createGroupChat })
    api.get.mockResolvedValueOnce({
      data: [
        { id: 2, username: 'alice', display_name: 'Alice', email: 'alice@example.com' },
        { id: 3, username: 'bob', display_name: 'Bob', email: 'bob@example.com' },
      ],
    })

    render(<NewChatModal onClose={onClose} />)
    fireEvent.click(screen.getByTestId('group-chat-tab'))
    fireEvent.change(screen.getByTestId('group-name-input'), { target: { value: 'Team Chat' } })
    fireEvent.change(screen.getByTestId('user-search-input'), { target: { value: 'team' } })

    const results = await screen.findAllByTestId('user-search-result')
    fireEvent.click(results[0])
    fireEvent.click(results[1])
    fireEvent.click(screen.getAllByRole('button').at(-1))

    await waitFor(() => expect(createGroupChat).toHaveBeenCalledWith('Team Chat', [2, 3]))
    expect(onClose).toHaveBeenCalled()
  })

  it('does not create a chat without selected users', async () => {
    render(<NewChatModal onClose={vi.fn()} />)

    const confirmButton = screen.getAllByRole('button').at(-1)
    expect(confirmButton).toBeDisabled()
    fireEvent.click(confirmButton)

    expect(useChatStore.getState().createChat).not.toHaveBeenCalled()
  })
})

import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useAuthStore } from '../../store/useAuthStore'
import { useChatStore } from '../../store/useChatStore'
import Sidebar from './Sidebar'

describe('Sidebar', () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: { id: 1, username: 'me', display_name: 'Me', email: 'me@example.com' },
      isInitialized: true,
      isLoading: false,
      error: null,
      logout: vi.fn(),
    })
    useChatStore.setState({
      searchQuery: '',
      filterTab: 'all',
      activeChatId: null,
      setSearchQuery: vi.fn(),
      setFilterTab: vi.fn(),
      setActiveChatId: vi.fn(),
      markAsRead: vi.fn(),
      getFilteredChatRooms: vi.fn(() => [
        {
          id: 1,
          name: 'Alice',
          isGroup: false,
          members: [1, 2],
          lastMessage: 'hello',
          lastMessageTime: '2026-06-03T08:00:00.000Z',
          unreadCount: 2,
          online: true,
        },
      ]),
    })
  })

  it('renders rooms and selects a room', () => {
    const onSelectChat = vi.fn()
    render(
      <MemoryRouter>
        <Sidebar onSelectChat={onSelectChat} />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByTestId('chat-room-item'))

    expect(useChatStore.getState().setActiveChatId).toHaveBeenCalledWith(1)
    expect(useChatStore.getState().markAsRead).toHaveBeenCalledWith(1)
    expect(onSelectChat).toHaveBeenCalled()
  })

  it('updates search query and filter tab', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    )

    fireEvent.change(screen.getByTestId('chat-search-input'), { target: { value: 'ali' } })
    fireEvent.click(screen.getByRole('button', { name: '群組' }))

    expect(useChatStore.getState().setSearchQuery).toHaveBeenCalledWith('ali')
    expect(useChatStore.getState().setFilterTab).toHaveBeenCalledWith('group')
  })

  it('opens and closes the new chat modal', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByTestId('new-chat-button'))
    expect(screen.getByTestId('new-chat-modal')).toBeInTheDocument()

    fireEvent.click(screen.getAllByRole('button').at(-2))
    expect(screen.queryByTestId('new-chat-modal')).not.toBeInTheDocument()
  })

  it('logs out through the auth store', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByTestId('logout-button'))

    expect(useAuthStore.getState().logout).toHaveBeenCalled()
  })
})

import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useAuthStore } from '../../store/useAuthStore'
import { useChatStore } from '../../store/useChatStore'
import ChatWindow from './ChatWindow'

const baseChatState = {
  chatRooms: [],
  messages: {},
  activeChatId: null,
  searchQuery: '',
  filterTab: 'all',
  onlineUsers: new Set(),
  isLoading: false,
}

describe('ChatWindow', () => {
  beforeEach(() => {
    Element.prototype.scrollIntoView = vi.fn()
    useAuthStore.setState({
      user: { id: 1, username: 'me', display_name: 'Me', email: 'me@example.com' },
      isInitialized: true,
      isLoading: false,
      error: null,
    })
    useChatStore.setState(baseChatState)
  })

  it('renders an empty state when no room is active', () => {
    render(<ChatWindow />)

    expect(screen.getByText('TSMC Messenger')).toBeInTheDocument()
  })

  it('renders active room messages and sends trimmed input', () => {
    const sendMessage = vi.fn()
    useChatStore.setState({
      activeChatId: 1,
      sendMessage,
      chatRooms: [
        {
          id: 1,
          name: 'Alice',
          isGroup: false,
          members: [1, 2],
          unreadCount: 0,
        },
      ],
      messages: {
        1: [
          {
            id: 10,
            chatId: 1,
            senderId: 2,
            senderName: 'Alice',
            content: 'Incoming',
            timestamp: '2026-06-03T08:00:00.000Z',
          },
          {
            id: 11,
            chatId: 1,
            senderId: 1,
            senderName: 'Me',
            content: 'Outgoing',
            timestamp: '2026-06-03T08:01:00.000Z',
          },
        ],
      },
      onlineUsers: new Set([2]),
    })

    render(<ChatWindow onBack={vi.fn()} />)

    expect(screen.getByTestId('active-chat-name')).toHaveTextContent('Alice')
    expect(screen.getByText('Incoming')).toBeInTheDocument()
    expect(screen.getByText('Outgoing')).toBeInTheDocument()

    fireEvent.change(screen.getByTestId('message-input'), { target: { value: '  hello  ' } })
    fireEvent.click(screen.getByTestId('send-button'))

    expect(sendMessage).toHaveBeenCalledWith(1, 'hello', 1)
    expect(screen.getByTestId('message-input')).toHaveValue('')
  })

  it('sends on Enter and keeps multiline input on Shift+Enter', () => {
    const sendMessage = vi.fn()
    useChatStore.setState({
      activeChatId: 1,
      sendMessage,
      chatRooms: [{ id: 1, name: 'Team', isGroup: true, members: [1, 2], unreadCount: 0 }],
      messages: { 1: [] },
    })

    render(<ChatWindow />)
    const input = screen.getByTestId('message-input')

    fireEvent.change(input, { target: { value: 'first' } })
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: true })
    expect(sendMessage).not.toHaveBeenCalled()

    fireEvent.keyDown(input, { key: 'Enter', shiftKey: false })
    expect(sendMessage).toHaveBeenCalledWith(1, 'first', 1)
  })
})

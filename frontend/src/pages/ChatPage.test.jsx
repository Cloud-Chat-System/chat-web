import { act, fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useChatStore } from '../store/useChatStore'
import ChatPage from './ChatPage'

vi.mock('../components/chat/Sidebar', () => ({
  default: ({ onSelectChat }) => <button data-testid="mock-sidebar" onClick={onSelectChat}>sidebar</button>,
}))

vi.mock('../components/chat/ChatWindow', () => ({
  default: ({ onBack }) => <button data-testid="mock-chat-window" onClick={onBack}>chat</button>,
}))

describe('ChatPage', () => {
  beforeEach(() => {
    useChatStore.setState({
      setActiveChatId: vi.fn(),
      fetchChatRooms: vi.fn(),
      fetchOnlineUsers: vi.fn(),
      initWebSocket: vi.fn(),
      disconnectWebSocket: vi.fn(),
    })
  })

  it('initializes chat data and disconnects on unmount', () => {
    const { unmount } = render(<ChatPage />)

    expect(useChatStore.getState().fetchChatRooms).toHaveBeenCalled()
    expect(useChatStore.getState().fetchOnlineUsers).toHaveBeenCalled()
    expect(useChatStore.getState().initWebSocket).toHaveBeenCalled()

    unmount()
    expect(useChatStore.getState().disconnectWebSocket).toHaveBeenCalled()
  })

  it('shows only the selected mobile panel and returns to the sidebar on back', () => {
    const originalWidth = globalThis.innerWidth
    globalThis.innerWidth = 500

    render(<ChatPage />)
    expect(screen.getByTestId('mock-sidebar')).toBeInTheDocument()
    expect(screen.queryByTestId('mock-chat-window')).not.toBeInTheDocument()

    fireEvent.click(screen.getByTestId('mock-sidebar'))
    expect(screen.queryByTestId('mock-sidebar')).not.toBeInTheDocument()
    expect(screen.getByTestId('mock-chat-window')).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('mock-chat-window'))
    expect(useChatStore.getState().setActiveChatId).toHaveBeenCalledWith(null)
    expect(screen.getByTestId('mock-sidebar')).toBeInTheDocument()

    globalThis.innerWidth = originalWidth
  })

  it('keeps both panels visible on wide screens and responds to resize', () => {
    globalThis.innerWidth = 500
    render(<ChatPage />)

    expect(screen.queryByTestId('mock-chat-window')).not.toBeInTheDocument()

    act(() => {
      globalThis.innerWidth = 900
      globalThis.dispatchEvent(new Event('resize'))
    })

    expect(screen.getByTestId('mock-sidebar')).toBeInTheDocument()
    expect(screen.getByTestId('mock-chat-window')).toBeInTheDocument()
  })
})

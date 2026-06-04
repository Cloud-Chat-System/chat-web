import { beforeEach, describe, expect, it, vi } from 'vitest'

import api from '../utils/api'
import { useAuthStore } from './useAuthStore'
import { useChatStore } from './useChatStore'

vi.mock('../utils/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}))

vi.mock('../utils/env', () => ({
  WS_URL: 'ws://localhost/ws',
}))

const baseChatState = {
  chatRooms: [],
  messages: {},
  activeChatId: null,
  searchQuery: '',
  filterTab: 'all',
  onlineUsers: new Set(),
  isLoading: false,
}

const apiRoom = (overrides = {}) => ({
  id: 1,
  name: 'Alice',
  room_type: 'direct',
  members: [{ id: 1 }, { id: 2 }],
  last_message: 'hello',
  last_message_at: '2026-06-03T08:00:00.000Z',
  created_at: '2026-06-03T07:00:00.000Z',
  unread_count: 0,
  ...overrides,
})

const apiMessage = (overrides = {}) => ({
  id: 10,
  room_id: 1,
  sender_id: 2,
  sender_name: 'Alice',
  content: 'hello',
  created_at: '2026-06-03T08:00:00.000Z',
  ...overrides,
})

describe('useChatStore', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    useAuthStore.setState({
      user: { id: 1, email: 'me@example.com', username: 'me' },
      isLoading: false,
      error: null,
      isInitialized: true,
    })
    useChatStore.getState().disconnectWebSocket()
    useChatStore.setState(baseChatState)
  })

  it('fetches, maps, and sorts chat rooms by recent activity', async () => {
    api.get.mockResolvedValueOnce({
      data: [
        apiRoom({ id: 1, name: 'Older', last_message_at: '2026-06-03T07:00:00.000Z' }),
        apiRoom({ id: 2, name: 'Newer', last_message_at: '2026-06-03T09:00:00.000Z' }),
      ],
    })

    await useChatStore.getState().fetchChatRooms()

    expect(api.get).toHaveBeenCalledWith('/chatrooms')
    expect(useChatStore.getState().chatRooms.map((room) => room.name)).toEqual(['Newer', 'Older'])
    expect(useChatStore.getState().chatRooms[0]).toMatchObject({
      id: 2,
      isGroup: false,
      members: [1, 2],
      lastMessage: 'hello',
    })
  })

  it('fetches messages and merges them without duplicating existing ids', async () => {
    useChatStore.setState({
      messages: {
        1: [
          {
            id: 10,
            chatId: 1,
            senderId: 2,
            senderName: 'Alice',
            content: 'old content',
            timestamp: '2026-06-03T08:00:00.000Z',
          },
        ],
      },
    })
    api.get.mockResolvedValueOnce({
      data: {
        messages: [
          apiMessage({ id: 10, content: 'updated', created_at: '2026-06-03T08:00:00.000Z' }),
          apiMessage({ id: 11, content: 'new', created_at: '2026-06-03T09:00:00.000Z' }),
        ],
      },
    })

    await useChatStore.getState().fetchMessages(1)

    expect(api.get).toHaveBeenCalledWith('/chatrooms/1/messages?limit=200')
    expect(useChatStore.getState().messages[1].map((message) => message.content)).toEqual(['updated', 'new'])
  })

  it('increments unread count for incoming messages outside the active room', () => {
    useChatStore.setState({
      activeChatId: 99,
      chatRooms: [
        {
          id: 1,
          name: 'Alice',
          isGroup: false,
          members: [1, 2],
          createdAt: '2026-06-03T07:00:00.000Z',
          unreadCount: 0,
        },
      ],
    })

    useChatStore.getState().upsertMessage(apiMessage({ content: 'ping' }))

    expect(useChatStore.getState().chatRooms[0]).toMatchObject({
      lastMessage: 'ping',
      unreadCount: 1,
    })
    expect(useChatStore.getState().messages[1][0]).toMatchObject({
      chatId: 1,
      senderId: 2,
      content: 'ping',
    })
  })

  it('does not increment unread count for self-sent messages', async () => {
    useChatStore.setState({
      chatRooms: [
        {
          id: 1,
          name: 'Alice',
          isGroup: false,
          members: [1, 2],
          createdAt: '2026-06-03T07:00:00.000Z',
          unreadCount: 0,
        },
      ],
    })
    api.post.mockResolvedValueOnce({
      data: apiMessage({ sender_id: 1, content: 'sent by me' }),
    })

    await useChatStore.getState().sendMessage(1, 'sent by me')

    expect(api.post).toHaveBeenCalledWith('/chatrooms/1/messages', { content: 'sent by me' })
    expect(useChatStore.getState().chatRooms[0].unreadCount).toBe(0)
  })

  it('filters rooms by tab, search query, and online direct members', () => {
    useChatStore.setState({
      chatRooms: [
        { id: 1, name: 'Alice', isGroup: false, members: [1, 2], unreadCount: 1 },
        { id: 2, name: 'Backend Team', isGroup: true, members: [1, 3], unreadCount: 0 },
        { id: 3, name: 'Carol', isGroup: false, members: [1, 4], unreadCount: 0 },
      ],
      onlineUsers: new Set([2]),
      searchQuery: 'ali',
      filterTab: 'all',
    })

    expect(useChatStore.getState().getFilteredChatRooms()).toEqual([
      expect.objectContaining({ id: 1, online: true }),
    ])

    useChatStore.setState({ searchQuery: '', filterTab: 'group' })
    expect(useChatStore.getState().getFilteredChatRooms()).toEqual([
      expect.objectContaining({ id: 2, online: false }),
    ])

    useChatStore.setState({ filterTab: 'unread' })
    expect(useChatStore.getState().getFilteredChatRooms()).toEqual([
      expect.objectContaining({ id: 1 }),
    ])
  })

  it('creates direct and group chats and activates the created room', async () => {
    api.post
      .mockResolvedValueOnce({ data: apiRoom({ id: 7, name: 'Alice' }) })
      .mockResolvedValueOnce({ data: apiRoom({ id: 8, name: 'Team', room_type: 'group' }) })
    api.get.mockResolvedValue({ data: { messages: [] } })

    await expect(useChatStore.getState().createChat(2)).resolves.toEqual(apiRoom({ id: 7, name: 'Alice' }))
    expect(api.post).toHaveBeenCalledWith('/chatrooms', {
      room_type: 'direct',
      member_ids: [2],
      name: '',
    })
    expect(useChatStore.getState().activeChatId).toBe(7)

    await expect(useChatStore.getState().createGroupChat('Team', [2, 3])).resolves.toEqual(
      apiRoom({ id: 8, name: 'Team', room_type: 'group' })
    )
    expect(api.post).toHaveBeenCalledWith('/chatrooms', {
      room_type: 'group',
      member_ids: [2, 3],
      name: 'Team',
    })
    expect(useChatStore.getState().activeChatId).toBe(8)
  })

  it('marks a room as read locally after the API call succeeds', async () => {
    useChatStore.setState({
      chatRooms: [
        { id: 1, name: 'Alice', isGroup: false, members: [1, 2], unreadCount: 3 },
        { id: 2, name: 'Team', isGroup: true, members: [1, 3], unreadCount: 2 },
      ],
    })
    api.put.mockResolvedValueOnce({})

    await useChatStore.getState().markAsRead(1)

    expect(api.put).toHaveBeenCalledWith('/chatrooms/1/read')
    expect(useChatStore.getState().chatRooms).toEqual([
      expect.objectContaining({ id: 1, unreadCount: 0 }),
      expect.objectContaining({ id: 2, unreadCount: 2 }),
    ])
  })
})

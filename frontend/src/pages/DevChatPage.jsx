import { useEffect, useState } from 'react'
import Sidebar from '../components/chat/Sidebar'
import ChatWindow from '../components/chat/ChatWindow'
import { useAuthStore } from '../store/useAuthStore'
import { useChatStore } from '../store/useChatStore'
import chatStyles from '../styles/chat.module.css'

const now = new Date()
const minutesAgo = (minutes) => new Date(now.getTime() - minutes * 60 * 1000).toISOString()

const mockUser = {
  id: 1,
  username: 'demo.user',
  display_name: 'Demo User',
  email: 'demo.user@tsmc.com',
}

const mockRooms = [
  {
    id: 101,
    name: '製程整合小組',
    isGroup: true,
    members: [1, 2, 3, 4],
    lastMessage: '下午三點同步測試結果',
    lastMessageTime: minutesAgo(4),
    createdAt: minutesAgo(160),
    unreadCount: 2,
    membersList: [],
  },
  {
    id: 102,
    name: 'Haozhe Xie',
    isGroup: false,
    members: [1, 2],
    lastMessage: '我先把資料整理到 shared folder',
    lastMessageTime: minutesAgo(38),
    createdAt: minutesAgo(220),
    unreadCount: 0,
    membersList: [],
  },
  {
    id: 103,
    name: '設備維護頻道',
    isGroup: true,
    members: [1, 3, 5],
    lastMessage: '機台保養時段已確認',
    lastMessageTime: minutesAgo(92),
    createdAt: minutesAgo(420),
    unreadCount: 0,
    membersList: [],
  },
]

const mockMessages = {
  101: [
    {
      id: 1001,
      chatId: 101,
      senderId: 2,
      senderName: 'Haozhe Xie',
      content: '早上的 wafer map 我已經上傳了。',
      timestamp: minutesAgo(16),
    },
    {
      id: 1002,
      chatId: 101,
      senderId: 1,
      senderName: 'Demo User',
      content: '收到，我先看 CP yield 變化。',
      timestamp: minutesAgo(12),
    },
    {
      id: 1003,
      chatId: 101,
      senderId: 3,
      senderName: 'Ivy Chen',
      content: '下午三點同步測試結果',
      timestamp: minutesAgo(4),
    },
  ],
  102: [
    {
      id: 2001,
      chatId: 102,
      senderId: 2,
      senderName: 'Haozhe Xie',
      content: '我先把資料整理到 shared folder',
      timestamp: minutesAgo(38),
    },
  ],
  103: [
    {
      id: 3001,
      chatId: 103,
      senderId: 5,
      senderName: '設備工程師',
      content: '機台保養時段已確認',
      timestamp: minutesAgo(92),
    },
  ],
}

export default function DevChatPage() {
  const [showSidebar, setShowSidebar] = useState(true)

  useEffect(() => {
    useAuthStore.setState({
      user: mockUser,
      isLoading: false,
      error: null,
      isInitialized: true,
      logout: () => {
        useAuthStore.setState({ user: null })
        window.location.assign('/login')
      },
    })

    useChatStore.setState((state) => ({
      ...state,
      chatRooms: mockRooms,
      messages: mockMessages,
      activeChatId: 101,
      searchQuery: '',
      filterTab: 'all',
      onlineUsers: new Set([2, 3]),
      isLoading: false,
      fetchChatRooms: async () => {},
      fetchMessages: async () => {},
      fetchOnlineUsers: async () => {},
      initWebSocket: () => {},
      disconnectWebSocket: () => {},
      markAsRead: async (chatId) => {
        useChatStore.setState((current) => ({
          chatRooms: current.chatRooms.map((room) =>
            room.id === chatId ? { ...room, unreadCount: 0 } : room
          ),
        }))
      },
      sendMessage: async (chatId, content) => {
        const message = {
          id: Date.now(),
          chatId,
          senderId: mockUser.id,
          senderName: mockUser.display_name,
          content,
          timestamp: new Date().toISOString(),
        }

        useChatStore.setState((current) => ({
          messages: {
            ...current.messages,
            [chatId]: [...(current.messages[chatId] || []), message],
          },
          chatRooms: current.chatRooms.map((room) =>
            room.id === chatId
              ? { ...room, lastMessage: content, lastMessageTime: message.timestamp }
              : room
          ),
        }))
      },
    }))
  }, [])

  const handleSelectChat = () => {
    if (window.innerWidth < 768) {
      setShowSidebar(false)
    }
  }

  const handleBack = () => {
    useChatStore.setState({ activeChatId: null })
    setShowSidebar(true)
  }

  return (
    <div className={chatStyles.chatLayout}>
      {(showSidebar || window.innerWidth >= 768) && <Sidebar onSelectChat={handleSelectChat} />}
      {(!showSidebar || window.innerWidth >= 768) && <ChatWindow onBack={handleBack} />}
    </div>
  )
}

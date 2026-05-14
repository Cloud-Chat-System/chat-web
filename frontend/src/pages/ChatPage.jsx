import { useState, useEffect } from 'react'
import Sidebar from '../components/chat/Sidebar'
import ChatWindow from '../components/chat/ChatWindow'
import { useChatStore } from '../store/useChatStore'
import chatStyles from '../styles/chat.module.css'

export default function ChatPage() {
  const [showSidebar, setShowSidebar] = useState(true)
  const { activeChatId, setActiveChatId, fetchChatRooms, fetchOnlineUsers, initWebSocket, disconnectWebSocket } = useChatStore()

  useEffect(() => {
    fetchChatRooms()
    fetchOnlineUsers()
    initWebSocket()

    return () => {
      disconnectWebSocket()
    }
  }, [fetchChatRooms, fetchOnlineUsers, initWebSocket, disconnectWebSocket])

  const handleSelectChat = () => {
    // On mobile, hide sidebar when a chat is selected
    if (window.innerWidth < 768) {
      setShowSidebar(false)
    }
  }

  const handleBack = () => {
    setActiveChatId(null)
    setShowSidebar(true)
  }

  return (
    <div className={chatStyles.chatLayout}>
      {/* On mobile: show sidebar or chat window, not both */}
      {(showSidebar || window.innerWidth >= 768) && (
        <Sidebar onSelectChat={handleSelectChat} />
      )}
      {(!showSidebar || window.innerWidth >= 768) && (
        <ChatWindow onBack={handleBack} />
      )}
    </div>
  )
}

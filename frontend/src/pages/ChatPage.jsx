import { useState, useEffect } from 'react'
import Sidebar from '../components/chat/Sidebar'
import ChatWindow from '../components/chat/ChatWindow'
import { useChatStore } from '../store/useChatStore'
import chatStyles from '../styles/chat.module.css'

function isWideViewport() {
  return typeof globalThis.innerWidth === 'number' && globalThis.innerWidth >= 768
}

export default function ChatPage() {
  const [showSidebar, setShowSidebar] = useState(true)
  const [isWide, setIsWide] = useState(isWideViewport)
  const { setActiveChatId, fetchChatRooms, fetchOnlineUsers, initWebSocket, disconnectWebSocket } = useChatStore()

  useEffect(() => {
    fetchChatRooms()
    fetchOnlineUsers()
    initWebSocket()

    return () => {
      disconnectWebSocket()
    }
  }, [fetchChatRooms, fetchOnlineUsers, initWebSocket, disconnectWebSocket])

  useEffect(() => {
    const handleResize = () => setIsWide(isWideViewport())
    globalThis.addEventListener('resize', handleResize)
    return () => globalThis.removeEventListener('resize', handleResize)
  }, [])

  const handleSelectChat = () => {
    // On mobile, hide sidebar when a chat is selected
    if (!isWide) {
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
      {(showSidebar || isWide) && (
        <Sidebar onSelectChat={handleSelectChat} />
      )}
      {(!showSidebar || isWide) && (
        <ChatWindow onBack={handleBack} />
      )}
    </div>
  )
}

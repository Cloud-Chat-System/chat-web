import { useRef, useEffect, useState, useCallback } from 'react'
import { useChatStore } from '../../store/useChatStore'
import { useAuthStore } from '../../store/useAuthStore'
import { formatMessageTime, formatDateDivider, shouldShowDateDivider } from '../../utils/formatTime'
import Avatar from '../common/Avatar'
import {
  FiPhone,
  FiVideo,
  FiInfo,
  FiSend,
  FiSmile,
  FiPlus,
  FiImage,
  FiMessageCircle,
  FiArrowLeft,
} from 'react-icons/fi'
import chatStyles from '../../styles/chat.module.css'

export default function ChatWindow({ onBack }) {
  const activeChatId = useChatStore((s) => s.activeChatId)
  const chatRooms = useChatStore((s) => s.chatRooms)
  const messages = useChatStore((s) => s.messages)
  const sendMessage = useChatStore((s) => s.sendMessage)
  const onlineUsers = useChatStore((s) => s.onlineUsers)
  const user = useAuthStore((s) => s.user)

  const [inputValue, setInputValue] = useState('')
  const messagesEndRef = useRef(null)
  const textareaRef = useRef(null)

  const activeRoom = chatRooms.find((r) => r.id === activeChatId)
  const chatMessages = messages[activeChatId] || []

  // Auto scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages.length])

  // Auto resize textarea
  const handleInputChange = useCallback((e) => {
    setInputValue(e.target.value)
    const el = e.target
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 120) + 'px'
  }, [])

  const handleSend = useCallback(() => {
    if (!inputValue.trim() || !activeChatId) return
    sendMessage(activeChatId, inputValue.trim(), user.id)
    setInputValue('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }, [inputValue, activeChatId, sendMessage, user])

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend]
  )

  // No chat selected
  if (!activeRoom) {
    return (
      <div className={chatStyles.chatWindow}>
        <div className={chatStyles.emptyChat}>
          <FiMessageCircle className={chatStyles.emptyChatIcon} />
          <div className={chatStyles.emptyChatTitle}>TSMC Messenger</div>
          <div className={chatStyles.emptyChatDesc}>
            選擇一個聊天室開始對話，或點擊左上角的 ✏️ 按鈕建立新的聊天室
          </div>
        </div>
      </div>
    )
  }
  const isOnline = activeRoom.isGroup ? false : activeRoom.members?.some((m) => m !== user?.id && onlineUsers.has(m))
  return (
    <div className={chatStyles.chatWindow}>
      {/* Header */}
      <div className={chatStyles.chatHeader}>
        <div className={chatStyles.chatHeaderLeft}>
          <button className={chatStyles.backBtn} onClick={onBack} id="chat-back-btn">
            <FiArrowLeft />
          </button>
          <Avatar
            name={activeRoom.name}
            avatar={activeRoom.avatar}
            size="md"
            online={isOnline}
            showStatus={!activeRoom.isGroup}
          />
          <div className={chatStyles.chatHeaderInfo}>
            <div className={chatStyles.chatHeaderName}>{activeRoom.name}</div>
            {!activeRoom.isGroup && (
              <div
                className={`${chatStyles.chatHeaderStatus} ${!isOnline ? chatStyles.chatHeaderOffline : ''
                  }`}
              >
                <span className={chatStyles.chatHeaderStatusDot} />
                {isOnline ? '在線上' : '離線'}
              </div>
            )}
            {activeRoom.isGroup && (
              <div className={chatStyles.chatHeaderStatus} style={{ color: 'var(--text-tertiary)' }}>
                {activeRoom.members?.length || 0} 位成員
              </div>
            )}
          </div>
        </div>
        <div className={chatStyles.chatHeaderActions}>
          <button className={chatStyles.headerIconBtn} title="資訊">
            <FiInfo />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className={chatStyles.messageList} id="message-list">
        {chatMessages.map((msg, index) => {
          const isSelf = msg.senderId === user?.id
          const prevMsg = index > 0 ? chatMessages[index - 1] : null
          const showDate = shouldShowDateDivider(msg, prevMsg)
          const showSenderName = activeRoom.isGroup && !isSelf && prevMsg?.senderId !== msg.senderId

          return (
            <div key={msg.id}>
              {showDate && (
                <div className={chatStyles.dateDivider}>
                  <span className={chatStyles.dateDividerText}>
                    {formatDateDivider(msg.timestamp)}
                  </span>
                </div>
              )}
              <div
                className={`${chatStyles.messageRow} ${isSelf ? chatStyles.messageRowSelf : chatStyles.messageRowOther
                  }`}
              >
                {!isSelf && (
                  <div className={chatStyles.messageAvatar}>
                    {(showSenderName || !prevMsg || prevMsg.senderId !== msg.senderId) ? (
                      <Avatar name={msg.senderName || '未知'} size="sm" />
                    ) : (
                      <div style={{ width: 36 }} />
                    )}
                  </div>
                )}
                <div className={chatStyles.messageBubbleWrap}>
                  {showSenderName && (
                    <div className={chatStyles.messageSenderName}>
                      {msg.senderName || '未知'}
                    </div>
                  )}
                  <div
                    className={`${chatStyles.messageBubble} ${isSelf ? chatStyles.messageBubbleSelf : chatStyles.messageBubbleOther
                      }`}
                  >
                    {msg.content}
                  </div>
                  <div
                    className={`${chatStyles.messageTime} ${isSelf ? chatStyles.messageTimeSelf : chatStyles.messageTimeOther
                      }`}
                  >
                    {formatMessageTime(msg.timestamp)}
                  </div>
                </div>
              </div>
            </div>
          )
        })}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className={chatStyles.messageInputWrap}>
        <div className={chatStyles.messageInputRow}>
          <textarea
            ref={textareaRef}
            className={chatStyles.messageTextarea}
            placeholder="Aa"
            value={inputValue}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            rows={1}
            id="message-input"
          />
          <button
            className={chatStyles.sendBtn}
            onClick={handleSend}
            disabled={!inputValue.trim()}
            title="發送"
            id="send-btn"
          >
            <FiSend />
          </button>
        </div>
      </div>
    </div>
  )
}

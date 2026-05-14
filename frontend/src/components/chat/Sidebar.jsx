import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useChatStore } from '../../store/useChatStore'
import { useAuthStore } from '../../store/useAuthStore'
import { formatChatListTime } from '../../utils/formatTime'
import Avatar from '../common/Avatar'
import NewChatModal from './NewChatModal'
import { FiEdit, FiSearch, FiLogOut, FiMessageCircle } from 'react-icons/fi'
import styles from '../../styles/sidebar.module.css'

export default function Sidebar({ onSelectChat }) {
  const [showNewChat, setShowNewChat] = useState(false)
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)

  const searchQuery = useChatStore((s) => s.searchQuery)
  const setSearchQuery = useChatStore((s) => s.setSearchQuery)
  const filterTab = useChatStore((s) => s.filterTab)
  const setFilterTab = useChatStore((s) => s.setFilterTab)
  const activeChatId = useChatStore((s) => s.activeChatId)
  const setActiveChatId = useChatStore((s) => s.setActiveChatId)
  const markAsRead = useChatStore((s) => s.markAsRead)
  const getFilteredChatRooms = useChatStore((s) => s.getFilteredChatRooms)

  const chatRooms = getFilteredChatRooms()

  const tabs = [
    { key: 'all', label: '全部' },
    //{ key: 'unread', label: '未讀' },
    { key: 'group', label: '群組' },
  ]

  const handleSelectChat = (room) => {
    setActiveChatId(room.id)
    markAsRead(room.id)
    onSelectChat?.()
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <>
      <aside className={styles.sidebar}>
        {/* Header */}
        <div className={styles.sidebarHeader}>
          <div className={styles.sidebarTitleRow}>
            <h1 className={styles.sidebarTitle}>聊天室</h1>
            <div className={styles.sidebarActions}>
              <button
                className={styles.iconBtn}
                onClick={() => setShowNewChat(true)}
                title="新增聊天室"
                id="new-chat-btn"
              >
                <FiEdit />
              </button>
            </div>
          </div>

          {/* Search */}
          <div className={styles.searchWrap}>
            <FiSearch className={styles.searchIcon} />
            <input
              className={styles.searchInput}
              placeholder="搜尋 Messenger Sidebar.jsx"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              id="search-input"
            />
          </div>

          {/* Filter Tabs */}
          <div className={styles.filterTabs}>
            {tabs.map((tab) => (
              <button
                key={tab.key}
                className={`${styles.filterTab} ${filterTab === tab.key ? styles.filterTabActive : ''}`}
                onClick={() => setFilterTab(tab.key)}
                id={`filter-tab-${tab.key}`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Chat List */}
        <div className={styles.chatList}>
          {chatRooms.length === 0 ? (
            <div className={styles.emptyList}>
              <FiMessageCircle className={styles.emptyListIcon} />
              <span>沒有聊天室</span>
            </div>
          ) : (
            chatRooms.map((room) => (
              <div
                key={room.id}
                className={`${styles.chatItem} ${activeChatId === room.id ? styles.chatItemActive : ''}`}
                onClick={() => handleSelectChat(room)}
                id={`chat-item-${room.id}`}
              >
                <div className={styles.chatItemAvatar}>
                  <Avatar
                    name={room.name}
                    avatar={room.avatar}
                    size="md"
                    online={room.online}
                    showStatus={!room.isGroup}
                  />
                </div>
                <div className={styles.chatItemInfo}>
                  <div className={styles.chatItemTop}>
                    <span className={styles.chatItemName}>{room.name}</span>
                    <span className={styles.chatItemTime}>
                      {formatChatListTime(room.lastMessageTime)}
                    </span>
                  </div>
                  <div className={styles.chatItemBottom}>
                    <span className={styles.chatItemMsg}>{room.lastMessage || '尚無訊息'}</span>
                    {room.unreadCount > 0 && (
                      <span className={styles.unreadBadge}>{room.unreadCount}</span>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* User Info */}
        {user && (
          <div className={styles.userInfo}>
            <Avatar name={user.display_name || user.username} size="sm" online showStatus />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className={styles.userInfoName}>{user.display_name || user.username}</div>
              <div className={styles.userInfoEmail}>{user.email}</div>
            </div>
            <button
              className={styles.logoutBtn}
              onClick={handleLogout}
              title="登出"
              id="logout-btn"
            >
              <FiLogOut />
            </button>
          </div>
        )}
      </aside>

      {showNewChat && <NewChatModal onClose={() => setShowNewChat(false)} />}
    </>
  )
}

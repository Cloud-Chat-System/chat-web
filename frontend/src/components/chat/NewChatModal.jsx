import { useState, useEffect } from 'react'
import { useChatStore } from '../../store/useChatStore'
import { useAuthStore } from '../../store/useAuthStore'
import api from '../../utils/api'
import chatStyles from '../../styles/chat.module.css'

export default function NewChatModal({ onClose }) {
  const [mode, setMode] = useState('single') // 'single' | 'group'
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [selectedUsers, setSelectedUsers] = useState([])
  const [groupName, setGroupName] = useState('')
  const [error, setError] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  
  const createChat = useChatStore((s) => s.createChat)
  const createGroupChat = useChatStore((s) => s.createGroupChat)

  // Debounced search
  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([])
      return
    }
    const timer = setTimeout(async () => {
      setIsSearching(true)
      try {
        const res = await api.get(`/users/search?q=${searchQuery}`)
        setSearchResults(res.data)
      } catch (err) {
        console.error("Search failed", err)
      } finally {
        setIsSearching(false)
      }
    }, 500)
    return () => clearTimeout(timer)
  }, [searchQuery])

  const toggleUserSelection = (user) => {
    if (mode === 'single') {
      setSelectedUsers([user])
    } else {
      if (selectedUsers.find(u => u.id === user.id)) {
        setSelectedUsers(selectedUsers.filter(u => u.id !== user.id))
      } else {
        setSelectedUsers([...selectedUsers, user])
      }
    }
  }

  const handleCreate = async () => {
    setError('')

    if (selectedUsers.length === 0) {
      setError('請選擇至少一位使用者')
      return
    }

    try {
      if (mode === 'single') {
        const res = await createChat(selectedUsers[0].id)
        if (res) onClose()
        else setError('建立聊天室失敗')
      } else {
        if (!groupName.trim()) {
          setError('請輸入群組名稱')
          return
        }
        const ids = selectedUsers.map(u => u.id)
        const res = await createGroupChat(groupName.trim(), ids)
        if (res) onClose()
        else setError('建立群組聊天失敗')
      }
    } catch (err) {
      setError('發生錯誤，請稍後再試')
    }
  }

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) onClose()
  }

  return (
    <div className={chatStyles.modalBackdrop} onClick={handleBackdropClick}>
      <div className={chatStyles.modal}>
        <h2 className={chatStyles.modalTitle}>新增聊天室</h2>
        <p className={chatStyles.modalDesc}>
          搜尋使用者名稱或 Email 來建立聊天
        </p>

        {/* Mode Tabs */}
        <div className={chatStyles.modalTabs}>
          <button
            className={`${chatStyles.modalTab} ${mode === 'single' ? chatStyles.modalTabActive : ''}`}
            onClick={() => { setMode('single'); setSelectedUsers([]); setError('') }}
          >
            1 對 1 聊天
          </button>
          <button
            className={`${chatStyles.modalTab} ${mode === 'group' ? chatStyles.modalTabActive : ''}`}
            onClick={() => { setMode('group'); setSelectedUsers([]); setError('') }}
          >
            群組聊天
          </button>
        </div>

        {mode === 'group' && (
          <input
            className={chatStyles.modalInput}
            placeholder="輸入群組名稱"
            value={groupName}
            onChange={(e) => setGroupName(e.target.value)}
            style={{ marginBottom: '1rem' }}
          />
        )}

        <input
          className={chatStyles.modalInput}
          placeholder="搜尋使用者..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          autoFocus
        />

        {error && <p className={chatStyles.modalError}>{error}</p>}

        {/* Selected Users */}
        {selectedUsers.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', margin: '12px 0' }}>
            {selectedUsers.map(u => (
              <div key={u.id} style={{ padding: '4px 8px', background: 'var(--tsmc-blue)', color: 'white', borderRadius: '16px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                {u.display_name || u.username}
                <button onClick={() => toggleUserSelection(u)} style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer', padding: 0 }}>×</button>
              </div>
            ))}
          </div>
        )}

        {/* Search Results */}
        <div style={{ maxHeight: '200px', overflowY: 'auto', border: '1px solid var(--border-color)', borderRadius: '8px', marginTop: '12px' }}>
          {isSearching ? (
            <div style={{ padding: '12px', textAlign: 'center', color: 'var(--text-secondary)' }}>搜尋中...</div>
          ) : searchResults.length > 0 ? (
            searchResults.map(u => {
              const isSelected = selectedUsers.some(su => su.id === u.id)
              return (
                <div 
                  key={u.id} 
                  onClick={() => toggleUserSelection(u)}
                  style={{ 
                    padding: '12px', 
                    borderBottom: '1px solid var(--border-color)',
                    cursor: 'pointer',
                    background: isSelected ? 'var(--hover-bg)' : 'transparent',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 500 }}>{u.display_name || u.username}</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{u.email}</div>
                  </div>
                  {isSelected && <span style={{ color: 'var(--tsmc-blue)' }}>✓</span>}
                </div>
              )
            })
          ) : searchQuery.trim() ? (
            <div style={{ padding: '12px', textAlign: 'center', color: 'var(--text-secondary)' }}>找不到使用者</div>
          ) : (
            <div style={{ padding: '12px', textAlign: 'center', color: 'var(--text-secondary)' }}>請輸入關鍵字搜尋</div>
          )}
        </div>

        <div className={chatStyles.modalBtnRow} style={{ marginTop: '20px' }}>
          <button className={chatStyles.modalBtnCancel} onClick={onClose}>取消</button>
          <button className={chatStyles.modalBtnConfirm} onClick={handleCreate} disabled={selectedUsers.length === 0}>建立</button>
        </div>
      </div>
    </div>
  )
}

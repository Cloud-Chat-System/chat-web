import { create } from 'zustand'
import api from '../utils/api'
import { useAuthStore } from './useAuthStore'

let ws = null;
let reconnectTimer = null;
let pingTimer = null;

function mapRoom(room) {
  return {
    id: room.id,
    name: room.name,
    isGroup: room.room_type === 'group',
    members: room.members.map(m => m.id),
    lastMessage: room.last_message,
    lastMessageTime: room.last_message_at,
    createdAt: room.created_at,
    unreadCount: room.unread_count,
    membersList: room.members
  }
}

function mapMessage(message) {
  return {
    id: message.id,
    chatId: message.room_id,
    senderId: message.sender_id,
    content: message.content,
    timestamp: message.created_at,
    senderName: message.sender_name
  }
}

function sortRooms(rooms) {
  return [...rooms].sort(
    (a, b) => new Date(b.lastMessageTime || b.createdAt) - new Date(a.lastMessageTime || a.createdAt)
  )
}

function mergeMessages(existingMessages = [], incomingMessages = []) {
  const byId = new Map()
  ;[...existingMessages, ...incomingMessages].forEach((message) => {
    if (message?.id != null) byId.set(message.id, message)
  })
  return [...byId.values()].sort((a, b) => {
    const timeDiff = new Date(a.timestamp) - new Date(b.timestamp)
    return timeDiff || a.id - b.id
  })
}

function upsertRoom(rooms, room) {
  const existingIndex = rooms.findIndex((r) => r.id === room.id)
  if (existingIndex === -1) {
    return sortRooms([...rooms, room])
  }

  const nextRooms = [...rooms]
  nextRooms[existingIndex] = { ...nextRooms[existingIndex], ...room }
  return sortRooms(nextRooms)
}

function clearPingTimer() {
  if (pingTimer) {
    clearInterval(pingTimer)
    pingTimer = null
  }
}

export const useChatStore = create((set, get) => ({
  chatRooms: [],
  messages: {},
  activeChatId: null,
  searchQuery: '',
  filterTab: 'all', // 'all' | 'unread' | 'group'
  onlineUsers: new Set(),
  isLoading: false,

  upsertChatRoom: (room) => {
    const mappedRoom = mapRoom(room)
    set((state) => ({
      chatRooms: upsertRoom(state.chatRooms, mappedRoom),
    }))
  },

  upsertMessage: (message, options = {}) => {
    const mappedMessage = mapMessage(message)
    set((state) => {
      const chatId = mappedMessage.chatId
      const previousMessages = state.messages[chatId] || []
      const alreadyExists = previousMessages.some((msg) => msg.id === mappedMessage.id)
      const nextMessages = mergeMessages(previousMessages, [mappedMessage])
      const currentUserId = useAuthStore.getState().user?.id

      const nextRooms = state.chatRooms.map((room) => {
        if (room.id !== chatId) return room

        const shouldIncrementUnread =
          !alreadyExists &&
          !options.fromSelf &&
          state.activeChatId !== chatId &&
          mappedMessage.senderId !== currentUserId

        return {
          ...room,
          lastMessage: mappedMessage.content,
          lastMessageTime: mappedMessage.timestamp,
          unreadCount: shouldIncrementUnread ? room.unreadCount + 1 : room.unreadCount,
        }
      })

      return {
        messages: { ...state.messages, [chatId]: nextMessages },
        chatRooms: sortRooms(nextRooms),
      }
    })
  },

  initWebSocket: () => {
    const token = localStorage.getItem('token');
    if (!token) return;
    
    if (ws) {
      ws.onclose = null;
      ws.close();
    }
    clearPingTimer();

    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    const wsUrl =
      import.meta.env.VITE_WS_URL ||
      apiBaseUrl.replace(/^http/, 'ws').replace(/\/$/, '') + '/ws';
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      ws.send(JSON.stringify({ token }));
      get().fetchChatRooms();
      const activeChatId = get().activeChatId;
      if (activeChatId) {
        get().fetchMessages(activeChatId);
      }
      
      // Ping periodically to keep alive
      clearPingTimer();
      pingTimer = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, 30000);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'new_message') {
          get().upsertMessage(data.data);
        } else if (data.type === 'chatroom_created') {
          get().upsertChatRoom(data.data);
        } else if (data.type === 'presence') {
          set((state) => {
            const newOnline = new Set(state.onlineUsers);
            if (data.status === 'online') {
              newOnline.add(data.user_id);
            } else {
              newOnline.delete(data.user_id);
            }
            return { onlineUsers: newOnline };
          });
        }
      } catch (err) {
        console.error("Failed to parse WS message", err);
      }
    };

    ws.onclose = () => {
      // Reconnect logic
      clearPingTimer();
      clearTimeout(reconnectTimer);
      reconnectTimer = setTimeout(() => {
        if (useAuthStore.getState().user) {
          get().initWebSocket();
        }
      }, 3000);
    };
  },

  fetchChatRooms: async () => {
    set({ isLoading: true });
    try {
      const res = await api.get('/chatrooms');
      const rooms = res.data.map(mapRoom);
      set({ chatRooms: sortRooms(rooms), isLoading: false });
    } catch (error) {
      console.error("Fetch chatrooms failed", error);
      set({ isLoading: false });
    }
  },

  fetchMessages: async (chatId) => {
    try {
      const res = await api.get(`/chatrooms/${chatId}/messages?limit=200`);
      const msgs = res.data.messages.map(mapMessage);
      
      set((state) => {
        const mergedMessages = mergeMessages(state.messages[chatId] || [], msgs)
        return {
          messages: { ...state.messages, [chatId]: mergedMessages }
        }
      });
    } catch (error) {
      console.error("Fetch messages failed", error);
    }
  },

  fetchOnlineUsers: async () => {
    try {
      const res = await api.get('/users/online');
      set({ onlineUsers: new Set(res.data) });
    } catch (error) {
      console.error("Failed to get online users", error);
    }
  },

  setActiveChatId: (id) => {
    set({ activeChatId: id })
    if (id) {
      get().fetchMessages(id);
      get().markAsRead(id);
    }
  },

  setSearchQuery: (query) => set({ searchQuery: query }),

  setFilterTab: (tab) => set({ filterTab: tab }),

  getFilteredChatRooms: () => {
    const { chatRooms, searchQuery, filterTab, onlineUsers } = get()
    
    let filtered = [...chatRooms]

    if (filterTab === 'unread') {
      filtered = filtered.filter((room) => room.unreadCount > 0)
    } else if (filterTab === 'group') {
      filtered = filtered.filter((room) => room.isGroup)
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      filtered = filtered.filter((room) =>
        room.name?.toLowerCase().includes(q)
      )
    }

    return filtered.map(room => ({
      ...room,
      online: room.isGroup ? false : room.members.some(m => m !== useAuthStore.getState().user?.id && onlineUsers.has(m))
    }));
  },

  sendMessage: async (chatId, content) => {
    try {
      const res = await api.post(`/chatrooms/${chatId}/messages`, { content });
      get().upsertMessage(res.data, { fromSelf: true });
    } catch (error) {
      console.error("Send message failed", error);
    }
  },

  createChat: async (userId) => {
    try {
      const res = await api.post('/chatrooms', {
        room_type: 'direct',
        member_ids: [userId],
        name: ''
      });
      
      get().upsertChatRoom(res.data);
      set({ activeChatId: res.data.id });
      get().fetchMessages(res.data.id);
      return res.data;
    } catch (error) {
      console.error("Create chat failed", error);
      return null;
    }
  },

  createGroupChat: async (name, memberIds) => {
    try {
      const res = await api.post('/chatrooms', {
        room_type: 'group',
        member_ids: memberIds,
        name: name
      });
      
      get().upsertChatRoom(res.data);
      set({ activeChatId: res.data.id });
      get().fetchMessages(res.data.id);
      return res.data;
    } catch (error) {
      console.error("Create group chat failed", error);
      return null;
    }
  },

  markAsRead: async (chatId) => {
    try {
      await api.put(`/chatrooms/${chatId}/read`);
      set((state) => ({
        chatRooms: state.chatRooms.map((room) =>
          room.id === chatId ? { ...room, unreadCount: 0 } : room
        ),
      }));
    } catch (error) {
      console.error("Mark read failed", error);
    }
  },
  
  disconnectWebSocket: () => {
    if (ws) {
      ws.onclose = null;
      ws.close();
      ws = null;
    }
    clearTimeout(reconnectTimer);
    clearPingTimer();
  }
}))

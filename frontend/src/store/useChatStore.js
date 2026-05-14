import { create } from 'zustand'
import api from '../utils/api'
import { useAuthStore } from './useAuthStore'

let ws = null;
let reconnectTimer = null;

export const useChatStore = create((set, get) => ({
  chatRooms: [],
  messages: {},
  activeChatId: null,
  searchQuery: '',
  filterTab: 'all', // 'all' | 'unread' | 'group'
  onlineUsers: new Set(),
  isLoading: false,

  initWebSocket: () => {
    const token = localStorage.getItem('token');
    if (!token) return;
    
    if (ws) {
      ws.close();
    }

    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    const wsUrl =
      import.meta.env.VITE_WS_URL ||
      apiBaseUrl.replace(/^http/, 'ws').replace(/\/$/, '') + '/ws';
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      ws.send(JSON.stringify({ token }));
      
      // Ping periodically to keep alive
      setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, 30000);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'new_message') {
          const msg = data.data;
          
          set((state) => {
            const chatId = msg.room_id;
            const updatedMessages = {
              ...state.messages,
              [chatId]: [...(state.messages[chatId] || []), {
                id: msg.id,
                chatId: msg.room_id,
                senderId: msg.sender_id,
                content: msg.content,
                timestamp: msg.created_at,
                senderName: msg.sender_name
              }],
            }
            
            const updatedRooms = state.chatRooms.map((room) =>
              room.id === chatId
                ? {
                    ...room,
                    lastMessage: msg.content,
                    lastMessageTime: msg.created_at,
                    unreadCount:
                      state.activeChatId !== chatId && msg.sender_id !== useAuthStore.getState().user?.id
                        ? room.unreadCount + 1
                        : room.unreadCount,
                  }
                : room
            )

            // Re-sort rooms
            updatedRooms.sort((a, b) => new Date(b.lastMessageTime || b.createdAt) - new Date(a.lastMessageTime || a.createdAt))
            
            return { messages: updatedMessages, chatRooms: updatedRooms }
          });
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
      const rooms = res.data.map(r => ({
        id: r.id,
        name: r.name,
        isGroup: r.room_type === 'group',
        members: r.members.map(m => m.id),
        lastMessage: r.last_message,
        lastMessageTime: r.last_message_at,
        createdAt: r.created_at,
        unreadCount: r.unread_count,
        membersList: r.members
      }));
      set({ chatRooms: rooms, isLoading: false });
    } catch (error) {
      console.error("Fetch chatrooms failed", error);
      set({ isLoading: false });
    }
  },

  fetchMessages: async (chatId) => {
    try {
      const res = await api.get(`/chatrooms/${chatId}/messages?limit=200`);
      const msgs = res.data.messages.map(m => ({
        id: m.id,
        chatId: m.room_id,
        senderId: m.sender_id,
        content: m.content,
        timestamp: m.created_at,
        senderName: m.sender_name
      }));
      
      set((state) => ({
        messages: { ...state.messages, [chatId]: msgs }
      }));
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
      await api.post(`/chatrooms/${chatId}/messages`, { content });
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
      
      await get().fetchChatRooms();
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
      
      await get().fetchChatRooms();
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
      ws.close();
      ws = null;
    }
    clearTimeout(reconnectTimer);
  }
}))

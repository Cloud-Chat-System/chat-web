import { create } from 'zustand'
import api from '../utils/api'

export const useAuthStore = create((set) => ({
  user: null,
  isLoading: true, // Start true for initial check
  error: null,
  isInitialized: false,

  initAuth: async () => {
    const token = localStorage.getItem('token');
    if (!token) {
      set({ isLoading: false, isInitialized: true });
      return;
    }
    
    try {
      const res = await api.get('/auth/me');
      set({ user: res.data, isLoading: false, isInitialized: true });
    } catch (error) {
      localStorage.removeItem('token');
      set({ user: null, isLoading: false, isInitialized: true });
    }
  },

  login: async (email, password) => {
    set({ isLoading: true, error: null })
    try {
      const res = await api.post('/auth/login', { email, password });
      localStorage.setItem('token', res.data.token);
      set({ user: res.data.user, isLoading: false, error: null });
      return res.data.user;
    } catch (error) {
      const err = error.response?.data?.detail || '帳號或密碼錯誤';
      set({ isLoading: false, error: err });
      throw new Error(err);
    }
  },

  loginWithGoogle: async () => {
    set({ isLoading: true, error: null })
    // Simulate until real OAuth is added
    try {
      const res = await api.post('/auth/google', {
        email: 'haozhe.xie@tsmc.com',
        name: '謝浩哲',
        google_id: '123456'
      });
      localStorage.setItem('token', res.data.token);
      set({ user: res.data.user, isLoading: false });
      return res.data.user;
    } catch (error) {
      set({ isLoading: false, error: 'Google 登入失敗' });
      throw error;
    }
  },

  register: async (name, email, password) => {
    set({ isLoading: true, error: null })
    try {
      await api.post('/auth/register', { 
        username: email.split('@')[0], // Extract from email
        display_name: name,
        email, 
        password 
      });
      set({ isLoading: false });
      return { name, email };
    } catch (error) {
      const err = error.response?.data?.detail || '註冊失敗';
      set({ isLoading: false, error: err });
      throw new Error(err);
    }
  },

  logout: async () => {
    try {
      await api.post('/auth/logout');
    } catch (e) {
      // Ignore logout error
    }
    localStorage.removeItem('token');
    set({ user: null, error: null });
  },

  clearError: () => set({ error: null }),
}))

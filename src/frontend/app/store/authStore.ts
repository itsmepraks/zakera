import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import api from '../lib/api'

interface User {
  id: string
  username: string
  email: string
  full_name?: string
  is_active: boolean
  created_at: string
}

interface AuthStore {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  login: (username: string, password: string) => Promise<void>
  register: (username: string, email: string, password: string, fullName?: string) => Promise<void>
  logout: () => Promise<void>
  checkAuth: () => Promise<void>
  clearError: () => void
}

export const useAuthStore = create<AuthStore>()((
  (set) => ({
    user: null,
    isAuthenticated: false,
    isLoading: false,
    error: null,

    login: async (username: string, password: string) => {
      set({ isLoading: true, error: null })
      try {
        await api.login(username, password)
        const user = await api.getCurrentUser()
        set({ user, isAuthenticated: true, isLoading: false })
      } catch (error: any) {
        set({
          error: error.response?.data?.detail || 'Login failed',
          isLoading: false,
        })
        throw error
      }
    },

    register: async (username: string, email: string, password: string, fullName?: string) => {
      set({ isLoading: true, error: null })
      try {
        await api.register(username, email, password, fullName)
        // Auto-login after registration
        await api.login(username, password)
        const user = await api.getCurrentUser()
        set({ user, isAuthenticated: true, isLoading: false })
      } catch (error: any) {
        set({
          error: error.response?.data?.detail || 'Registration failed',
          isLoading: false,
        })
        throw error
      }
    },

    logout: async () => {
      set({ isLoading: true })
      try {
        await api.logout()
      } finally {
        set({ user: null, isAuthenticated: false, isLoading: false })
      }
    },

    checkAuth: async () => {
      set({ isLoading: true })
      try {
        const user = await api.getCurrentUser()
        set({ user, isAuthenticated: true, isLoading: false })
      } catch (error) {
        set({ user: null, isAuthenticated: false, isLoading: false })
      }
    },

    clearError: () => set({ error: null }),
  })
))

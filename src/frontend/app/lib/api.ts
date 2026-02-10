import axios, { AxiosInstance } from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

class APIClient {
  private client: AxiosInstance
  private token: string | null = null

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config) => {
        if (this.token) {
          config.headers.Authorization = `Bearer ${this.token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          this.clearToken()
          // Redirect to login or trigger auth flow
          if (typeof window !== 'undefined') {
            window.location.href = '/login'
          }
        }
        return Promise.reject(error)
      }
    )

    // Load token from localStorage on client
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('auth_token')
    }
  }

  setToken(token: string) {
    this.token = token
    if (typeof window !== 'undefined') {
      localStorage.setItem('auth_token', token)
    }
  }

  clearToken() {
    this.token = null
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token')
    }
  }

  // Auth endpoints
  async register(username: string, email: string, password: string, fullName?: string) {
    const response = await this.client.post('/api/v1/auth/register', {
      username,
      email,
      password,
      full_name: fullName,
    })
    return response.data
  }

  async login(username: string, password: string) {
    const response = await this.client.post('/api/v1/auth/login/json', {
      username,
      password,
    })
    this.setToken(response.data.access_token)
    return response.data
  }

  async logout() {
    try {
      await this.client.post('/api/v1/auth/logout')
    } finally {
      this.clearToken()
    }
  }

  async getCurrentUser() {
    const response = await this.client.get('/api/v1/auth/me')
    return response.data
  }

  // Conversation endpoints
  async createConversation(title: string = 'New Conversation', systemPrompt?: string) {
    const response = await this.client.post('/api/v1/conversations', {
      title,
      system_prompt: systemPrompt,
    })
    return response.data
  }

  async getConversations(archived: boolean = false, search?: string) {
    const params: any = { archived }
    if (search) params.search = search
    const response = await this.client.get('/api/v1/conversations', { params })
    return response.data
  }

  async getConversation(conversationId: string) {
    const response = await this.client.get(`/api/v1/conversations/${conversationId}`)
    return response.data
  }

  async updateConversation(
    conversationId: string,
    updates: {
      title?: string
      system_prompt?: string
      is_archived?: boolean
      is_pinned?: boolean
    }
  ) {
    const response = await this.client.patch(`/api/v1/conversations/${conversationId}`, updates)
    return response.data
  }

  async deleteConversation(conversationId: string) {
    const response = await this.client.delete(`/api/v1/conversations/${conversationId}`)
    return response.data
  }

  // Chat endpoints
  async sendMessage(conversationId: string, message: string) {
    const response = await this.client.post('/api/v1/chat', {
      conversation_id: conversationId,
      message,
    })
    return response.data
  }

  // WebSocket connection
  createWebSocket(conversationId: string): WebSocket {
    const wsUrl = (API_URL.replace('http', 'ws') + `/api/v1/ws/chat/${conversationId}`)
    return new WebSocket(wsUrl)
  }
}

export const api = new APIClient()
export default api

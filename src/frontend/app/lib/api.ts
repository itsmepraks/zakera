import axios, { AxiosInstance } from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface AgentStep {
  id: string
  run_id: string
  sequence: number
  step_type: string
  status: string
  label: string
  detail?: string
  tool_name?: string
  tokens?: number
  latency_ms?: number
  error?: string
  metadata?: Record<string, any>
  started_at?: string
  completed_at?: string
}

export interface AgentApproval {
  id: string
  run_id: string
  step_id?: string
  status: string
  tool_name: string
  reason?: string
  requested_payload?: Record<string, any>
  resolved_at?: string
  created_at?: string
}

export interface AgentRun {
  id: string
  conversation_id: string
  user_id?: string
  status: string
  model_name: string
  tools_enabled: boolean
  error?: string
  total_tokens?: number
  created_at?: string
  completed_at?: string
  user_message_id?: string
  assistant_message_id?: string
  metadata?: Record<string, any>
  steps?: AgentStep[]
  approvals?: AgentApproval[]
}

export interface AgentStreamEvent {
  type: string
  run_id?: string
  step_id?: string
  approval_id?: string
  status?: string
  label?: string
  detail?: string
  tool?: string
  chunk?: string
  content?: string
  error?: string
  reason?: string
  usage?: Record<string, number>
  parameters?: Record<string, any>
}

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
  async createConversation(title: string = 'New Conversation', systemPrompt?: string, modelName?: string) {
    const response = await this.client.post('/api/v1/conversations', {
      title,
      system_prompt: systemPrompt,
      model_name: modelName,
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

  async streamMessage(
    conversationId: string,
    message: string,
    options: {
      toolsEnabled?: boolean
      onEvent: (event: AgentStreamEvent) => void
    }
  ) {
    const response = await fetch(`${API_URL}/api/v1/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
      },
      body: JSON.stringify({
        conversation_id: conversationId,
        message,
        tools_enabled: options.toolsEnabled ?? true,
        stream: true,
      }),
    })

    if (!response.ok || !response.body) {
      const detail = await response.text()
      throw new Error(detail || 'Failed to stream message')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { value, done } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const frames = buffer.split('\n\n')
      buffer = frames.pop() ?? ''

      for (const frame of frames) {
        const line = frame
          .split('\n')
          .find((part) => part.startsWith('data: '))
        if (!line) continue
        try {
          options.onEvent(JSON.parse(line.slice(6)))
        } catch {
          // Ignore malformed SSE frames for forward compatibility.
        }
      }
    }
  }

  async getAgentRuns(conversationId: string): Promise<AgentRun[]> {
    const response = await this.client.get('/api/v1/agent-runs', {
      params: { conversation_id: conversationId },
    })
    return response.data
  }

  async getAgentRun(runId: string): Promise<AgentRun> {
    const response = await this.client.get(`/api/v1/agent-runs/${runId}`)
    return response.data
  }

  async approveAgentAction(runId: string, approvalId: string) {
    const response = await this.client.post(
      `/api/v1/agent-runs/${runId}/approvals/${approvalId}/approve`
    )
    return response.data
  }

  async rejectAgentAction(runId: string, approvalId: string) {
    const response = await this.client.post(
      `/api/v1/agent-runs/${runId}/approvals/${approvalId}/reject`
    )
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

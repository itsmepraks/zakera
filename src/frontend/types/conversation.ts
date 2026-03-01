/**
 * Conversation Management Type Definitions
 */

export interface Message {
  id: string;
  conversationId: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  model?: string;
  tokens?: {
    prompt: number;
    completion: number;
    total: number;
  };
  metadata?: {
    branchPoint?: boolean;
    parentMessageId?: string;
    tools?: string[];
    error?: string;
  };
}

export interface Branch {
  id: string;
  conversationId: string;
  name: string;
  parentId: string | null;
  createdAt: string;
  lastActivity: string;
  messageCount: number;
  messages: Message[];
  metadata?: {
    model?: string;
    tags?: string[];
    description?: string;
    color?: string;
  };
}

export interface Conversation {
  id: string;
  title: string;
  userId: string;
  createdAt: string;
  updatedAt: string;
  lastMessageAt?: string;
  messageCount: number;
  currentBranchId: string;
  branches: Branch[];
  tags: string[];
  metadata?: {
    model?: string;
    temperature?: number;
    pinned?: boolean;
    starred?: boolean;
    archived?: boolean;
    color?: string;
    folder?: string;
  };
  status: 'active' | 'archived' | 'deleted';
}

export interface ConversationFilter {
  search?: string;
  tags?: string[];
  models?: string[];
  dateRange?: {
    start: string;
    end: string;
  };
  status?: Conversation['status'][];
  starred?: boolean;
  pinned?: boolean;
  hasAttachments?: boolean;
  minMessages?: number;
  maxMessages?: number;
}

export interface ConversationSort {
  field: 'createdAt' | 'updatedAt' | 'lastMessageAt' | 'title' | 'messageCount';
  direction: 'asc' | 'desc';
}

export interface ConversationGroup {
  key: string;
  label: string;
  conversations: Conversation[];
  count: number;
}

export interface BulkOperation {
  type: 'delete' | 'archive' | 'tag' | 'export' | 'move';
  conversationIds: string[];
  params?: any;
  progress?: number;
  status: 'pending' | 'running' | 'completed' | 'failed';
  error?: string;
}

export interface ConversationAction {
  id: string;
  label: string;
  icon: string;
  shortcut?: string;
  handler: (conversation: Conversation) => void | Promise<void>;
  disabled?: (conversation: Conversation) => boolean;
  dangerous?: boolean;
}

export interface TimelineEvent {
  id: string;
  type: 'message' | 'branch' | 'merge' | 'tag' | 'edit';
  timestamp: string;
  data: any;
  actor?: string;
}

export interface ConversationStats {
  total: number;
  active: number;
  archived: number;
  byModel: Record<string, number>;
  byTag: Record<string, number>;
  totalMessages: number;
  averageMessages: number;
  oldestDate: string;
  newestDate: string;
}

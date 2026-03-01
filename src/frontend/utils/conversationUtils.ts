/**
 * Conversation Utility Functions
 */

import { Conversation, Branch, Message, ConversationStats } from '../types/conversation';

/**
 * Calculate statistics for conversations
 */
export function calculateConversationStats(conversations: Conversation[]): ConversationStats {
  const active = conversations.filter(c => c.status === 'active');
  const archived = conversations.filter(c => c.status === 'archived');
  
  const byModel: Record<string, number> = {};
  const byTag: Record<string, number> = {};
  let totalMessages = 0;
  
  conversations.forEach(conv => {
    totalMessages += conv.messageCount;
    
    const model = conv.metadata?.model || 'unknown';
    byModel[model] = (byModel[model] || 0) + 1;
    
    conv.tags.forEach(tag => {
      byTag[tag] = (byTag[tag] || 0) + 1;
    });
  });

  const dates = conversations
    .map(c => new Date(c.createdAt).getTime())
    .filter(d => !isNaN(d));

  return {
    total: conversations.length,
    active: active.length,
    archived: archived.length,
    byModel,
    byTag,
    totalMessages,
    averageMessages: conversations.length > 0 ? totalMessages / conversations.length : 0,
    oldestDate: dates.length > 0 ? new Date(Math.min(...dates)).toISOString() : '',
    newestDate: dates.length > 0 ? new Date(Math.max(...dates)).toISOString() : '',
  };
}

/**
 * Format conversation title for display
 */
export function formatConversationTitle(conversation: Conversation, maxLength = 50): string {
  const title = conversation.title || 'Untitled Conversation';
  return title.length > maxLength ? `${title.slice(0, maxLength)}...` : title;
}

/**
 * Get conversation age in human-readable format
 */
export function getConversationAge(conversation: Conversation): string {
  const now = new Date();
  const created = new Date(conversation.createdAt);
  const diffMs = now.getTime() - created.getTime();
  
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);
  
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  if (diffDays < 365) return `${Math.floor(diffDays / 30)}mo ago`;
  return `${Math.floor(diffDays / 365)}y ago`;
}

/**
 * Get last activity time
 */
export function getLastActivity(conversation: Conversation): string {
  const date = conversation.lastMessageAt || conversation.updatedAt;
  return getConversationAge({ ...conversation, createdAt: date } as Conversation);
}

/**
 * Check if conversation matches filter
 */
export function matchesFilter(conversation: Conversation, filter: any): boolean {
  // Search text
  if (filter.search) {
    const searchLower = filter.search.toLowerCase();
    const titleMatch = conversation.title?.toLowerCase().includes(searchLower);
    const tagMatch = conversation.tags.some(tag => tag.toLowerCase().includes(searchLower));
    if (!titleMatch && !tagMatch) return false;
  }

  // Tags
  if (filter.tags?.length > 0) {
    if (!filter.tags.some((tag: string) => conversation.tags.includes(tag))) {
      return false;
    }
  }

  // Models
  if (filter.models?.length > 0) {
    if (!filter.models.includes(conversation.metadata?.model)) {
      return false;
    }
  }

  // Status
  if (filter.status?.length > 0) {
    if (!filter.status.includes(conversation.status)) {
      return false;
    }
  }

  // Starred
  if (filter.starred !== undefined) {
    if (conversation.metadata?.starred !== filter.starred) {
      return false;
    }
  }

  // Pinned
  if (filter.pinned !== undefined) {
    if (conversation.metadata?.pinned !== filter.pinned) {
      return false;
    }
  }

  // Date range
  if (filter.dateRange) {
    const created = new Date(conversation.createdAt).getTime();
    const start = new Date(filter.dateRange.start).getTime();
    const end = new Date(filter.dateRange.end).getTime();
    if (created < start || created > end) {
      return false;
    }
  }

  // Message count
  if (filter.minMessages !== undefined) {
    if (conversation.messageCount < filter.minMessages) {
      return false;
    }
  }
  if (filter.maxMessages !== undefined) {
    if (conversation.messageCount > filter.maxMessages) {
      return false;
    }
  }

  return true;
}

/**
 * Sort conversations
 */
export function sortConversations(
  conversations: Conversation[],
  sort: { field: string; direction: 'asc' | 'desc' }
): Conversation[] {
  const sorted = [...conversations].sort((a, b) => {
    let aVal: any;
    let bVal: any;

    switch (sort.field) {
      case 'title':
        aVal = a.title?.toLowerCase() || '';
        bVal = b.title?.toLowerCase() || '';
        break;
      case 'messageCount':
        aVal = a.messageCount;
        bVal = b.messageCount;
        break;
      case 'lastMessageAt':
        aVal = new Date(a.lastMessageAt || a.updatedAt).getTime();
        bVal = new Date(b.lastMessageAt || b.updatedAt).getTime();
        break;
      case 'updatedAt':
        aVal = new Date(a.updatedAt).getTime();
        bVal = new Date(b.updatedAt).getTime();
        break;
      case 'createdAt':
      default:
        aVal = new Date(a.createdAt).getTime();
        bVal = new Date(b.createdAt).getTime();
        break;
    }

    if (aVal < bVal) return sort.direction === 'asc' ? -1 : 1;
    if (aVal > bVal) return sort.direction === 'asc' ? 1 : -1;
    return 0;
  });

  return sorted;
}

/**
 * Group conversations
 */
export function groupConversations(
  conversations: Conversation[],
  groupBy: string
): Map<string, Conversation[]> {
  const groups = new Map<string, Conversation[]>();

  conversations.forEach(conv => {
    let key: string;

    switch (groupBy) {
      case 'date':
        key = getDateGroup(conv.createdAt);
        break;
      case 'model':
        key = conv.metadata?.model || 'Unknown Model';
        break;
      case 'tag':
        key = conv.tags[0] || 'Untagged';
        break;
      case 'status':
        key = conv.status.charAt(0).toUpperCase() + conv.status.slice(1);
        break;
      default:
        key = 'All Conversations';
        break;
    }

    if (!groups.has(key)) {
      groups.set(key, []);
    }
    groups.get(key)!.push(conv);
  });

  return groups;
}

/**
 * Get date group label
 */
function getDateGroup(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - date.getTime()) / 86400000);

  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return 'This Week';
  if (diffDays < 30) return 'This Month';
  if (diffDays < 90) return 'Last 3 Months';
  if (diffDays < 365) return 'This Year';
  return date.getFullYear().toString();
}

/**
 * Export conversations to various formats
 */
export async function exportConversations(
  conversations: Conversation[],
  format: 'json' | 'markdown' | 'pdf' | 'csv'
): Promise<Blob> {
  switch (format) {
    case 'json':
      return new Blob(
        [JSON.stringify(conversations, null, 2)],
        { type: 'application/json' }
      );
    
    case 'markdown':
      const markdown = conversations.map(conv => 
        `# ${conv.title}\n\nCreated: ${conv.createdAt}\nMessages: ${conv.messageCount}\n\n---\n`
      ).join('\n');
      return new Blob([markdown], { type: 'text/markdown' });
    
    case 'csv':
      const csv = [
        'ID,Title,Created,Updated,Messages,Status,Tags',
        ...conversations.map(c => 
          `${c.id},"${c.title}",${c.createdAt},${c.updatedAt},${c.messageCount},${c.status},"${c.tags.join(', ')}"`
        )
      ].join('\n');
      return new Blob([csv], { type: 'text/csv' });
    
    case 'pdf':
      // Would integrate with PDF library
      throw new Error('PDF export not yet implemented');
    
    default:
      throw new Error(`Unsupported format: ${format}`);
  }
}

/**
 * Download blob as file
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Local storage service for conversation persistence.
 * 
 * Provides methods to save, load, and manage conversations
 * in browser's local storage with automatic backup.
 */

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  model?: string;
  tokens?: number;
}

interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  created_at: string;
  updated_at: string;
  model: string;
  total_tokens?: number;
  metadata?: Record<string, any>;
}

const STORAGE_KEY = 'zakera_conversations';
const BACKUP_KEY = 'zakera_conversations_backup';
const MAX_CONVERSATIONS = 100; // Limit to prevent storage issues

export class ConversationStorage {
  /**
   * Save a conversation to local storage.
   */
  static saveConversation(conversation: Conversation): void {
    try {
      const conversations = this.getAllConversations();
      const existingIndex = conversations.findIndex(
        (c) => c.id === conversation.id
      );

      if (existingIndex !== -1) {
        conversations[existingIndex] = conversation;
      } else {
        conversations.unshift(conversation);
        
        // Limit number of stored conversations
        if (conversations.length > MAX_CONVERSATIONS) {
          conversations.pop();
        }
      }

      localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
      this.createBackup(conversations);
    } catch (error) {
      console.error('Failed to save conversation:', error);
      throw new Error('Failed to save conversation to local storage');
    }
  }

  /**
   * Get all conversations from local storage.
   */
  static getAllConversations(): Conversation[] {
    try {
      const data = localStorage.getItem(STORAGE_KEY);
      if (!data) return [];
      return JSON.parse(data) as Conversation[];
    } catch (error) {
      console.error('Failed to load conversations:', error);
      // Try to restore from backup
      return this.restoreFromBackup();
    }
  }

  /**
   * Get a specific conversation by ID.
   */
  static getConversation(id: string): Conversation | null {
    const conversations = this.getAllConversations();
    return conversations.find((c) => c.id === id) || null;
  }

  /**
   * Delete a conversation by ID.
   */
  static deleteConversation(id: string): void {
    try {
      const conversations = this.getAllConversations();
      const filtered = conversations.filter((c) => c.id !== id);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered));
      this.createBackup(filtered);
    } catch (error) {
      console.error('Failed to delete conversation:', error);
      throw new Error('Failed to delete conversation');
    }
  }

  /**
   * Update conversation metadata.
   */
  static updateConversation(
    id: string,
    updates: Partial<Conversation>
  ): void {
    const conversation = this.getConversation(id);
    if (!conversation) {
      throw new Error('Conversation not found');
    }

    const updated = {
      ...conversation,
      ...updates,
      updated_at: new Date().toISOString(),
    };

    this.saveConversation(updated);
  }

  /**
   * Search conversations by query.
   */
  static searchConversations(query: string): Conversation[] {
    const conversations = this.getAllConversations();
    const lowerQuery = query.toLowerCase();

    return conversations.filter((conv) => {
      if (conv.title.toLowerCase().includes(lowerQuery)) return true;
      return conv.messages.some((msg) =>
        msg.content.toLowerCase().includes(lowerQuery)
      );
    });
  }

  /**
   * Get conversations by model.
   */
  static getConversationsByModel(model: string): Conversation[] {
    const conversations = this.getAllConversations();
    return conversations.filter((c) => c.model === model);
  }

  /**
   * Get storage statistics.
   */
  static getStats(): {
    totalConversations: number;
    totalMessages: number;
    totalTokens: number;
    storageUsed: number;
    storageLimit: number;
  } {
    const conversations = this.getAllConversations();
    const totalMessages = conversations.reduce(
      (sum, conv) => sum + conv.messages.length,
      0
    );
    const totalTokens = conversations.reduce(
      (sum, conv) => sum + (conv.total_tokens || 0),
      0
    );

    // Estimate storage used
    const data = localStorage.getItem(STORAGE_KEY) || '';
    const storageUsed = new Blob([data]).size;
    const storageLimit = 5 * 1024 * 1024; // 5MB typical limit

    return {
      totalConversations: conversations.length,
      totalMessages,
      totalTokens,
      storageUsed,
      storageLimit,
    };
  }

  /**
   * Export all conversations as JSON.
   */
  static exportAll(): string {
    const conversations = this.getAllConversations();
    const exportData = {
      version: '1.0',
      exported_at: new Date().toISOString(),
      conversations,
    };
    return JSON.stringify(exportData, null, 2);
  }

  /**
   * Import conversations from JSON.
   */
  static importAll(jsonData: string): number {
    try {
      const data = JSON.parse(jsonData);
      const importedConversations = data.conversations || data;

      if (!Array.isArray(importedConversations)) {
        throw new Error('Invalid import format');
      }

      const currentConversations = this.getAllConversations();
      const merged = [...currentConversations];
      let imported = 0;

      for (const conv of importedConversations) {
        // Validate structure
        if (!conv.id || !conv.title || !Array.isArray(conv.messages)) {
          continue;
        }

        // Check if conversation already exists
        const existingIndex = merged.findIndex((c) => c.id === conv.id);
        if (existingIndex === -1) {
          merged.unshift(conv);
          imported++;
        }
      }

      // Limit total conversations
      const limited = merged.slice(0, MAX_CONVERSATIONS);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(limited));
      this.createBackup(limited);

      return imported;
    } catch (error) {
      console.error('Failed to import conversations:', error);
      throw new Error('Failed to import conversations');
    }
  }

  /**
   * Clear all conversations.
   */
  static clearAll(): void {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(BACKUP_KEY);
  }

  /**
   * Create a backup of conversations.
   */
  private static createBackup(conversations: Conversation[]): void {
    try {
      localStorage.setItem(
        BACKUP_KEY,
        JSON.stringify({
          timestamp: new Date().toISOString(),
          conversations,
        })
      );
    } catch (error) {
      console.warn('Failed to create backup:', error);
    }
  }

  /**
   * Restore conversations from backup.
   */
  private static restoreFromBackup(): Conversation[] {
    try {
      const backupData = localStorage.getItem(BACKUP_KEY);
      if (!backupData) return [];

      const backup = JSON.parse(backupData);
      console.info('Restored conversations from backup:', backup.timestamp);
      return backup.conversations || [];
    } catch (error) {
      console.error('Failed to restore from backup:', error);
      return [];
    }
  }
}

export default ConversationStorage;

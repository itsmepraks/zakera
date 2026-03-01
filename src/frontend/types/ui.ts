/**
 * UI State Type Definitions
 */

export interface UIPreferences {
  theme: 'light' | 'dark' | 'auto';
  density: 'compact' | 'comfortable' | 'spacious';
  conversationView: 'list' | 'grid' | 'timeline';
  sidebarCollapsed: boolean;
  showBranchTree: boolean;
  showMetadata: boolean;
  fontSize: number;
  animationsEnabled: boolean;
}

export interface ViewState {
  selectedConversationId: string | null;
  selectedMessageId: string | null;
  selectedBranchId: string | null;
  expandedGroups: Set<string>;
  scrollPosition: number;
}

export interface ModalState {
  type: 'create' | 'edit' | 'delete' | 'export' | 'share' | null;
  data?: any;
  isOpen: boolean;
}

export interface ToastNotification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  description?: string;
  duration?: number;
  action?: {
    label: string;
    handler: () => void;
  };
}

export interface KeyboardShortcut {
  key: string;
  ctrlKey?: boolean;
  shiftKey?: boolean;
  altKey?: boolean;
  metaKey?: boolean;
  description: string;
  handler: () => void;
  enabled: boolean;
}

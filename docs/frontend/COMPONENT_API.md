# Component API Reference

Complete API documentation for all conversation management components.

## Table of Contents

1. [ConversationBranching](#conversationbranching)
2. [ConversationBulkActions](#conversationbulkactions)
3. [ConversationTimeline](#conversationtimeline)
4. [QuickActionsMenu](#quickactionsmenu)
5. [ConversationActions](#conversationactions)
6. [ConversationSorting](#conversationsorting)
7. [ConversationComparison](#conversationcomparison)
8. [ConversationListEnhanced](#conversationlistenhanced)

---

## ConversationBranching

Interactive visual interface for managing conversation branches.

### Props

```tsx
interface ConversationBranchingProps {
  conversationId: string;        // Current conversation ID
  branches: Branch[];            // Array of all branches
  currentBranchId: string;       // Active branch ID
  onBranchSwitch: (branchId: string) => void;  // Switch to different branch
  onBranchCreate: (params: BranchCreateParams) => Promise<void>;  // Create new branch
  onBranchMerge: (sourceId: string, targetId: string) => Promise<void>;  // Merge branches
  onBranchDelete: (branchId: string) => Promise<void>;  // Delete branch
  onBranchRename: (branchId: string, newName: string) => Promise<void>;  // Rename branch
  className?: string;            // Optional CSS class
}

type BranchCreateParams = {
  parentId: string;              // Parent branch ID
  name: string;                  // New branch name
  fromMessageId?: string;        // Optional: branch from specific message
};
```

### Usage

```tsx
import { ConversationBranching } from './components/conversation/ConversationBranching';

function MyComponent() {
  const handleBranchSwitch = (branchId: string) => {
    // Switch to the selected branch
    console.log('Switching to branch:', branchId);
  };

  return (
    <ConversationBranching
      conversationId="conv-123"
      branches={branches}
      currentBranchId="main"
      onBranchSwitch={handleBranchSwitch}
      onBranchCreate={async (params) => {
        await api.createBranch(params);
      }}
      onBranchMerge={async (src, target) => {
        await api.mergeBranches(src, target);
      }}
      onBranchDelete={async (id) => {
        await api.deleteBranch(id);
      }}
      onBranchRename={async (id, name) => {
        await api.renameBranch(id, name);
      }}
    />
  );
}
```

### Features

- ✅ Visual tree representation
- ✅ Create, rename, delete branches
- ✅ Merge with conflict detection
- ✅ Double-click to switch
- ✅ Inline rename editing
- ✅ Branch metadata display
- ✅ Keyboard navigation

---

## ConversationBulkActions

Provides bulk operations on multiple selected conversations.

### Props

```tsx
interface ConversationBulkActionsProps {
  conversations: Conversation[];   // All available conversations
  selectedIds: Set<string>;        // Currently selected IDs
  onSelectionChange: (ids: Set<string>) => void;  // Selection change handler
  onBulkDelete: (ids: string[]) => Promise<void>; // Bulk delete handler
  onBulkArchive: (ids: string[]) => Promise<void>; // Bulk archive handler
  onBulkExport: (ids: string[], format: ExportFormat) => Promise<void>; // Bulk export
  onBulkTag: (ids: string[], tags: string[]) => Promise<void>; // Bulk tag
}

type ExportFormat = 'json' | 'markdown' | 'pdf' | 'csv';
```

### Usage

```tsx
import { ConversationBulkActions } from './components/conversation/ConversationBulkActions';

function MyComponent() {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  return (
    <ConversationBulkActions
      conversations={conversations}
      selectedIds={selectedIds}
      onSelectionChange={setSelectedIds}
      onBulkDelete={async (ids) => {
        await Promise.all(ids.map(id => api.delete(id)));
      }}
      onBulkArchive={async (ids) => {
        await api.bulkArchive(ids);
      }}
      onBulkExport={async (ids, format) => {
        const blob = await api.exportConversations(ids, format);
        downloadBlob(blob, `conversations.${format}`);
      }}
      onBulkTag={async (ids, tags) => {
        await api.bulkAddTags(ids, tags);
      }}
    />
  );
}
```

### Features

- ✅ Multi-select with checkboxes
- ✅ Select all / deselect all
- ✅ Bulk delete with confirmation
- ✅ Bulk archive
- ✅ Bulk export (multiple formats)
- ✅ Bulk tagging
- ✅ Progress indicators
- ✅ Keyboard shortcuts

---

## ConversationTimeline

Interactive timeline visualization of conversation history.

### Props

```tsx
interface ConversationTimelineProps {
  messages: Message[];            // All messages to display
  branches: Branch[];             // All branches in conversation
  currentBranchId: string;        // Active branch
  selectedMessageId?: string;     // Currently selected message
  onMessageSelect: (messageId: string) => void;  // Message selection handler
  onBranchSwitch: (branchId: string) => void;    // Branch switch handler
}
```

### Usage

```tsx
import { ConversationTimeline } from './components/conversation/ConversationTimeline';

function MyComponent() {
  const [selectedMessageId, setSelectedMessageId] = useState<string | undefined>();

  return (
    <ConversationTimeline
      messages={currentBranch.messages}
      branches={conversation.branches}
      currentBranchId={conversation.currentBranchId}
      selectedMessageId={selectedMessageId}
      onMessageSelect={setSelectedMessageId}
      onBranchSwitch={(branchId) => {
        switchToBranch(branchId);
      }}
    />
  );
}
```

### Features

- ✅ Chronological message timeline
- ✅ Interactive scrubber
- ✅ Grouped by date
- ✅ Branch point indicators
- ✅ Message preview on hover
- ✅ Branch switcher
- ✅ Scroll to any point

---

## QuickActionsMenu

Command palette (Cmd+K style) for quick access to all actions.

### Props

```tsx
interface QuickActionsMenuProps {
  actions: Action[];           // Available actions
  isOpen: boolean;             // Menu open state
  onClose: () => void;         // Close handler
}

interface Action {
  id: string;                  // Unique identifier
  label: string;               // Display label
  description?: string;        // Optional description
  icon: string;                // Icon (emoji or icon name)
  category: string;            // Action category
  shortcut?: string;           // Keyboard shortcut label
  handler: () => void | Promise<void>;  // Action handler
  keywords?: string[];         // Search keywords
}
```

### Usage

```tsx
import { QuickActionsMenu } from './components/conversation/QuickActionsMenu';

function MyComponent() {
  const [showQuickActions, setShowQuickActions] = useState(false);

  const actions: Action[] = [
    {
      id: 'new-conversation',
      label: 'New Conversation',
      description: 'Start a new chat',
      icon: '➕',
      category: 'Conversations',
      shortcut: '⌘N',
      handler: () => createNewConversation(),
      keywords: ['create', 'start', 'new', 'begin'],
    },
    // ... more actions
  ];

  // Open with Cmd+K
  useKeyboardShortcuts([{
    key: 'k',
    metaKey: true,
    handler: () => setShowQuickActions(true),
    enabled: true,
  }]);

  return (
    <QuickActionsMenu
      actions={actions}
      isOpen={showQuickActions}
      onClose={() => setShowQuickActions(false)}
    />
  );
}
```

### Features

- ✅ Fuzzy search
- ✅ Keyboard navigation (↑↓, Enter)
- ✅ Categorized actions
- ✅ Shortcut labels
- ✅ Recent actions
- ✅ ESC to close

---

## Custom Hooks

### useConversationBranching

Manages branch state and tree operations.

```tsx
const {
  selectedBranchId,       // Currently selected branch
  setSelectedBranchId,    // Set selected branch
  branchTree,             // Tree structure (parent->children map)
  getBranchPath,          // Get path from root to branch
  canMergeBranches,       // Check if two branches can merge
  getCommonAncestor,      // Find common ancestor
  getBranchDepth,         // Get depth in tree
  getDescendants,         // Get all descendant branches
} = useConversationBranching(branches, currentBranchId);
```

### useConversationBulkSelect

Manages multi-select state.

```tsx
const {
  selectAll,              // Select all conversations
  deselectAll,            // Clear all selections
  toggleSelection,        // Toggle single item
  selectRange,            // Select range of items
  toggleRange,            // Toggle range
  isAllSelected,          // All items selected?
  hasSelection,           // Any items selected?
  isSomeSelected,         // Some (but not all) selected?
} = useConversationBulkSelect(conversations, selectedIds, onSelectionChange);
```

### useKeyboardShortcuts

Registers keyboard shortcuts.

```tsx
const shortcuts: KeyboardShortcut[] = [
  {
    key: 'k',
    metaKey: true,
    description: 'Quick actions',
    handler: () => setShowQuickActions(true),
    enabled: true,
  },
];

const { getShortcutLabel } = useKeyboardShortcuts(shortcuts);

// Returns formatted label like "⌘K"
const label = getShortcutLabel(shortcuts[0]);
```

---

## Type Definitions

### Conversation

```tsx
interface Conversation {
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
```

### Branch

```tsx
interface Branch {
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
```

### Message

```tsx
interface Message {
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
```

---

## Examples

See `src/frontend/examples/` for complete working examples:

- `ConversationManager.tsx` - Full integration
- `BasicUsage.tsx` - Simple implementation
- `AdvancedFeatures.tsx` - All features combined

---

**Last Updated**: February 2026  
**Version**: 1.0.0

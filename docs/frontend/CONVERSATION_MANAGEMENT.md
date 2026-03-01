# Conversation Management UI - Feature Guide

Comprehensive guide to the conversation management features in Zakera's frontend.

## Overview

The conversation management UI provides professional-grade tools for organizing, searching, and navigating conversations. Built with React and TypeScript, it offers a modern, accessible, and performant experience.

## Features

### 1. Conversation Branching

**Visual Branch Tree**
- Interactive tree visualization of conversation branches
- Git-like branching model with parent-child relationships
- Drag-and-drop branch reordering
- Branch metadata (creation time, message count, last activity)

**Branch Operations**
- Create new branches from any point
- Merge branches with conflict resolution
- Delete branches (with confirmation)
- Rename branches inline
- Switch between branches with smooth transitions

**Usage Example:**
```tsx
import { ConversationBranching } from './components/conversation/ConversationBranching';

<ConversationBranching
  conversationId={conversationId}
  branches={branches}
  currentBranchId={currentBranchId}
  onBranchSwitch={(branchId) => handleBranchSwitch(branchId)}
  onBranchCreate={async (params) => await createBranch(params)}
  onBranchMerge={async (source, target) => await mergeBranches(source, target)}
  onBranchDelete={async (branchId) => await deleteBranch(branchId)}
  onBranchRename={async (branchId, name) => await renameBranch(branchId, name)}
/>
```

### 2. Bulk Operations

**Multi-Select**
- Select multiple conversations with checkboxes
- Select all / deselect all
- Range selection with Shift+Click
- Keyboard shortcuts (Cmd+A, Cmd+D)

**Bulk Actions**
- Delete multiple conversations
- Archive/unarchive in bulk
- Add tags to multiple conversations
- Export multiple conversations (JSON, MD, PDF, CSV)
- Move to folders

**Progress Tracking**
- Visual progress indicators
- Cancel long-running operations
- Error handling with retry
- Success/failure notifications

**Usage Example:**
```tsx
import { ConversationBulkActions } from './components/conversation/ConversationBulkActions';

const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

<ConversationBulkActions
  conversations={conversations}
  selectedIds={selectedIds}
  onSelectionChange={setSelectedIds}
  onBulkDelete={async (ids) => await deleteConversations(ids)}
  onBulkArchive={async (ids) => await archiveConversations(ids)}
  onBulkExport={async (ids, format) => await exportConversations(ids, format)}
  onBulkTag={async (ids, tags) => await tagConversations(ids, tags)}
/>
```

### 3. Timeline Visualization

**Interactive Timeline**
- Chronological view of all messages
- Timeline scrubber for navigation
- Branch point indicators
- Group by date/model/tag

**Features**
- Scroll to any point in history
- Preview messages on hover
- Jump to branches from timeline
- Activity heatmap
- Time-based filtering

**Usage Example:**
```tsx
import { ConversationTimeline } from './components/conversation/ConversationTimeline';

<ConversationTimeline
  messages={messages}
  branches={branches}
  currentBranchId={currentBranchId}
  selectedMessageId={selectedMessageId}
  onMessageSelect={(msgId) => handleMessageSelect(msgId)}
  onBranchSwitch={(branchId) => handleBranchSwitch(branchId)}
/>
```

### 4. Quick Actions Menu

**Command Palette (Cmd+K)**
- Fuzzy search across all actions
- Keyboard navigation (↑↓, Enter)
- Categorized actions
- Recent actions tracking
- Custom shortcuts

**Available Actions**
- New conversation
- Search conversations
- Create branch
- Export conversation
- Toggle theme
- Open settings
- Navigate to...

**Usage Example:**
```tsx
import { QuickActionsMenu } from './components/conversation/QuickActionsMenu';

const actions = [
  {
    id: 'new-conversation',
    label: 'New Conversation',
    description: 'Start a new chat',
    icon: '➕',
    category: 'Conversations',
    shortcut: '⌘N',
    handler: () => createNewConversation(),
    keywords: ['create', 'start', 'begin'],
  },
  // ... more actions
];

<QuickActionsMenu
  actions={actions}
  isOpen={showQuickActions}
  onClose={() => setShowQuickActions(false)}
/>
```

### 5. Advanced Filtering

**Filter Criteria**
- Full-text search
- Date range selection
- Model filtering
- Tag filtering
- Status (active/archived)
- Star/pin status
- Message count range

**Filter Presets**
- Save custom filters
- Quick access to common filters
- Share filter presets
- Export/import filters

**Smart Suggestions**
- Tag autocomplete
- Model suggestions
- Recent searches
- Popular filters

### 6. Sorting & Grouping

**Sort Options**
- Date created/updated
- Last message time
- Title (alphabetical)
- Message count
- Custom sort orders

**Group Options**
- By date (today, yesterday, this week, etc.)
- By model used
- By tags
- By status
- Custom grouping

**Persistence**
- Save sort preferences
- Per-view settings
- Sync across devices

### 7. Keyboard Shortcuts

See [KEYBOARD_SHORTCUTS.md](./KEYBOARD_SHORTCUTS.md) for complete list.

**Most Common:**
- `Cmd+K` / `Ctrl+K` - Quick actions
- `Cmd+N` / `Ctrl+N` - New conversation
- `Cmd+F` / `Ctrl+F` - Search
- `Cmd+B` / `Ctrl+B` - Toggle branches
- `Cmd+A` / `Ctrl+A` - Select all
- `Escape` - Clear selection / Close dialog
- `↑` `↓` - Navigate
- `Enter` - Open/select

## Component Architecture

### Component Hierarchy

```
App
├── ConversationList
│   ├── SearchBar
│   ├── FilterPanel
│   ├── ConversationBulkActions
│   ├── ConversationSorting
│   └── ConversationItem (repeated)
│
├── ConversationView
│   ├── ConversationBranching
│   ├── ConversationTimeline
│   ├── ConversationActions
│   └── MessageList
│       └── Message (repeated)
│
└── QuickActionsMenu
```

### State Management

**Zustand Stores:**
- `conversationStore.ts` - Conversation data and operations
- `filterStore.ts` - Filter state and presets
- `uiStore.ts` - UI preferences and view state

**Custom Hooks:**
- `useConversationBranching` - Branch management
- `useConversationBulkSelect` - Multi-select logic
- `useConversationFilters` - Filter state
- `useKeyboardShortcuts` - Keyboard navigation
- `useConversationActions` - Action handlers
- `useConversationSort` - Sorting logic
- `useConversationSync` - Real-time sync
- `useConversationTimeline` - Timeline data

## Styling

### CSS Modules

Each component has its own CSS module:
```
ConversationBranching.tsx
ConversationBranching.css  <-- Component styles
```

### CSS Variables

**Light Theme:**
```css
--bg-primary: #ffffff;
--bg-secondary: #f3f4f6;
--text-primary: #111827;
--text-secondary: #6b7280;
--primary-color: #3b82f6;
--border-color: #e5e7eb;
```

**Dark Theme:**
```css
--bg-primary: #1f2937;
--bg-secondary: #374151;
--text-primary: #f9fafb;
--text-secondary: #9ca3af;
--primary-color: #3b82f6;
--border-color: #4b5563;
```

### Responsive Design

All components are mobile-responsive with breakpoints:
- Desktop: > 1024px
- Tablet: 768px - 1024px
- Mobile: < 768px

## Accessibility

### ARIA Support

All components include proper ARIA labels:
```tsx
<button
  aria-label="Delete conversation"
  aria-describedby="delete-description"
  aria-pressed={isSelected}
>
  Delete
</button>
```

### Keyboard Navigation

- All interactive elements are keyboard accessible
- Logical tab order
- Focus indicators
- Escape to close dialogs
- Arrow key navigation in lists

### Screen Reader Support

- Semantic HTML
- Descriptive labels
- Status announcements
- Error messages

## Performance

### Optimizations

**React Optimization:**
- `useMemo` for expensive calculations
- `useCallback` for stable references
- `React.memo` for pure components
- Virtualization for long lists

**Code Splitting:**
```tsx
const ConversationBranching = lazy(() => 
  import('./components/conversation/ConversationBranching')
);
```

**Debouncing:**
```tsx
const debouncedSearch = useDeb ounce(searchValue => {
  performSearch(searchValue);
}, 300);
```

## Testing

### Unit Tests

```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { ConversationBranching } from './ConversationBranching';

test('creates new branch', async () => {
  const onBranchCreate = jest.fn();
  
  render(<ConversationBranching onBranchCreate={onBranchCreate} />);
  
  fireEvent.click(screen.getByText('+ New Branch'));
  fireEvent.change(screen.getByPlaceholderText('Branch name'), {
    target: { value: 'Test Branch' },
  });
  fireEvent.click(screen.getByText('Create'));
  
  expect(onBranchCreate).toHaveBeenCalledWith({
    parentId: expect.any(String),
    name: 'Test Branch',
  });
});
```

### Integration Tests

```tsx
test('bulk delete workflow', async () => {
  // Test complete flow from selection to deletion
});
```

## Best Practices

### Component Usage

1. **Always provide all required props**
2. **Use TypeScript for type safety**
3. **Handle loading and error states**
4. **Provide accessible labels**
5. **Test keyboard navigation**

### Performance

1. **Virtualize long lists** (>100 items)
2. **Debounce search inputs** (300ms)
3. **Lazy load heavy components**
4. **Memoize expensive calculations**
5. **Use code splitting**

### Accessibility

1. **Test with keyboard only**
2. **Test with screen reader**
3. **Ensure sufficient color contrast**
4. **Provide skip links**
5. **Use semantic HTML**

## Troubleshooting

### Common Issues

**Problem**: Branches not showing
**Solution**: Check that `branches` prop includes all required fields

**Problem**: Keyboard shortcuts not working
**Solution**: Ensure shortcuts are enabled in `useKeyboardShortcuts` hook

**Problem**: Bulk actions slow
**Solution**: Implement progress indicators and consider chunking large operations

**Problem**: Theme not applying
**Solution**: Verify `data-theme` attribute is set on root element

## Examples

See `src/frontend/examples/` for complete working examples:
- Basic conversation list
- Branch management
- Bulk operations
- Custom filters
- Timeline view

## Further Reading

- [Component API Documentation](./COMPONENT_API.md)
- [Keyboard Shortcuts Reference](./KEYBOARD_SHORTCUTS.md)
- [TypeScript Types](../../src/frontend/types/conversation.ts)
- [Custom Hooks](../../src/frontend/hooks/)

---

**Version**: 1.0.0  
**Last Updated**: February 2026  
**Status**: Production Ready

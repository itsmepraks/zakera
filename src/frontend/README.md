# Zakera Frontend - Conversation Management UI

Modern React frontend for Zakera AI Chat Agent with professional-grade conversation management features.

## Features

### 🌳 Conversation Branching
- Visual tree representation of conversation branches
- Git-like branching with merge/split operations
- Interactive branch switching and navigation
- Branch comparison and diff viewing

### ✅ Bulk Operations
- Multi-select conversations with checkboxes
- Bulk delete, archive, export, and tag
- Progress indicators for long operations
- Keyboard shortcuts for efficiency

### ⏱️ Timeline Visualization
- Interactive timeline of conversation history
- Timeline scrubber for navigation
- Branch point indicators
- Time-based grouping and filtering

### ⚡ Quick Actions (Cmd+K)
- Command palette for quick access
- Fuzzy search across all actions
- Keyboard-first navigation
- Recent actions tracking

### 🔍 Advanced Search & Filters
- Full-text search across conversations
- Multi-criteria filtering (date, model, tags, status)
- Saved filter presets
- Smart search suggestions

### ⌨️ Keyboard Shortcuts
- Comprehensive keyboard navigation
- Customizable shortcuts
- Platform-aware (Mac/Windows/Linux)
- Accessibility support

### 🎨 Modern UI/UX
- Dark mode support
- Responsive design (mobile, tablet, desktop)
- Smooth animations and transitions
- Loading skeletons
- Toast notifications

## Quick Start

### Installation

```bash
cd src/frontend
npm install
```

### Development

```bash
npm run dev
```

Open http://localhost:5173

### Build

```bash
npm run build
```

Output in `dist/`

## Project Structure

```
src/frontend/
├── components/
│   ├── conversation/
│   │   ├── ConversationBranching.tsx
│   │   ├── ConversationBulkActions.tsx
│   │   ├── ConversationTimeline.tsx
│   │   ├── QuickActionsMenu.tsx
│   │   └── ... (20+ components)
│   ├── chat/
│   └── common/
├── hooks/
│   ├── useConversationBranching.ts
│   ├── useConversationBulkSelect.ts
│   ├── useKeyboardShortcuts.ts
│   └── ... (8 hooks)
├── store/
│   ├── conversationStore.ts
│   ├── filterStore.ts
│   └── uiStore.ts
├── types/
│   ├── conversation.ts
│   ├── filter.ts
│   └── ui.ts
├── utils/
└── styles/
```

## Components

### Core Components

#### ConversationBranching
Visual branch tree with full CRUD operations.

```tsx
import { ConversationBranching } from './components/conversation/ConversationBranching';

<ConversationBranching
  conversationId={id}
  branches={branches}
  currentBranchId={currentId}
  onBranchSwitch={handleSwitch}
  onBranchCreate={handleCreate}
  onBranchMerge={handleMerge}
  onBranchDelete={handleDelete}
  onBranchRename={handleRename}
/>
```

#### ConversationBulkActions
Multi-select and bulk operations.

```tsx
import { ConversationBulkActions } from './components/conversation/ConversationBulkActions';

<ConversationBulkActions
  conversations={conversations}
  selectedIds={selectedIds}
  onSelectionChange={setSelectedIds}
  onBulkDelete={handleBulkDelete}
  onBulkArchive={handleBulkArchive}
  onBulkExport={handleBulkExport}
  onBulkTag={handleBulkTag}
/>
```

#### QuickActionsMenu
Command palette (Cmd+K).

```tsx
import { QuickActionsMenu } from './components/conversation/QuickActionsMenu';

const actions = [
  {
    id: 'new',
    label: 'New Conversation',
    icon: '➕',
    category: 'Conversations',
    handler: createNew,
  },
];

<QuickActionsMenu
  actions={actions}
  isOpen={showMenu}
  onClose={() => setShowMenu(false)}
/>
```

### Custom Hooks

#### useConversationBranching
Manage branch state and operations.

```tsx
import { useConversationBranching } from './hooks/useConversationBranching';

const {
  branchTree,
  getBranchPath,
  canMergeBranches,
  getCommonAncestor,
} = useConversationBranching(branches, currentBranchId);
```

#### useKeyboardShortcuts
Register keyboard shortcuts.

```tsx
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';

const shortcuts = [
  {
    key: 'k',
    metaKey: true,
    description: 'Quick actions',
    handler: () => setShowQuickActions(true),
    enabled: true,
  },
];

useKeyboardShortcuts(shortcuts);
```

## Styling

### CSS Modules
Each component has a CSS module:

```tsx
import './ComponentName.css';
```

### CSS Variables
Define in `:root` or `[data-theme="..."]`:

```css
:root {
  --bg-primary: #ffffff;
  --text-primary: #111827;
  --primary-color: #3b82f6;
}

[data-theme="dark"] {
  --bg-primary: #1f2937;
  --text-primary: #f9fafb;
}
```

### Responsive
Use standard breakpoints:

```css
/* Mobile */
@media (max-width: 768px) { }

/* Tablet */
@media (min-width: 769px) and (max-width: 1024px) { }

/* Desktop */
@media (min-width: 1025px) { }
```

## State Management

### Zustand Stores

#### conversationStore
```tsx
import { useConversationStore } from './store/conversationStore';

const conversations = useConversationStore(state => state.conversations);
const addConversation = useConversationStore(state => state.addConversation);
```

#### filterStore
```tsx
import { useFilterStore } from './store/filterStore';

const activeFilter = useFilterStore(state => state.activeFilter);
const setFilter = useFilterStore(state => state.setFilter);
```

## Testing

### Unit Tests

```bash
npm test
```

### Test with UI

```bash
npm run test:ui
```

### Coverage

```bash
npm run test:coverage
```

### Example Test

```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { ConversationBranching } from './ConversationBranching';

test('creates branch', () => {
  const onCreate = jest.fn();
  render(<ConversationBranching onBranchCreate={onCreate} />);
  
  fireEvent.click(screen.getByText('+ New Branch'));
  // ... assertions
});
```

## Keyboard Shortcuts

See [docs/frontend/KEYBOARD_SHORTCUTS.md](../../docs/frontend/KEYBOARD_SHORTCUTS.md) for complete list.

**Most Used:**
- `Cmd+K` - Quick actions
- `Cmd+N` - New conversation
- `Cmd+F` - Search
- `Cmd+B` - Toggle branches
- `Cmd+A` - Select all

## Accessibility

### ARIA Labels
All interactive elements have aria-labels:

```tsx
<button aria-label="Delete conversation" aria-describedby="hint">
  Delete
</button>
```

### Keyboard Navigation
- Tab through all interactive elements
- Arrow keys for list navigation
- Enter/Space to activate
- Escape to close dialogs

### Screen Readers
- Semantic HTML
- Status announcements
- Error messages
- Progress indicators

## Performance

### Optimization Techniques

1. **React.memo** for pure components
2. **useMemo** for expensive calculations
3. **useCallback** for stable references
4. **Code splitting** with lazy loading
5. **Virtualization** for long lists
6. **Debouncing** for search inputs

## Browser Support

- Chrome/Edge: Latest 2 versions
- Firefox: Latest 2 versions
- Safari: Latest 2 versions
- Mobile: iOS 14+, Android 10+

## Documentation

- [Conversation Management Guide](../../docs/frontend/CONVERSATION_MANAGEMENT.md)
- [Keyboard Shortcuts Reference](../../docs/frontend/KEYBOARD_SHORTCUTS.md)
- [Component API](../../docs/frontend/COMPONENT_API.md)
- [TypeScript Types](./types/)

## Contributing

1. Create feature branch
2. Write tests
3. Update documentation
4. Submit PR

See [CONTRIBUTING.md](../../CONTRIBUTING.md)

## License

MIT License - see LICENSE file

---

**Version**: 0.8.0  
**React**: 18.2+  
**TypeScript**: 5.3+  
**Status**: Production Ready 🚀

# Frontend Architecture - Conversation Management

## Overview

The Zakera frontend is built with React 18, TypeScript, and Zustand for state management. It follows modern React patterns with functional components, hooks, and CSS modules.

## Technology Stack

- **React 18.2+**: UI library
- **TypeScript 5.3+**: Type safety
- **Zustand**: State management
- **Vite**: Build tool
- **Vitest**: Testing framework
- **CSS Modules**: Scoped styling

## Architecture Patterns

### Component Structure

```
Components (Presentational)
  ↑ Props
  ↓ Events
Hooks (Logic)
  ↑ Actions
  ↓ State
Stores (State Management)
  ↑ API Calls
  ↓ Data
API Layer
```

### Data Flow

```
User Action
  ↓
Component Event Handler
  ↓
Custom Hook
  ↓
Store Action
  ↓
API Call (if needed)
  ↓
State Update
  ↓
Component Re-render
```

## Folder Structure

```
src/frontend/
├── components/         # React components
│   ├── conversation/  # Conversation management
│   ├── chat/          # Chat interface
│   └── common/        # Shared components
├── hooks/             # Custom hooks
├── store/             # Zustand stores
├── types/             # TypeScript types
├── utils/             # Utility functions
├── styles/            # Global styles
├── examples/          # Usage examples
└── __tests__/         # Tests
```

## Component Design Principles

### 1. Single Responsibility
Each component does one thing well.

### 2. Composition Over Inheritance
Build complex UIs from simple components.

### 3. Props Interface
Well-defined TypeScript interfaces for all props.

### 4. Controlled Components
Parent manages state, child receives props.

### 5. Accessibility First
ARIA labels, keyboard navigation, semantic HTML.

## State Management

### Zustand Stores

**conversationStore.ts**
- Manages conversation data
- Handles CRUD operations
- Syncs with API

**filterStore.ts**
- Manages filter state
- Saves filter presets
- Persists to localStorage

**uiStore.ts**
- UI preferences
- View state
- Theme settings

### When to Use Each

- **Component State** (`useState`): Local UI state (open/closed, hover)
- **Custom Hooks**: Reusable logic (branching, bulk select)
- **Stores**: Global state (conversations, filters, preferences)

## Performance Optimization

### React Optimization

```tsx
// Memoize expensive calculations
const filtered = useMemo(
  () => conversations.filter(matchesFilter),
  [conversations, filter]
);

// Memoize callbacks
const handleClick = useCallback(
  () => doSomething(param),
  [param]
);

// Memo components
export const MyComponent = React.memo(Component);
```

### Code Splitting

```tsx
const ConversationBranching = lazy(() => 
  import('./components/conversation/ConversationBranching')
);

<Suspense fallback={<LoadingSkeleton />}>
  <ConversationBranching />
</Suspense>
```

### Virtualization

For lists > 100 items:

```tsx
import { FixedSizeList } from 'react-window';

<FixedSizeList
  height={600}
  itemCount={conversations.length}
  itemSize={80}
  width="100%"
>
  {({ index, style }) => (
    <div style={style}>
      <ConversationCard conversation={conversations[index]} />
    </div>
  )}
</FixedSizeList>
```

## Testing Strategy

### Test Types

1. **Unit Tests**: Individual components and hooks
2. **Integration Tests**: Component interactions
3. **Accessibility Tests**: ARIA, keyboard navigation
4. **Visual Tests**: Snapshot testing (optional)

### Testing Tools

- **Vitest**: Test runner
- **@testing-library/react**: Component testing
- **@testing-library/user-event**: User interaction simulation
- **@testing-library/jest-dom**: Custom matchers

### Example Test

```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { ConversationBranching } from './ConversationBranching';

test('creates new branch', async () => {
  const onCreate = jest.fn();
  render(<ConversationBranching onBranchCreate={onCreate} />);
  
  fireEvent.click(screen.getByText('+ New Branch'));
  // ... test implementation
});
```

## Styling Approach

### CSS Modules

Scoped styles per component:

```tsx
import './Component.css';

<div className="component-name">...</div>
```

### CSS Variables

Themeable with CSS custom properties:

```css
:root {
  --primary-color: #3b82f6;
  --text-primary: #111827;
}

[data-theme="dark"] {
  --primary-color: #3b82f6;
  --text-primary: #f9fafb;
}
```

### Responsive Design

Mobile-first with breakpoints:

```css
/* Mobile default */
.component { }

/* Tablet */
@media (min-width: 768px) { }

/* Desktop */
@media (min-width: 1024px) { }
```

## API Integration

### axios Client

```tsx
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to all requests
api.interceptors.request.use(config => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

### Store Actions with API

```tsx
const useConversationStore = create((set) => ({
  conversations: [],
  
  loadConversations: async () => {
    const response = await api.get('/conversations');
    set({ conversations: response.data });
  },
  
  createConversation: async (data) => {
    const response = await api.post('/conversations', data);
    set(state => ({
      conversations: [response.data, ...state.conversations],
    }));
    return response.data;
  },
}));
```

## Best Practices

### 1. TypeScript
- Define interfaces for all props
- Use strict mode
- Avoid `any` type
- Export types for reuse

### 2. Components
- Small, focused components
- Clear prop interfaces
- Handle loading/error states
- Accessibility attributes

### 3. Hooks
- Extract reusable logic
- Clear dependencies
- Document return values
- Unit test hooks

### 4. State
- Lift state up when needed
- Use stores for global state
- Persist important state
- Avoid prop drilling

### 5. Performance
- Memoize when appropriate
- Lazy load heavy components
- Virtualize long lists
- Debounce expensive operations

## Future Enhancements

- [ ] React Server Components
- [ ] Concurrent rendering
- [ ] Progressive Web App (PWA)
- [ ] Offline support
- [ ] Real-time with WebSocket
- [ ] Advanced animations

---

**Last Updated**: February 2026  
**React Version**: 18.2+  
**TypeScript Version**: 5.3+

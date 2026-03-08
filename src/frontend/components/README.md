# Zakera Frontend Components

## 🎨 Enhanced Chat UI Components

Modern, feature-rich React components for the Zakera AI Chat Agent interface.

## 📦 Components

### 1. EnhancedChatUI
**Main integration component** bringing together all chat features.

```typescript
import { EnhancedChatUI } from './components/EnhancedChatUI/EnhancedChatUI';

<EnhancedChatUI
  conversationId="conv-123"
  messages={messages}
  onSendMessage={handleSend}
  onReact={handleReact}
  onFeedback={handleFeedback}
  currentModel="gpt-4-turbo"
/>
```

**Features:** Template integration, reactions, summary panel, enhanced composer

---

### 2. TemplateSelector
**Conversation template browser** with filtering and search.

```typescript
import { TemplateSelector } from './components/TemplateSelector/TemplateSelector';

<TemplateSelector
  isOpen={showTemplates}
  onClose={() => setShowTemplates(false)}
  onSelectTemplate={(template) => {
    console.log('Selected:', template);
  }}
  defaultCategory="code_review"
/>
```

**Features:** 8 categories, 4 difficulty levels, search, grid/list views, popular templates

---

### 3. MessageReactions
**Reaction and feedback system** for AI messages.

```typescript
import { MessageReactions } from './components/MessageReactions/MessageReactions';

<MessageReactions
  messageId="msg-123"
  reactions={reactions}
  onReact={(msgId, type) => toggleReaction(msgId, type)}
  onFeedback={(msgId, type, text) => saveFeedback(msgId, type, text)}
  compact={false}
/>
```

**Features:** 8 reaction types, feedback form, reaction counts, color coding

---

### 4. MessageComposer
**Enhanced message input** with formatting and auto-save.

```typescript
import { MessageComposer } from './components/MessageComposer/MessageComposer';

<MessageComposer
  conversationId="conv-123"
  onSendMessage={(message) => sendMessage(message)}
  onOpenTemplates={() => setShowTemplates(true)}
  showTemplateButton={true}
  maxLength={5000}
/>
```

**Features:** Formatting toolbar, keyboard shortcuts, auto-save, character counter

---

### 5. ConversationSummary
**AI-powered conversation summaries** with multiple formats.

```typescript
import { ConversationSummary } from './components/ConversationSummary/ConversationSummary';

<ConversationSummary
  messages={messages}
  conversationId="conv-123"
  onClose={() => setShowSummary(false)}
  autoGenerate={false}
/>
```

**Features:** Brief/detailed/bullet summaries, key points, action items, topics

---

## 🪝 Custom Hooks

### useTemplates
Hook for managing conversation templates with API integration.

```typescript
import { useTemplates } from './hooks/useTemplates';

const {
  templates,
  loading,
  error,
  fetchTemplates,
  fetchPopular,
  getTemplate,
  logTemplateUsage,
} = useTemplates();
```

**Features:** Filtering, pagination, stats, popular templates, usage logging

---

### useDraftAutosave
Hook for auto-saving message drafts with persistence.

```typescript
import { useDraftAutosave } from './hooks/useDraftAutosave';

const {
  draft,
  setDraft,
  clearDraft,
  hasDraft,
  lastSaved,
  isSaving,
} = useDraftAutosave({
  conversationId: 'conv-123',
  autosaveDelay: 2000,
});
```

**Features:** Auto-save, restoration, conversation-specific, 24h retention

---

## 🎯 Quick Start

### Basic Chat Interface
```typescript
import React, { useState } from 'react';
import { EnhancedChatUI } from './components/EnhancedChatUI/EnhancedChatUI';

function ChatPage() {
  const [messages, setMessages] = useState([]);

  return (
    <EnhancedChatUI
      conversationId="demo"
      messages={messages}
      onSendMessage={(msg) => {
        setMessages([...messages, {
          id: Date.now().toString(),
          role: 'user',
          content: msg,
          timestamp: new Date().toISOString(),
        }]);
      }}
      onReact={(msgId, type) => console.log('React:', type)}
      onFeedback={(msgId, type, text) => console.log('Feedback:', type)}
    />
  );
}
```

### Template-Only Integration
```typescript
import { TemplateSelector } from './components/TemplateSelector/TemplateSelector';

function TemplateDemo() {
  const [show, setShow] = useState(false);

  return (
    <>
      <button onClick={() => setShow(true)}>Choose Template</button>
      <TemplateSelector
        isOpen={show}
        onClose={() => setShow(false)}
        onSelectTemplate={(t) => console.log(t.title)}
      />
    </>
  );
}
```

### Composer-Only Integration
```typescript
import { MessageComposer } from './components/MessageComposer/MessageComposer';

function ComposerDemo() {
  return (
    <MessageComposer
      conversationId="demo"
      onSendMessage={(msg) => console.log('Send:', msg)}
      placeholder="Type your message..."
    />
  );
}
```

## 📋 Dependencies

### Required
```json
{
  "react": "^18.0.0",
  "react-dom": "^18.0.0"
}
```

### Dev Dependencies
```json
{
  "@types/react": "^18.0.0",
  "@types/react-dom": "^18.0.0",
  "typescript": "^5.0.0"
}
```

### Optional (for enhanced features)
```json
{
  "marked": "^9.0.0",
  "dompurify": "^3.0.0"
}
```

## 🎨 Styling

### Import Styles
```typescript
// Import all component styles
import './components/EnhancedChatUI/EnhancedChatUI.css';
import './components/TemplateSelector/TemplateSelector.css';
import './components/MessageReactions/MessageReactions.css';
import './components/MessageComposer/MessageComposer.css';
import './components/ConversationSummary/ConversationSummary.css';
```

### Or use individual imports
```typescript
// Import only what you need
import './components/TemplateSelector/TemplateSelector.css';
```

## 🔧 Configuration

### Environment Variables
```bash
# .env file
REACT_APP_API_URL=http://localhost:8000/api/v1
REACT_APP_AUTOSAVE_DELAY=2000
REACT_APP_MAX_MESSAGE_LENGTH=5000
```

### TypeScript Config
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "jsx": "react-jsx",
    "module": "ESNext",
    "moduleResolution": "node",
    "strict": true,
    "esModuleInterop": true
  }
}
```

## 📊 Component Sizes

| Component | TSX | CSS | Total |
|-----------|-----|-----|-------|
| TemplateSelector | 11KB | 9KB | 20KB |
| MessageReactions | 10KB | 8KB | 18KB |
| MessageComposer | 10KB | 6KB | 16KB |
| ConversationSummary | 11KB | 7KB | 18KB |
| EnhancedChatUI | 8KB | 8KB | 16KB |
| **Total** | **50KB** | **38KB** | **88KB** |

## 🎯 Browser Support

- ✅ Chrome/Edge 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Mobile browsers (iOS Safari, Chrome Mobile)

## 📝 Examples

See `/src/frontend/examples/` for:
- Complete integration examples
- Individual component demos
- Custom styling examples
- Advanced use cases

## 🙏 Contributing

When adding new components:
1. Follow TypeScript best practices
2. Include prop types and documentation
3. Add CSS with dark mode support
4. Write unit tests
5. Update this README

## 📚 Documentation

- **Feature Guide:** `/docs/frontend/ENHANCED_CHAT_UI_FEATURES.md`
- **API Docs:** `/docs/api/CONVERSATION_TEMPLATES.md`
- **Main README:** `/README.md`

---

**Version:** 1.0.0  
**Last Updated:** March 8, 2026  
**License:** MIT

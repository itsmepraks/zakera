# UI Enhancements: Markdown & Code Highlighting

## Overview

Zakera's chat UI now features professional markdown rendering and syntax highlighting, making conversations more readable and user-friendly, especially for technical content.

## Features

### ✅ Rich Markdown Support

- **Headings** (H1-H6)
- **Bold**, *Italic*, and `inline code`
- Code blocks with syntax highlighting
- Tables with responsive design
- Lists (ordered and unordered)
- Blockquotes with visual indicators
- Links with external indicators
- Math equations (KaTeX)

### ✅ Code Syntax Highlighting

**Supported Languages** (20+):
- JavaScript/TypeScript
- Python
- Java
- C/C++/C#
- Go
- Rust
- Ruby
- PHP
- Swift
- Kotlin
- HTML/CSS
- SQL
- Bash/Shell
- And more...

**Features**:
- Automatic language detection
- Line numbers
- Copy-to-clipboard button
- Language badges
- Dark/Light theme support
- Professional color schemes

### ✅ Formatting Toolbar

**Quick Actions**:
- 🗯 **Bold** (Ctrl+B)
- 🦝 *Italic* (Ctrl+I)
- 👨‍💻 `Code` (Ctrl+E)
- 📝 Code Block (Ctrl+Shift+C)
- 🔗 Link (Ctrl+K)
- 🅲 Heading (Ctrl+H)
- 📊 List (Ctrl+L)
- 🔢 Numbered List (Ctrl+Shift+L)
- ❝ Quote (Ctrl+Q)

## Usage Examples

### Basic Formatting

```markdown
# Main Heading

## Subheading

This is **bold** and this is *italic*.

Here's some `inline code`.
```

### Code Blocks

````markdown
```python
def hello_world():
    print("Hello, World!")
    return True
```
````

**Renders as**:
```python
def hello_world():
    print("Hello, World!")
    return True
```

With:
- Syntax highlighting
- Line numbers
- Copy button
- Language badge

### Tables

```markdown
| Feature | Status | Notes |
|---------|--------|-------|
| Markdown | ✅ | Full support |
| Syntax | ✅ | 20+ languages |
| Math | ✅ | KaTeX |
```

**Renders as**:

| Feature | Status | Notes |
|---------|--------|-------|
| Markdown | ✅ | Full support |
| Syntax | ✅ | 20+ languages |
| Math | ✅ | KaTeX |

### Math Equations

```markdown
Inline math: $E = mc^2$

Block math:
$$
\int_0^\infty e^{-x^2} dx = \frac{\sqrt{\pi}}{2}
$$
```

### Lists

```markdown
**Ordered**:
1. First item
2. Second item
3. Third item

**Unordered**:
- Item one
- Item two
  - Nested item
  - Another nested
```

### Blockquotes

```markdown
> This is a quote.
> 
> It can span multiple lines.
```

## Integration

### In Chat Messages

```tsx
import MessageRenderer from './components/MessageRenderer';

function ChatMessage({ message, theme }) {
  return (
    <MessageRenderer
      content={message.content}
      role={message.role}
      theme={theme}
    />
  );
}
```

### With Formatting Toolbar

```tsx
import { FormattingToolbar } from './components/FormattingToolbar';
import { useState } from 'react';

function MessageInput() {
  const [content, setContent] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  
  const handleFormat = (format: string, value?: string) => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selected = content.substring(start, end);
    
    let newContent = content;
    let newCursorPos = start;
    
    switch (format) {
      case 'wrap':
        // Wrap selected text with value (e.g., ** for bold)
        newContent = 
          content.substring(0, start) +
          value + selected + value +
          content.substring(end);
        newCursorPos = start + value.length + selected.length;
        break;
      
      case 'prefix':
        // Add prefix to line (e.g., ## for heading)
        const lineStart = content.lastIndexOf('\n', start - 1) + 1;
        newContent = 
          content.substring(0, lineStart) +
          value +
          content.substring(lineStart);
        newCursorPos = start + value.length;
        break;
      
      case 'block':
        // Wrap in block (e.g., code block)
        const [prefix, suffix] = value.split('|');
        newContent = 
          content.substring(0, start) +
          prefix + selected + suffix +
          content.substring(end);
        newCursorPos = start + prefix.length + selected.length;
        break;
      
      case 'link':
        // Insert link
        const url = prompt('Enter URL:');
        if (url) {
          const linkText = selected || 'link text';
          newContent = 
            content.substring(0, start) +
            `[${linkText}](${url})` +
            content.substring(end);
          newCursorPos = start + linkText.length + url.length + 4;
        }
        break;
    }
    
    setContent(newContent);
    
    // Restore cursor position
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(newCursorPos, newCursorPos);
    }, 0);
  };
  
  return (
    <div>
      <FormattingToolbar onFormat={handleFormat} />
      <textarea
        ref={textareaRef}
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="Type your message... (Markdown supported)"
      />
    </div>
  );
}
```

## Theme Support

### Light Theme

```tsx
<MessageRenderer
  content={content}
  role="assistant"
  theme="light"
/>
```

### Dark Theme

```tsx
<MessageRenderer
  content={content}
  role="assistant"
  theme="dark"
/>
```

### Custom Theme Variables

```css
:root {
  /* Light theme */
  --text-primary: #1a1a1a;
  --message-user-bg: #e3f2fd;
  --message-assistant-bg: #f5f5f5;
  --inline-code-bg: #f4f4f4;
  --inline-code-color: #e83e8c;
  --link-color: #2196f3;
}

.theme-dark {
  /* Dark theme */
  --text-primary: #e0e0e0;
  --message-user-bg: #1e3a5f;
  --message-assistant-bg: #2a2a2a;
  --inline-code-bg: #3a3a3a;
  --inline-code-color: #ff79c6;
  --link-color: #61afef;
}
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+B` | Bold |
| `Ctrl+I` | Italic |
| `Ctrl+E` | Inline code |
| `Ctrl+Shift+C` | Code block |
| `Ctrl+K` | Insert link |
| `Ctrl+H` | Heading |
| `Ctrl+L` | Bullet list |
| `Ctrl+Shift+L` | Numbered list |
| `Ctrl+Q` | Quote |

## Accessibility

### Features
- ✅ Keyboard navigation
- ✅ ARIA labels
- ✅ Focus indicators
- ✅ Screen reader support
- ✅ Semantic HTML
- ✅ High contrast support

### Example

```tsx
<button
  className="format-button"
  onClick={handleBold}
  aria-label="Bold text"
  title="Bold (Ctrl+B)"
>
  <span className="format-icon">🗯</span>
</button>
```

## Performance

### Optimizations

1. **React.memo**: Prevents unnecessary re-renders
```tsx
const CodeBlock = React.memo(({ ... }) => {
  // Component logic
});
```

2. **useCallback**: Memoizes callbacks
```tsx
const handleCopy = useCallback(async () => {
  await navigator.clipboard.writeText(code);
}, [code]);
```

3. **Lazy Loading**: Load syntax highlighter on demand
```tsx
const SyntaxHighlighter = lazy(() => 
  import('react-syntax-highlighter')
);
```

## Browser Support

| Browser | Version | Status |
|---------|---------|--------|
| Chrome | 90+ | ✅ Full |
| Firefox | 88+ | ✅ Full |
| Safari | 14+ | ✅ Full |
| Edge | 90+ | ✅ Full |
| Mobile Safari | 14+ | ✅ Full |
| Mobile Chrome | 90+ | ✅ Full |

## Dependencies

```json
{
  "react-markdown": "^9.0.1",
  "react-syntax-highlighter": "^15.5.0",
  "remark-gfm": "^4.0.0",
  "remark-math": "^6.0.0",
  "rehype-katex": "^7.0.0",
  "katex": "^0.16.9"
}
```

## Best Practices

### 1. Use Semantic Markdown

```markdown
✅ Good:
# Main Title
## Section
### Subsection

❌ Avoid:
**BIG TEXT**
*medium text*
```

### 2. Format Code Properly

```markdown
✅ Good:
```python
code here
```

❌ Avoid:
code without language
```

### 3. Use Tables for Structured Data

```markdown
✅ Good:
| Name | Value |
|------|-------|
| A    | 1     |

❌ Avoid:
Name: A, Value: 1
Name: B, Value: 2
```

## Troubleshooting

### Code Not Highlighting

**Issue**: Code block shows plain text

**Solution**: Ensure language is specified
```markdown
```python  <-- Language specified
code here
```
```

### Math Not Rendering

**Issue**: Math equations show as plain text

**Solution**: Check KaTeX CSS is imported
```tsx
import 'katex/dist/katex.min.css';
```

### Toolbar Not Working

**Issue**: Formatting buttons don't work

**Solution**: Ensure textarea ref is properly connected
```tsx
const textareaRef = useRef<HTMLTextAreaElement>(null);
<textarea ref={textareaRef} />
```

## Future Enhancements

- [ ] Mermaid diagram support
- [ ] Custom emoji picker
- [ ] Drag-and-drop image upload
- [ ] Voice-to-text formatting
- [ ] Collaborative editing
- [ ] Version history
- [ ] Export to PDF/HTML
- [ ] Template snippets

---

**Version**: 1.0.0  
**Last Updated**: February 2026  
**Status**: Production Ready ✅

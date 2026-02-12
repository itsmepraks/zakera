# Responsive Design Guide

Comprehensive guide to Zakera's mobile-first responsive design system.

## Table of Contents

- [Overview](#overview)
- [Design System](#design-system)
- [Breakpoints](#breakpoints)
- [Components](#components)
- [Touch Optimizations](#touch-optimizations)
- [Accessibility](#accessibility)
- [Performance](#performance)
- [Best Practices](#best-practices)

## Overview

Zakera implements a mobile-first responsive design approach with:

- ✅ Mobile-first CSS architecture
- ✅ Touch-friendly UI components (44px+ touch targets)
- ✅ Responsive navigation with mobile menu
- ✅ Swipe gestures and touch interactions
- ✅ Accessibility features (ARIA, keyboard navigation)
- ✅ Dark mode support
- ✅ Performance optimizations
- ✅ iOS and Android compatibility

## Design System

### Design Tokens

All design values are defined as CSS custom properties for consistency:

```css
:root {
  /* Breakpoints */
  --breakpoint-sm: 640px;
  --breakpoint-md: 768px;
  --breakpoint-lg: 1024px;
  --breakpoint-xl: 1280px;

  /* Spacing */
  --spacing-xs: 0.25rem;  /* 4px */
  --spacing-sm: 0.5rem;   /* 8px */
  --spacing-md: 1rem;     /* 16px */
  --spacing-lg: 1.5rem;   /* 24px */
  --spacing-xl: 2rem;     /* 32px */

  /* Touch targets */
  --touch-target-min: 44px;
  --touch-target-comfortable: 56px;

  /* Font sizes */
  --text-sm: 0.875rem;
  --text-base: 1rem;
  --text-lg: 1.125rem;
  --text-xl: 1.25rem;
}
```

### Using Design Tokens

```css
.my-component {
  padding: var(--spacing-md);
  font-size: var(--text-base);
  min-height: var(--touch-target-min);
}
```

## Breakpoints

### Breakpoint System

| Size | Min Width | Target Devices |
|------|-----------|----------------|
| xs   | 320px     | Small phones   |
| sm   | 640px     | Phones         |
| md   | 768px     | Tablets        |
| lg   | 1024px    | Small desktops |
| xl   | 1280px    | Large desktops |
| 2xl  | 1536px    | Extra large    |

### Media Queries

Use mobile-first media queries:

```css
/* Mobile first (default) */
.component {
  padding: 1rem;
}

/* Tablet and up */
@media (min-width: 768px) {
  .component {
    padding: 2rem;
  }
}

/* Desktop and up */
@media (min-width: 1024px) {
  .component {
    padding: 3rem;
  }
}
```

### Responsive Utilities

```html
<!-- Hide on mobile -->
<div class="hidden-mobile">Desktop only content</div>

<!-- Hide on desktop -->
<div class="hidden-desktop">Mobile only content</div>
```

## Components

### Mobile Navigation

Responsive navigation that transforms into a hamburger menu on mobile:

```typescript
import { MobileNav } from '@/components/MobileNav';

const menuItems = [
  { label: 'Home', href: '/' },
  { label: 'Chat', href: '/chat' },
  { label: 'Settings', href: '/settings' },
];

<MobileNav
  brandName="Zakera"
  menuItems={menuItems}
/>
```

**Features:**
- Animated hamburger to X transition
- Smooth slide-in animation
- Body scroll lock when open
- Touch-friendly menu items (56px height)
- Automatic desktop layout on larger screens

### Touch-Optimized Chat

Chat interface optimized for touch interactions:

```typescript
import { TouchOptimizedChat } from '@/components/TouchOptimizedChat';

const handleSend = async (message: string) => {
  await sendMessageToAPI(message);
};

<TouchOptimizedChat
  messages={messages}
  onSendMessage={handleSend}
  isLoading={isLoading}
  placeholder="Type a message..."
/>
```

**Features:**
- Pull-to-refresh gesture
- Auto-expanding textarea
- Touch-friendly send button (44px)
- Smooth scroll to new messages
- Empty state with helpful prompts
- Loading indicators

### Responsive Grid

Flexible grid system that adapts to screen size:

```html
<!-- 1 column on mobile, 2 on tablet, 3 on desktop -->
<div class="grid grid-sm-2 grid-lg-3">
  <div>Item 1</div>
  <div>Item 2</div>
  <div>Item 3</div>
</div>
```

## Touch Optimizations

### Touch Target Sizes

**Minimum touch target: 44x44px** (Apple/Google guidelines)
**Comfortable touch target: 56px** (Material Design)

```css
button {
  min-height: var(--touch-target-min);
  min-width: var(--touch-target-min);
  /* Even better for primary actions */
  min-height: var(--touch-target-comfortable);
}
```

### Touch Interactions

#### 1. Tap Feedback

```css
button:active {
  transform: scale(0.98);
  opacity: 0.8;
}
```

#### 2. Prevent Unwanted Behavior

```css
/* Prevent tap highlight on iOS */
* {
  -webkit-tap-highlight-color: transparent;
}

/* Prevent text selection on double-tap */
.no-select {
  -webkit-user-select: none;
  user-select: none;
}

/* Disable touch callout (iOS context menu) */
.no-callout {
  -webkit-touch-callout: none;
}
```

#### 3. Smooth Scrolling

```css
/* iOS momentum scrolling */
.scrollable {
  -webkit-overflow-scrolling: touch;
  overflow-y: auto;
}
```

### Swipe Gestures

Implement swipe gestures using Touch Events:

```typescript
const [touchStart, setTouchStart] = useState(0);
const [touchEnd, setTouchEnd] = useState(0);

const handleTouchStart = (e: TouchEvent) => {
  setTouchStart(e.touches[0].clientX);
};

const handleTouchEnd = (e: TouchEvent) => {
  setTouchEnd(e.changedTouches[0].clientX);
  
  const swipeDistance = touchStart - touchEnd;
  const minSwipeDistance = 50;
  
  if (Math.abs(swipeDistance) > minSwipeDistance) {
    if (swipeDistance > 0) {
      // Swiped left
      handleSwipeLeft();
    } else {
      // Swiped right
      handleSwipeRight();
    }
  }
};
```

### Pull to Refresh

Implemented in TouchOptimizedChat component:

```typescript
const handleTouchStart = (e: TouchEvent) => {
  if (window.scrollY === 0) {
    touchStartY.current = e.touches[0].clientY;
    setIsPulling(true);
  }
};

const handleTouchMove = (e: TouchEvent) => {
  if (!isPulling) return;
  
  const distance = e.touches[0].clientY - touchStartY.current;
  if (distance > 0 && distance < 100) {
    setPullDistance(distance);
  }
};

const handleTouchEnd = () => {
  if (pullDistance > 70) {
    // Trigger refresh
    refreshData();
  }
  setIsPulling(false);
};
```

## Accessibility

### ARIA Labels

Provide descriptive labels for screen readers:

```html
<button aria-label="Send message">
  <SendIcon />
</button>

<nav aria-label="Main navigation">
  <!-- Navigation items -->
</nav>

<div role="article" aria-label="Assistant message">
  <!-- Message content -->
</div>
```

### Keyboard Navigation

Ensure all interactive elements are keyboard accessible:

```css
/* Clear focus indicator */
*:focus-visible {
  outline: 2px solid #3b82f6;
  outline-offset: 2px;
}

/* Remove outline for mouse users */
*:focus:not(:focus-visible) {
  outline: none;
}
```

```typescript
// Handle Enter key
const handleKeyDown = (e: React.KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSubmit();
  }
};
```

### Skip Links

Allow keyboard users to skip to main content:

```html
<a href="#main-content" class="skip-to-main">
  Skip to main content
</a>

<main id="main-content">
  <!-- Main content -->
</main>
```

```css
.skip-to-main {
  position: absolute;
  left: -9999px;
}

.skip-to-main:focus {
  left: 0;
  top: 0;
  z-index: 999;
}
```

### Screen Reader Only Content

```html
<span class="sr-only">Loading messages</span>
```

```css
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}
```

### Live Regions

Announce dynamic content to screen readers:

```html
<div role="status" aria-live="polite">
  Loading messages...
</div>

<div role="alert" aria-live="assertive">
  Error: Failed to send message
</div>
```

## Performance

### Viewport Meta Tag

Essential for proper mobile rendering:

```html
<meta 
  name="viewport" 
  content="width=device-width, initial-scale=1, maximum-scale=5"
>
```

### Dynamic Viewport Height

Handle mobile browser chrome correctly:

```css
.full-height {
  height: 100vh;
  height: 100dvh; /* Dynamic viewport height */
}
```

### GPU Acceleration

Use transforms for smoother animations:

```css
/* Instead of: */
.bad {
  left: 100px; /* Triggers layout */
}

/* Use: */
.good {
  transform: translateX(100px); /* GPU accelerated */
  will-change: transform;
}
```

### Reduce Motion

Respect user preferences:

```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

### Image Optimization

```html
<!-- Responsive images -->
<img 
  src="image-400.jpg"
  srcset="
    image-400.jpg 400w,
    image-800.jpg 800w,
    image-1200.jpg 1200w
  "
  sizes="(max-width: 640px) 100vw, 50vw"
  alt="Description"
  loading="lazy"
>
```

## Best Practices

### 1. Test on Real Devices

- Use browser DevTools device emulation
- Test on actual iOS and Android devices
- Test with different screen sizes
- Test in portrait and landscape

### 2. Touch Target Spacing

```css
/* Ensure adequate spacing between touch targets */
.button-group button {
  margin: var(--spacing-sm);
  /* At least 8px between buttons */
}
```

### 3. Readable Text

```css
/* Minimum 16px font size to prevent zoom on iOS */
input, textarea, select {
  font-size: 16px;
}

/* Readable line length */
.text-content {
  max-width: 65ch; /* ~65 characters */
}
```

### 4. Form Inputs

```html
<!-- Use appropriate input types for mobile keyboards -->
<input type="email" inputmode="email">
<input type="tel" inputmode="tel">
<input type="number" inputmode="numeric">
<input type="search" inputmode="search">
```

### 5. Prevent Zoom on Focus

```css
/* Option 1: Use 16px+ font size */
input {
  font-size: 16px;
}

/* Option 2: Disable zoom (not recommended) */
<meta 
  name="viewport" 
  content="width=device-width, initial-scale=1, maximum-scale=1"
>
```

### 6. Safe Areas (Notch Support)

```css
/* Respect notches and home indicators */
.container {
  padding-left: max(1rem, env(safe-area-inset-left));
  padding-right: max(1rem, env(safe-area-inset-right));
  padding-bottom: max(1rem, env(safe-area-inset-bottom));
}
```

### 7. Dark Mode

```css
@media (prefers-color-scheme: dark) {
  :root {
    --bg-primary: #1f2937;
    --text-primary: #f9fafb;
  }
}
```

## Browser Compatibility

### Supported Browsers

- iOS Safari 13+
- Chrome (Android) 80+
- Samsung Internet 12+
- Firefox (Android) 80+

### Feature Detection

```typescript
// Check for touch support
const hasTouch = 'ontouchstart' in window;

// Check for CSS feature
const supportsDvh = CSS.supports('height', '100dvh');

// Progressive enhancement
if (hasTouch) {
  enableTouchGestures();
}
```

## Testing Checklist

- [ ] Test on iPhone (Safari)
- [ ] Test on Android (Chrome)
- [ ] Test with screen reader (VoiceOver/TalkBack)
- [ ] Test keyboard navigation
- [ ] Test in portrait and landscape
- [ ] Test with slow network
- [ ] Test with reduced motion enabled
- [ ] Test touch interactions
- [ ] Test form inputs
- [ ] Test at different zoom levels
- [ ] Verify touch target sizes
- [ ] Check color contrast ratios

## Resources

### Guidelines
- [Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/)
- [Material Design](https://material.io/design)
- [WCAG 2.1 Accessibility Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)

### Tools
- [Chrome DevTools Device Mode](https://developer.chrome.com/docs/devtools/device-mode/)
- [Lighthouse](https://developers.google.com/web/tools/lighthouse)
- [axe DevTools](https://www.deque.com/axe/devtools/)

## Support

For responsive design issues:
- Check browser console for errors
- Verify viewport meta tag
- Test on multiple devices
- File an issue: https://github.com/itsmepraks/zakera/issues

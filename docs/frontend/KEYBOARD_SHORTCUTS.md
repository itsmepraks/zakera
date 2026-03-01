# Keyboard Shortcuts Reference

Complete reference of keyboard shortcuts available in Zakera's conversation management UI.

## Global Shortcuts

### Navigation

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Cmd/Ctrl + K` | **Quick Actions** | Open command palette |
| `Cmd/Ctrl + N` | **New Conversation** | Create new conversation |
| `Cmd/Ctrl + F` | **Search** | Focus search bar |
| `Cmd/Ctrl + B` | **Toggle Branches** | Show/hide branch tree |
| `Cmd/Ctrl + ,` | **Settings** | Open settings |
| `Cmd/Ctrl + /` | **Shortcuts Help** | Show this reference |

### Selection

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Cmd/Ctrl + A` | **Select All** | Select all conversations |
| `Cmd/Ctrl + D` | **Deselect All** | Clear selection |
| `Shift + Click` | **Range Select** | Select range of items |
| `Cmd/Ctrl + Click` | **Multi-Select** | Toggle individual items |

### Actions

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Cmd/Ctrl + E` | **Export** | Export conversation |
| `Cmd/Ctrl + P` | **Pin** | Pin/unpin conversation |
| `Cmd/Ctrl + S` | **Star** | Star/unstar conversation |
| `Delete` | **Delete** | Delete selected (with confirmation) |
| `Backspace` | **Archive** | Archive selected |

### View

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Cmd/Ctrl + 1` | **List View** | Switch to list view |
| `Cmd/Ctrl + 2` | **Grid View** | Switch to grid view |
| `Cmd/Ctrl + 3` | **Timeline View** | Switch to timeline view |
| `Cmd/Ctrl + T` | **Toggle Theme** | Switch light/dark mode |

## Dialog Shortcuts

### Universal

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Escape` | **Close** | Close dialog/modal |
| `Enter` | **Confirm** | Confirm/submit |
| `Tab` | **Next Field** | Move to next input |
| `Shift + Tab` | **Previous Field** | Move to previous input |

## List Navigation

### Movement

| Shortcut | Action | Description |
|----------|--------|-------------|
| `↑` | **Previous** | Move to previous item |
| `↓` | **Next** | Move to next item |
| `Home` | **First** | Jump to first item |
| `End` | **Last** | Jump to last item |
| `PageUp` | **Page Up** | Scroll up one page |
| `PageDown` | **Page Down** | Scroll down one page |

### Actions

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Enter` | **Open** | Open selected conversation |
| `Space` | **Preview** | Preview selected conversation |
| `Shift + Enter` | **Open in New Tab** | Open in new tab (if supported) |

## Quick Actions Menu

### Navigation

| Shortcut | Action | Description |
|----------|--------|-------------|
| `↑` | **Previous Action** | Highlight previous |
| `↓` | **Next Action** | Highlight next |
| `Enter` | **Execute** | Run highlighted action |
| `Escape` | **Close Menu** | Close without executing |

### Typing

Just start typing to search actions. The menu filters in real-time.

## Branch Management

### Navigation

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Cmd/Ctrl + ←` | **Parent Branch** | Navigate to parent |
| `Cmd/Ctrl + →` | **Child Branch** | Navigate to first child |
| `Cmd/Ctrl + ↑` | **Previous Sibling** | Previous branch at same level |
| `Cmd/Ctrl + ↓` | **Next Sibling** | Next branch at same level |

### Operations

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Cmd/Ctrl + Shift + N` | **New Branch** | Create branch from current |
| `Cmd/Ctrl + Shift + M` | **Merge Branch** | Merge selected branch |
| `F2` | **Rename Branch** | Rename selected branch |

## Timeline View

### Navigation

| Shortcut | Action | Description |
|----------|--------|-------------|
| `←` | **Earlier** | Move timeline back |
| `→` | **Later** | Move timeline forward |
| `Shift + ←` | **Jump Back** | Jump back 10 messages |
| `Shift + →` | **Jump Forward** | Jump forward 10 messages |

### View

| Shortcut | Action | Description |
|----------|--------|-------------|
| `+` / `=` | **Zoom In** | Increase timeline density |
| `-` | **Zoom Out** | Decrease timeline density |
| `0` | **Reset Zoom** | Reset to default zoom |

## Search & Filter

### Search Bar

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Cmd/Ctrl + F` | **Focus Search** | Focus search input |
| `Escape` | **Clear Search** | Clear search and exit |
| `Enter` | **Execute Search** | Run search |
| `↓` | **Suggestions** | Move to suggestions |

### Filters

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Cmd/Ctrl + Shift + F` | **Advanced Filters** | Open filter panel |
| `Cmd/Ctrl + Shift + C` | **Clear Filters** | Reset all filters |
| `Cmd/Ctrl + Shift + S` | **Save Filter** | Save current filter as preset |

## Bulk Actions

### Selection

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Cmd/Ctrl + A` | **Select All** | Select all visible |
| `Cmd/Ctrl + I` | **Invert Selection** | Invert current selection |
| `Escape` | **Clear Selection** | Deselect all |

### Actions

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Cmd/Ctrl + Shift + D` | **Bulk Delete** | Delete selected |
| `Cmd/Ctrl + Shift + A` | **Bulk Archive** | Archive selected |
| `Cmd/Ctrl + Shift + E` | **Bulk Export** | Export selected |
| `Cmd/Ctrl + Shift + T` | **Bulk Tag** | Add tags to selected |

## Accessibility

### Screen Readers

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Tab` | **Next Element** | Move to next interactive element |
| `Shift + Tab` | **Previous Element** | Move to previous element |
| `Space` | **Activate** | Activate focused element |
| `Enter` | **Activate** | Activate focused element |

### Focus Management

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Cmd/Ctrl + L` | **Focus List** | Move focus to conversation list |
| `Cmd/Ctrl + M` | **Focus Messages** | Move focus to message area |
| `Cmd/Ctrl + [` | **Focus Sidebar** | Move focus to sidebar |

## Mobile (Touch Gestures)

While not keyboard shortcuts, here are the touch gestures:

| Gesture | Action | Description |
|---------|--------|-------------|
| **Swipe Left** | Delete | Swipe conversation left to delete |
| **Swipe Right** | Archive | Swipe conversation right to archive |
| **Long Press** | Multi-Select | Long press to enter selection mode |
| **Pull Down** | Refresh | Pull down to refresh list |
| **Pinch** | Zoom | Pinch timeline to zoom in/out |

## Customization

Shortcuts can be customized in Settings → Keyboard Shortcuts.

### Custom Shortcut Format

```tsx
{
  key: 'n',           // Key to press
  metaKey: true,      // Cmd (Mac) / Ctrl (Win/Linux)
  shiftKey: false,    // Shift modifier
  altKey: false,      // Alt/Option modifier
  description: 'Create new conversation',
  handler: () => createConversation(),
}
```

## Platform Differences

### macOS
- `Cmd` is used instead of `Ctrl`
- `Option` is `Alt`
- Additional shortcuts using `Cmd + Option`

### Windows/Linux
- `Ctrl` is primary modifier
- `Alt` is secondary modifier
- Some shortcuts differ (e.g., `Ctrl + Y` for redo)

## Tips

### Learning Shortcuts

1. **Start with basics**: Learn `Cmd+K` first
2. **Use tooltips**: Hover over buttons to see shortcuts
3. **Practice daily**: Use 1-2 new shortcuts each day
4. **Print reference**: Keep this page handy
5. **Customize**: Adjust shortcuts to your workflow

### Power User Tips

1. **Cmd+K is your friend**: Access any action quickly
2. **Combine with selection**: Select multiple, then action
3. **Learn navigation**: `↑↓←→` keys are faster than mouse
4. **Use labels**: Most buttons show shortcut hints
5. **Sequential actions**: Chain actions with shortcuts

## Conflicts

Some shortcuts may conflict with browser/OS shortcuts:

- `Cmd/Ctrl + F`: Browser find vs. App search
- `Cmd/Ctrl + T`: New tab vs. Toggle theme
- `Cmd/Ctrl + N`: New window vs. New conversation

**Solution**: App shortcuts take precedence when focused. Use browser shortcuts when in address bar.

## Disabling Shortcuts

To temporarily disable all shortcuts:

1. Press `Cmd/Ctrl + Shift + K`
2. Or go to Settings → Keyboard → Disable Shortcuts

## Feedback

Suggestions for new shortcuts? Open an issue or submit a PR!

---

**Quick Reference Card**: [Download PDF](./keyboard-shortcuts.pdf)  
**Video Tutorial**: [Watch on YouTube](https://youtube.com/...)

---

**Version**: 1.0.0  
**Last Updated**: February 2026  
**Platforms**: Web, Desktop (Electron)

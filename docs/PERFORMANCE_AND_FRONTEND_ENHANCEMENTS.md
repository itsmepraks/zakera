# Performance Testing & Frontend Enhancements

Comprehensive guide to the new performance testing suite and frontend feature enhancements.

## 📊 Performance Testing Suite

### Overview

We've added a complete performance testing suite using Locust that provides comprehensive load testing capabilities for the Zakera AI Chat Agent.

### 🎯 Features

- **Multiple Test Scenarios**: Normal load, stress, spike, and endurance testing
- **REST API Testing**: All endpoints including chat, conversations, search, and tools
- **WebSocket Testing**: Real-time connection testing
- **Streaming Response Testing**: SSE/streaming chat validation
- **Model Provider Testing**: Multi-provider performance analysis
- **Comprehensive Reporting**: HTML, JSON, and Prometheus metrics
- **CI/CD Integration**: GitHub Actions support

### 📁 File Structure

```
tests/performance/
├── locustfile.py           # Main test suite
├── reporters.py            # HTML/JSON/Prometheus reporters
├── requirements.txt        # Performance test dependencies
├── run_tests.sh           # Automated test runner
├── README.md              # Comprehensive documentation
└── config/
    ├── normal_load.py     # Baseline testing (50 users, 10min)
    ├── stress_test.py     # Heavy load (500 users, 15min)
    ├── spike_test.py      # Traffic spikes (1000 users)
    └── endurance_test.py  # Long-running (100 users, 2hrs)
```

### 🚀 Quick Start

#### Installation

```bash
# Install dependencies
pip install -r tests/performance/requirements.txt

# Or use the setup command
make perf-test-setup
```

#### Running Tests

**Interactive Mode (Web UI)**:
```bash
locust -f tests/performance/locustfile.py --host http://localhost:8000
# Open http://localhost:8089
```

**Headless Mode (CI/CD)**:
```bash
# Normal load test
./tests/performance/run_tests.sh normal

# Stress test
./tests/performance/run_tests.sh stress

# Spike test
./tests/performance/run_tests.sh spike

# All tests
./tests/performance/run_tests.sh all
```

**With Configuration Files**:
```bash
locust -f tests/performance/locustfile.py \
       --config tests/performance/config/normal_load.py
```

### 📊 Test Scenarios

#### 1. Normal Load Test
**Purpose**: Establish performance baseline

```python
Users: 50
Spawn Rate: 5 users/second
Duration: 10 minutes
Wait Time: 2-5 seconds

SLA Targets:
- Avg Response Time: < 1000ms
- Max Response Time: < 5000ms
- Failure Rate: < 1%
- Throughput: > 10 req/s
```

#### 2. Stress Test
**Purpose**: Find system breaking points

```python
Users: 500 (3 stages: 100 → 300 → 500)
Spawn Rate: 25 users/second
Duration: 15 minutes
Wait Time: 0.5-1 second

Expected:
- System remains responsive
- Graceful degradation
- Failure rate < 5%
```

#### 3. Spike Test
**Purpose**: Validate auto-scaling

```python
Users: 1000 (sudden spike)
Spawn Rate: 100 users/second
Pattern: Baseline → SPIKE → Sustain → Drop
Duration: 10 minutes

Monitors:
- Auto-scaling behavior
- Error handling
- Recovery time
```

#### 4. Endurance Test
**Purpose**: Identify memory leaks

```python
Users: 100
Duration: 2 hours
Monitors:
- Memory growth
- Connection pool health
- Performance degradation
```

### 📈 Reporting

#### HTML Report
```bash
# Generated automatically in results/ directory
open results/normal_load_report.html
```

Features:
- ✅ Key metrics dashboard
- 📊 Response time charts
- 📈 Requests over time graphs
- 📋 Endpoint statistics table
- ✓ SLA validation results

#### JSON Report (CI/CD)
```bash
cat results/normal_load_report.json
```

Use in CI/CD pipelines:
```yaml
- name: Validate SLA
  run: |
    python tests/performance/validate_sla.py results/report.json
```

#### Prometheus Metrics
```bash
cat results/normal_load_metrics.prom
```

Export to Prometheus for monitoring:
```bash
curl -X POST \
  http://prometheus:9091/metrics/job/perf_test \
  --data-binary @results/metrics.prom
```

### 🎯 Task Distribution

The test suite simulates realistic user behavior:

| Task Set | Weight | Tasks |
|----------|--------|-------|
| API Endpoints | 50% | Chat, conversations, search, tools |
| Streaming Chat | 15% | SSE/streaming responses |
| WebSocket | 15% | Real-time connections |
| Model Providers | 20% | Multi-provider testing |

Individual task weights:
- **Send chat message** (weight: 5) - Most common
- **Get conversations** (weight: 3)
- **Get history** (weight: 2)
- **Search conversations** (weight: 2)
- **Execute tool** (weight: 1)
- **Export conversation** (weight: 1)
- **Health check** (weight: 1)

### 🔍 Monitoring During Tests

**Real-time Metrics**:
- Locust Web UI: http://localhost:8089
- API Metrics: http://localhost:8000/api/v1/monitoring/metrics
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001

**Key Metrics**:
- Response time (p50, p95, p99)
- Error rate by endpoint
- Throughput (requests/second)
- Model provider latency
- System resource usage

### 🛠️ Makefile Targets

```bash
make perf-test-setup      # Install dependencies
make perf-test-all        # Run all tests
make perf-test-normal     # Normal load
make perf-test-stress     # Stress test
make perf-test-spike      # Spike test
make perf-test-endurance  # Endurance test
make perf-test-report     # Generate reports
make perf-test-clean      # Clean results
```

### 📚 Best Practices

1. **Environment**: Use dedicated test environment matching production
2. **Data**: Clean test data between runs
3. **Warm-up**: Allow system warm-up before measuring
4. **Isolation**: Test one variable at a time
5. **Baselines**: Establish performance baselines
6. **Monitoring**: Watch system resources during tests
7. **Documentation**: Document test scenarios and results

---

## 🎨 Frontend Enhancements

### Overview

We've added several advanced features to the React TypeScript frontend to improve user experience and functionality.

### ✨ New Features

1. **Dark Mode Support** with theme persistence
2. **Conversation Search** with text highlighting
3. **Typing Indicator** for real-time feedback
4. **Message Export UI** with format preview (coming soon)

### 📁 File Structure

```
src/frontend/src/
├── contexts/
│   └── ThemeContext.tsx           # Theme management
├── components/
│   ├── ThemeToggle.tsx           # Theme toggle button
│   ├── ThemeToggle.css           # Theme toggle styles
│   ├── ConversationSearch.tsx    # Search component
│   ├── ConversationSearch.css    # Search styles
│   ├── TypingIndicator.tsx       # Typing animation
│   └── TypingIndicator.css       # Typing styles
└── styles/
    └── theme.css                 # Global theme variables
```

### 🌓 Dark Mode Support

#### Features
- ✅ Light and dark themes
- ✅ System preference detection
- ✅ localStorage persistence
- ✅ Smooth transitions
- ✅ CSS custom properties
- ✅ Theme-aware components

#### Usage

**Setup Theme Provider**:
```typescript
import { ThemeProvider } from './contexts/ThemeContext';

function App() {
  return (
    <ThemeProvider>
      <YourApp />
    </ThemeProvider>
  );
}
```

**Use Theme in Components**:
```typescript
import { useTheme, useThemeColors } from './contexts/ThemeContext';

function MyComponent() {
  const { theme, toggleTheme } = useTheme();
  const colors = useThemeColors();
  
  return (
    <div style={{ background: colors.background }}>
      <button onClick={toggleTheme}>
        Toggle Theme
      </button>
    </div>
  );
}
```

**Theme Toggle Button**:
```typescript
import ThemeToggle from './components/ThemeToggle';

function Header() {
  return (
    <header>
      <ThemeToggle showLabel={true} />
    </header>
  );
}
```

#### Theme Colors

**Light Theme**:
```css
--color-background: #ffffff
--color-surface: #f5f5f5
--color-primary: #2563eb
--color-text: #1a1a1a
--color-border: #e5e5e5
```

**Dark Theme**:
```css
--color-background: #1a1a1a
--color-surface: #2d2d2d
--color-primary: #3b82f6
--color-text: #e5e5e5
--color-border: #404040
```

### 🔍 Conversation Search

#### Features
- ✅ Real-time search with debouncing
- ✅ Text highlighting
- ✅ Keyboard navigation (↑↓, Enter, Esc)
- ✅ Results ranking by relevance
- ✅ Timestamp formatting
- ✅ Empty and loading states
- ✅ Mobile responsive

#### Usage

```typescript
import ConversationSearch from './components/ConversationSearch';

function ChatInterface() {
  const [showSearch, setShowSearch] = useState(false);
  
  const handleResultClick = (result) => {
    // Navigate to conversation/message
    console.log('Selected:', result);
  };
  
  return (
    <>
      <button onClick={() => setShowSearch(true)}>
        Search (⌘K)
      </button>
      
      {showSearch && (
        <ConversationSearch
          conversations={conversations}
          onResultClick={handleResultClick}
          onClose={() => setShowSearch(false)}
          placeholder="Search conversations..."
        />
      )}
    </>
  );
}
```

#### Keyboard Shortcuts
- **↑↓** - Navigate results
- **Enter** - Select result
- **Esc** - Close search
- **⌘K / Ctrl+K** - Open search (implement in parent)

#### Search Features
- Searches all message content
- Ranks by relevance (keyword frequency)
- Secondary sort by timestamp
- Limits to 50 results
- Highlights matching text
- Shows message role (user/AI)
- Displays relative time

### 💬 Typing Indicator

#### Features
- ✅ Animated dots
- ✅ Customizable message
- ✅ Smooth animations
- ✅ Theme-aware
- ✅ Lightweight

#### Usage

```typescript
import TypingIndicator from './components/TypingIndicator';

function ChatMessages() {
  const [isAITyping, setIsAITyping] = useState(false);
  
  return (
    <div className="messages">
      {messages.map(msg => <Message key={msg.id} {...msg} />)}
      
      {isAITyping && (
        <TypingIndicator message="AI is thinking..." />
      )}
    </div>
  );
}
```

**With Streaming**:
```typescript
const handleStreamingMessage = async () => {
  setIsAITyping(true);
  
  const stream = await sendMessage(message);
  
  for await (const chunk of stream) {
    setIsAITyping(false); // Hide when first chunk arrives
    // Display chunk
  }
};
```

### 🎨 Styling Best Practices

#### Use CSS Custom Properties

```css
.my-component {
  background: var(--color-surface);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  box-shadow: var(--shadow-md);
}
```

#### Utility Classes

```html
<div className="bg-surface rounded shadow text-muted">
  Content
</div>
```

#### Animations

```html
<div className="animate-fade-in">
  Fades in on mount
</div>

<div className="animate-slide-up">
  Slides up on mount
</div>
```

### 📱 Responsive Design

All components are fully responsive:

```css
/* Mobile: 0-640px */
@media (max-width: 640px) {
  html { font-size: 14px; }
}

/* Tablet: 641-768px */
@media (max-width: 768px) {
  /* Adjusted spacing */
}

/* Desktop: 769px+ */
/* Default styles */
```

### ♿ Accessibility

All components follow accessibility best practices:

- ✅ ARIA labels
- ✅ Keyboard navigation
- ✅ Focus states
- ✅ Screen reader support
- ✅ Color contrast (WCAG 2.1 AA)

### 🚀 Integration Guide

#### 1. Install Dependencies

```bash
cd src/frontend
npm install lodash @types/lodash
```

#### 2. Import Theme Styles

```typescript
// src/frontend/src/index.tsx
import './styles/theme.css';
```

#### 3. Wrap App with ThemeProvider

```typescript
// src/frontend/src/App.tsx
import { ThemeProvider } from './contexts/ThemeContext';

function App() {
  return (
    <ThemeProvider>
      {/* Your app */}
    </ThemeProvider>
  );
}
```

#### 4. Add Theme Toggle to Header

```typescript
import ThemeToggle from './components/ThemeToggle';

function Header() {
  return (
    <header className="app-header">
      <h1>Zakera</h1>
      <ThemeToggle showLabel={true} />
    </header>
  );
}
```

#### 5. Add Search to Chat Interface

```typescript
import ConversationSearch from './components/ConversationSearch';

// Implement search modal/panel
// Add keyboard shortcut (⌘K)
```

#### 6. Add Typing Indicator to Chat

```typescript
import TypingIndicator from './components/TypingIndicator';

// Show during streaming responses
```

### 📊 Performance Considerations

**Theme Switching**:
- CSS custom properties update instantly
- No component re-renders needed
- Smooth 0.3s transitions

**Search**:
- Debounced (300ms) to reduce CPU usage
- Limits results to 50
- Efficient regex for highlighting

**Typing Indicator**:
- Pure CSS animations
- Lightweight component
- No JavaScript animations

### 🎯 Future Enhancements

**Coming Soon**:
- [ ] Message export UI with format preview
- [ ] Voice input/output integration
- [ ] Multi-language support
- [ ] Advanced search filters
- [ ] Search history
- [ ] Keyboard shortcut customization
- [ ] Theme customization

---

## 🧪 Testing

### Performance Tests

```bash
# Run performance test suite
./tests/performance/run_tests.sh all

# Check SLA compliance
python tests/performance/validate_sla.py results/report.json
```

### Frontend Tests

```bash
# Unit tests
npm test

# E2E tests
npm run test:e2e

# Theme switching tests
npm test -- --testPathPattern=Theme

# Search component tests
npm test -- --testPathPattern=Search
```

---

## 📚 Documentation

- [Performance Testing README](../tests/performance/README.md)
- [Frontend Architecture](./ARCHITECTURE.md)
- [Theme System Documentation](./THEME_SYSTEM.md)
- [Component Library](./COMPONENTS.md)

---

## 🤝 Contributing

### Performance Tests
1. Add new test scenarios in `tests/performance/config/`
2. Update `locustfile.py` for new endpoints
3. Add reporters for new metrics
4. Update documentation

### Frontend Features
1. Follow existing component patterns
2. Use theme CSS custom properties
3. Ensure accessibility
4. Add responsive styles
5. Write tests
6. Update documentation

---

## 📝 Changelog

**February 2026**:
- ✅ Added comprehensive Locust performance testing suite
- ✅ Implemented dark mode with system preference detection
- ✅ Created conversation search with text highlighting
- ✅ Added typing indicator component
- ✅ Comprehensive documentation and examples

---

**Version**: 1.0.0  
**Status**: Production Ready  
**Last Updated**: February 27, 2026  
**Contributors**: Zakera Team

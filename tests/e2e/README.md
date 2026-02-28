# E2E Testing with Playwright

Comprehensive end-to-end testing framework for the Zakera AI Chat Agent.

## Overview

Our E2E test suite validates critical user flows across multiple browsers and devices, ensuring the entire application works correctly from a user's perspective.

## Features

- **Cross-Browser Testing**: Chromium, Firefox, WebKit
- **Mobile Testing**: iOS and Android viewports
- **Visual Regression**: Automated screenshot comparison
- **Parallel Execution**: Fast test runs with parallel workers
- **CI/CD Integration**: Automated testing in GitHub Actions
- **Page Object Model**: Maintainable test architecture
- **Rich Reporting**: HTML, JSON, and JUnit reports

## Installation

```bash
# Install Playwright and dependencies
npm install -D @playwright/test
npx playwright install --with-deps
```

## Running Tests

```bash
# Run all E2E tests
npm run test:e2e

# Run specific test file
npx playwright test tests/chat.spec.ts

# Run in headed mode (see browser)
npx playwright test --headed

# Run in debug mode
npx playwright test --debug

# Run specific browser
npx playwright test --project=chromium

# Run in UI mode (interactive)
npx playwright test --ui
```

## Test Structure

```
tests/e2e/
├── playwright.config.ts    # Playwright configuration
├── tests/                  # Test specifications
│   ├── auth.spec.ts       # Authentication tests
│   ├── chat.spec.ts       # Chat functionality tests
│   └── search.spec.ts     # Search feature tests
├── pages/                  # Page Object Models
│   ├── ChatPage.ts        # Chat page interactions
│   ├── SearchPage.ts      # Search page interactions
│   ├── LoginPage.ts       # Login page interactions
│   └── RegisterPage.ts    # Registration page interactions
└── fixtures/              # Test data and utilities
```

## Writing Tests

### Basic Test Example

```typescript
import { test, expect } from '@playwright/test';
import { ChatPage } from '../pages/ChatPage';

test('should send message', async ({ page }) => {
  const chatPage = new ChatPage(page);
  await chatPage.goto();
  await chatPage.sendMessage('Hello');
  await chatPage.waitForResponse();
  
  const response = await chatPage.getLastResponse();
  expect(response).toBeTruthy();
});
```

### Using Page Objects

```typescript
// pages/ChatPage.ts
export class ChatPage {
  constructor(private page: Page) {}
  
  async sendMessage(message: string) {
    await this.page.locator('[data-testid="input"]').fill(message);
    await this.page.locator('[data-testid="send"]').click();
  }
}
```

## Best Practices

### 1. Use Data Test IDs

```tsx
// Good
<button data-testid="send-button">Send</button>

// Avoid
<button className="btn-primary">Send</button>
```

### 2. Wait for Elements Properly

```typescript
// Good - explicit wait
await page.waitForSelector('[data-testid="message"]');

// Avoid - arbitrary timeout
await page.waitForTimeout(1000);
```

### 3. Use Page Objects

```typescript
// Good - encapsulated logic
const chatPage = new ChatPage(page);
await chatPage.sendMessage('Hello');

// Avoid - direct selectors in tests
await page.fill('[data-testid="input"]', 'Hello');
```

### 4. Independent Tests

```typescript
// Each test should set up its own state
test.beforeEach(async ({ page }) => {
  await loginPage.login('test@example.com', 'password');
});
```

### 5. Clean Assertions

```typescript
// Good - specific expectations
await expect(page.getByText('Success')).toBeVisible();

// Avoid - vague checks
expect(await page.content()).toContain('Success');
```

## CI/CD Integration

### GitHub Actions

```yaml
- name: Install Playwright
  run: npx playwright install --with-deps

- name: Run E2E tests
  run: npm run test:e2e
  env:
    E2E_BASE_URL: http://localhost:8000

- name: Upload test results
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: playwright-report
    path: e2e-report/
```

## Debugging

### Visual Debugging

```bash
# Run with headed browser
npx playwright test --headed

# Pause execution
test('debug test', async ({ page }) => {
  await page.pause();
});
```

### Trace Viewer

```bash
# View trace for failed tests
npx playwright show-trace trace.zip
```

### Screenshots and Videos

Automatic capture on failure:
- Screenshots: `test-results/`
- Videos: `test-results/`
- Traces: `test-results/`

## Reporting

### HTML Report

```bash
npx playwright show-report
```

### JSON Report

Useful for custom processing:
- Location: `e2e-results.json`
- Format: Standard Playwright JSON

### JUnit Report

For CI/CD integration:
- Location: `e2e-results.xml`
- Compatible with Jenkins, GitLab CI, etc.

## Performance Testing

```typescript
test('should load quickly', async ({ page }) => {
  const start = Date.now();
  await page.goto('/chat');
  const duration = Date.now() - start;
  
  expect(duration).toBeLessThan(3000);
});
```

## Visual Regression

```typescript
test('UI should match snapshot', async ({ page }) => {
  await page.goto('/chat');
  await expect(page).toHaveScreenshot('chat-page.png');
});
```

## Troubleshooting

### Tests Timing Out

- Increase timeout in `playwright.config.ts`
- Check for slow network requests
- Verify element selectors are correct

### Flaky Tests

- Use `page.waitForLoadState('networkidle')`
- Add explicit waits for dynamic content
- Avoid time-dependent assertions

### Browser Launch Failures

```bash
# Reinstall browsers
npx playwright install --with-deps
```

## Resources

- [Playwright Documentation](https://playwright.dev/)
- [Best Practices](https://playwright.dev/docs/best-practices)
- [API Reference](https://playwright.dev/docs/api/class-playwright)
- [Examples](https://playwright.dev/docs/examples)

## Contributing

When adding new E2E tests:

1. Create page objects for new pages
2. Use descriptive test names
3. Add comments for complex interactions
4. Ensure tests are independent
5. Update this README with new patterns

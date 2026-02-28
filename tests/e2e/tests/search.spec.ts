/**
 * E2E Tests for Conversation Search
 * 
 * Tests search functionality including filtering, sorting, and result highlighting.
 */

import { test, expect } from '@playwright/test';
import { SearchPage } from '../pages/SearchPage';
import { LoginPage } from '../pages/LoginPage';
import { ChatPage } from '../pages/ChatPage';

test.describe('Conversation Search', () => {
  let searchPage: SearchPage;
  let loginPage: LoginPage;
  let chatPage: ChatPage;

  test.beforeEach(async ({ page }) => {
    searchPage = new SearchPage(page);
    loginPage = new LoginPage(page);
    chatPage = new ChatPage(page);
    
    // Login and create test conversations
    await loginPage.goto();
    await loginPage.login('test@example.com', 'password123');
    
    // Create conversations with different content
    await chatPage.goto();
    await chatPage.sendMessage('Python programming question');
    await chatPage.waitForResponse();
    
    await chatPage.createNewConversation();
    await chatPage.sendMessage('JavaScript coding help');
    await chatPage.waitForResponse();
    
    await chatPage.createNewConversation();
    await chatPage.sendMessage('Machine learning concepts');
    await chatPage.waitForResponse();
  });

  test('should search conversations by text', async ({ page }) => {
    await searchPage.goto();
    await searchPage.search('Python');
    
    // Verify search results
    await expect(page.getByText(/Python programming/i)).toBeVisible();
    await expect(page.getByText(/JavaScript/i)).not.toBeVisible();
  });

  test('should filter by date range', async ({ page }) => {
    await searchPage.goto();
    await searchPage.openFilters();
    
    // Set date range to today
    const today = new Date();
    await searchPage.setDateRange(today, today);
    await searchPage.applyFilters();
    
    // Verify results are from today
    const results = await searchPage.getSearchResults();
    expect(results.length).toBeGreaterThan(0);
  });

  test('should filter by model', async ({ page }) => {
    await searchPage.goto();
    await searchPage.openFilters();
    await searchPage.selectModelFilter('gpt-4');
    await searchPage.applyFilters();
    
    // Verify only GPT-4 conversations appear
    await expect(page.getByText(/gpt-4/i)).toBeVisible();
  });

  test('should filter by tags', async ({ page }) => {
    await searchPage.goto();
    await searchPage.openFilters();
    await searchPage.selectTagFilter('Code');
    await searchPage.applyFilters();
    
    // Verify filtered results
    const results = await searchPage.getSearchResults();
    expect(results.length).toBeGreaterThan(0);
  });

  test('should combine multiple filters', async ({ page }) => {
    await searchPage.goto();
    await searchPage.search('programming');
    await searchPage.openFilters();
    await searchPage.selectModelFilter('gpt-4');
    await searchPage.selectTagFilter('Code');
    await searchPage.applyFilters();
    
    // Verify combined filter results
    await expect(page.getByText(/programming/i)).toBeVisible();
    await expect(page.locator('[data-testid="active-filters"]')).toContainText('gpt-4');
  });

  test('should clear search and filters', async ({ page }) => {
    await searchPage.goto();
    await searchPage.search('Python');
    await searchPage.openFilters();
    await searchPage.selectModelFilter('gpt-4');
    await searchPage.applyFilters();
    
    // Clear all
    await searchPage.clearSearch();
    
    // Verify all conversations are shown
    const results = await searchPage.getSearchResults();
    expect(results.length).toBeGreaterThanOrEqual(3);
  });

  test('should use keyboard shortcut to open search', async ({ page }) => {
    await searchPage.goto();
    
    // Press Cmd/Ctrl + K
    await page.keyboard.press(process.platform === 'darwin' ? 'Meta+K' : 'Control+K');
    
    // Verify search is focused
    const searchInput = page.locator('[data-testid="search-input"]');
    await expect(searchInput).toBeFocused();
  });

  test('should show search results count', async ({ page }) => {
    await searchPage.goto();
    await searchPage.search('programming');
    
    // Verify results count is displayed
    await expect(page.getByText(/found \d+ conversation/i)).toBeVisible();
  });

  test('should highlight search terms in results', async ({ page }) => {
    await searchPage.goto();
    await searchPage.search('Python');
    
    // Verify search term is highlighted
    const highlightedText = page.locator('mark', { hasText: 'Python' });
    await expect(highlightedText).toBeVisible();
  });

  test('should handle empty search results', async ({ page }) => {
    await searchPage.goto();
    await searchPage.search('nonexistentterm123456');
    
    // Verify empty state message
    await expect(page.getByText(/no conversations found/i)).toBeVisible();
  });

  test('should debounce search input', async ({ page }) => {
    await searchPage.goto();
    const searchInput = page.locator('[data-testid="search-input"]');
    
    // Type quickly
    await searchInput.type('Python', { delay: 50 });
    
    // Verify loading state
    await expect(page.locator('[data-testid="search-loading"]')).toBeVisible();
    
    // Wait for results
    await page.waitForTimeout(500);
    await expect(page.getByText(/found/i)).toBeVisible();
  });
});

/**
 * E2E Tests for Chat Functionality
 * 
 * Tests core chat features including sending messages, streaming responses,
 * and conversation management.
 */

import { test, expect } from '@playwright/test';
import { ChatPage } from '../pages/ChatPage';
import { LoginPage } from '../pages/LoginPage';

test.describe('Chat Functionality', () => {
  let chatPage: ChatPage;
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    chatPage = new ChatPage(page);
    loginPage = new LoginPage(page);
    
    // Login before each test
    await loginPage.goto();
    await loginPage.login('test@example.com', 'password123');
    await chatPage.goto();
  });

  test('should send a message and receive response', async ({ page }) => {
    const testMessage = 'Hello, what is 2+2?';
    
    await chatPage.sendMessage(testMessage);
    
    // Verify message appears in chat
    await expect(page.getByText(testMessage)).toBeVisible();
    
    // Wait for and verify response
    await chatPage.waitForResponse();
    const lastResponse = await chatPage.getLastResponse();
    expect(lastResponse).toBeTruthy();
    expect(lastResponse.length).toBeGreaterThan(0);
  });

  test('should handle streaming responses', async ({ page }) => {
    await chatPage.sendMessage('Write a short poem about AI');
    
    // Verify streaming indicator appears
    await expect(page.locator('[data-testid="streaming-indicator"]')).toBeVisible();
    
    // Wait for streaming to complete
    await chatPage.waitForStreamingComplete();
    
    // Verify final response is present
    const response = await chatPage.getLastResponse();
    expect(response.length).toBeGreaterThan(50);
  });

  test('should create new conversation', async ({ page }) => {
    await chatPage.createNewConversation();
    
    // Verify new conversation UI
    await expect(page.getByText(/new conversation/i)).toBeVisible();
    
    // Send message in new conversation
    await chatPage.sendMessage('Test message in new conversation');
    await chatPage.waitForResponse();
    
    const response = await chatPage.getLastResponse();
    expect(response).toBeTruthy();
  });

  test('should switch between conversations', async ({ page }) => {
    // Send message in first conversation
    const firstMessage = 'Message in conversation 1';
    await chatPage.sendMessage(firstMessage);
    await chatPage.waitForResponse();
    
    // Create new conversation
    await chatPage.createNewConversation();
    
    // Send message in second conversation
    const secondMessage = 'Message in conversation 2';
    await chatPage.sendMessage(secondMessage);
    await chatPage.waitForResponse();
    
    // Switch back to first conversation
    await chatPage.selectConversation(0);
    
    // Verify first message is visible
    await expect(page.getByText(firstMessage)).toBeVisible();
    await expect(page.getByText(secondMessage)).not.toBeVisible();
  });

  test('should select different models', async ({ page }) => {
    await chatPage.selectModel('gpt-4');
    await chatPage.sendMessage('Test with GPT-4');
    await chatPage.waitForResponse();
    
    // Verify model indicator
    await expect(page.getByText(/gpt-4/i)).toBeVisible();
  });

  test('should handle long messages', async ({ page }) => {
    const longMessage = 'A'.repeat(500);
    await chatPage.sendMessage(longMessage);
    
    // Verify message is sent
    await expect(page.getByText(longMessage)).toBeVisible();
    await chatPage.waitForResponse();
  });

  test('should show typing indicator', async ({ page }) => {
    await chatPage.sendMessage('Test typing indicator');
    
    // Verify typing indicator appears
    const typingIndicator = page.locator('[data-testid="typing-indicator"]');
    await expect(typingIndicator).toBeVisible();
    
    // Wait for response
    await chatPage.waitForResponse();
    
    // Verify typing indicator disappears
    await expect(typingIndicator).not.toBeVisible();
  });

  test('should preserve conversation context', async ({ page }) => {
    // Send first message
    await chatPage.sendMessage('My name is Alice');
    await chatPage.waitForResponse();
    
    // Send follow-up that requires context
    await chatPage.sendMessage('What is my name?');
    await chatPage.waitForResponse();
    
    const response = await chatPage.getLastResponse();
    expect(response.toLowerCase()).toContain('alice');
  });
});

test.describe('Chat Error Handling', () => {
  let chatPage: ChatPage;
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    chatPage = new ChatPage(page);
    loginPage = new LoginPage(page);
    
    await loginPage.goto();
    await loginPage.login('test@example.com', 'password123');
    await chatPage.goto();
  });

  test('should handle network errors gracefully', async ({ page }) => {
    // Simulate network offline
    await page.context().setOffline(true);
    
    await chatPage.sendMessage('Test message');
    
    // Verify error message
    await expect(page.getByText(/connection error|network error/i)).toBeVisible();
    
    // Restore network
    await page.context().setOffline(false);
  });

  test('should handle rate limiting', async ({ page }) => {
    // Send multiple messages rapidly
    const promises = [];
    for (let i = 0; i < 10; i++) {
      promises.push(chatPage.sendMessage(`Message ${i}`));
    }
    await Promise.all(promises);
    
    // Verify rate limit message appears
    await expect(page.getByText(/rate limit|too many requests/i)).toBeVisible({ timeout: 5000 });
  });
});

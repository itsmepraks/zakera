/**
 * Page Object Model for Chat Page
 * 
 * Encapsulates interactions with the main chat interface.
 */

import { Page, Locator } from '@playwright/test';

export class ChatPage {
  readonly page: Page;
  readonly messageInput: Locator;
  readonly sendButton: Locator;
  readonly messageList: Locator;
  readonly newConversationButton: Locator;
  readonly modelSelector: Locator;

  constructor(page: Page) {
    this.page = page;
    this.messageInput = page.locator('[data-testid="message-input"]');
    this.sendButton = page.locator('[data-testid="send-button"]');
    this.messageList = page.locator('[data-testid="message-list"]');
    this.newConversationButton = page.locator('[data-testid="new-conversation"]');
    this.modelSelector = page.locator('[data-testid="model-selector"]');
  }

  async goto() {
    await this.page.goto('/chat');
  }

  async sendMessage(message: string) {
    await this.messageInput.fill(message);
    await this.sendButton.click();
  }

  async waitForResponse(timeout: number = 30000) {
    await this.page.waitForSelector(
      '[data-testid="assistant-message"]:last-child',
      { timeout, state: 'visible' }
    );
  }

  async getLastResponse(): Promise<string> {
    const lastMessage = this.page.locator('[data-testid="assistant-message"]').last();
    return await lastMessage.textContent() || '';
  }

  async createNewConversation() {
    await this.newConversationButton.click();
  }

  async selectConversation(index: number) {
    const conversation = this.page.locator('[data-testid="conversation-item"]').nth(index);
    await conversation.click();
  }

  async selectModel(model: string) {
    await this.modelSelector.click();
    await this.page.locator(`[data-value="${model}"]`).click();
  }

  async waitForStreamingComplete() {
    await this.page.waitForSelector(
      '[data-testid="streaming-indicator"]',
      { state: 'hidden', timeout: 60000 }
    );
  }

  async logout() {
    await this.page.locator('[data-testid="user-menu"]').click();
    await this.page.locator('[data-testid="logout-button"]').click();
  }
}

/**
 * Page Object Model for Search Page
 * 
 * Encapsulates interactions with the conversation search interface.
 */

import { Page, Locator } from '@playwright/test';

export class SearchPage {
  readonly page: Page;
  readonly searchInput: Locator;
  readonly filterButton: Locator;
  readonly clearButton: Locator;
  readonly resultsList: Locator;

  constructor(page: Page) {
    this.page = page;
    this.searchInput = page.locator('[data-testid="search-input"]');
    this.filterButton = page.locator('[data-testid="filter-button"]');
    this.clearButton = page.locator('[data-testid="clear-search"]');
    this.resultsList = page.locator('[data-testid="search-results"]');
  }

  async goto() {
    await this.page.goto('/chat');
  }

  async search(query: string) {
    await this.searchInput.fill(query);
  }

  async clearSearch() {
    await this.clearButton.click();
  }

  async openFilters() {
    await this.filterButton.click();
  }

  async setDateRange(start: Date, end: Date) {
    // Interact with date pickers
    await this.page.locator('[data-testid="date-start"]').fill(start.toISOString().split('T')[0]);
    await this.page.locator('[data-testid="date-end"]').fill(end.toISOString().split('T')[0]);
  }

  async selectModelFilter(model: string) {
    await this.page.locator(`[data-testid="model-filter-${model}"]`).click();
  }

  async selectTagFilter(tag: string) {
    await this.page.locator(`[data-testid="tag-filter-${tag}"]`).click();
  }

  async applyFilters() {
    await this.page.locator('[data-testid="apply-filters"]').click();
  }

  async getSearchResults(): Promise<string[]> {
    const results = await this.resultsList.locator('[data-testid="result-item"]').allTextContents();
    return results;
  }
}

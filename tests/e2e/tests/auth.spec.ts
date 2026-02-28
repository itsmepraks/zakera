/**
 * E2E Tests for Authentication
 * 
 * Tests login, logout, registration, and session management.
 */

import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';
import { RegisterPage } from '../pages/RegisterPage';
import { ChatPage } from '../pages/ChatPage';

test.describe('Authentication', () => {
  test('should login with valid credentials', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login('test@example.com', 'password123');
    
    // Verify redirect to chat
    await expect(page).toHaveURL(/\/chat/);
  });

  test('should show error with invalid credentials', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login('invalid@example.com', 'wrongpassword');
    
    // Verify error message
    await expect(page.getByText(/invalid credentials|incorrect/i)).toBeVisible();
  });

  test('should logout successfully', async ({ page }) => {
    const loginPage = new LoginPage(page);
    const chatPage = new ChatPage(page);
    
    // Login first
    await loginPage.goto();
    await loginPage.login('test@example.com', 'password123');
    
    // Logout
    await chatPage.logout();
    
    // Verify redirect to login
    await expect(page).toHaveURL(/\/login/);
  });

  test('should register new user', async ({ page }) => {
    const registerPage = new RegisterPage(page);
    const timestamp = Date.now();
    const email = `test${timestamp}@example.com`;
    
    await registerPage.goto();
    await registerPage.register(
      'Test User',
      email,
      'password123',
      'password123'
    );
    
    // Verify success or redirect
    await expect(page).toHaveURL(/\/chat|\/verify-email/);
  });

  test('should validate password requirements', async ({ page }) => {
    const registerPage = new RegisterPage(page);
    await registerPage.goto();
    
    // Try weak password
    await registerPage.register(
      'Test User',
      'test@example.com',
      '123',
      '123'
    );
    
    // Verify validation error
    await expect(page.getByText(/password.*too short|minimum.*characters/i)).toBeVisible();
  });

  test('should persist session across page refresh', async ({ page }) => {
    const loginPage = new LoginPage(page);
    
    await loginPage.goto();
    await loginPage.login('test@example.com', 'password123');
    
    // Refresh page
    await page.reload();
    
    // Verify still logged in
    await expect(page).toHaveURL(/\/chat/);
  });

  test('should redirect to login when accessing protected route', async ({ page }) => {
    await page.goto('/chat');
    
    // Verify redirect to login
    await expect(page).toHaveURL(/\/login/);
  });
});

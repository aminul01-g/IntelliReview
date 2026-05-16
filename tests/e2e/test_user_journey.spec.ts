import { test, expect } from '@playwright/test';

test.describe('IntelliReview E2E Flow', () => {
  test('should complete full user journey: login -> analyze -> feedback', async ({ page }) => {
    // 1. Login Flow
    await page.goto('/login');
    await page.fill('input[placeholder="developer01"]', 'testuser');
    await page.fill('input[type="password"]', 'password123');
    await page.click('button:has-text("Sign In")');
    await expect(page).toHaveURL('/');

    // 2. Analysis Flow
    await page.click('text=Review Engine');
    await page.fill('textarea', 'def insecure():\n    print("hello world")');
    await page.click('button:has-text("Run Security Analysis")');

    // Wait for analysis to complete (websocket or polling)
    await expect(page.locator('text=Analysis Complete')).toBeVisible({ timeout: 30000 });

    // 3. Feedback Loop
    const acceptButton = page.locator('button:has-text("Accept Suggestion")').first();
    await expect(acceptButton).toBeVisible();
    await acceptButton.click();

    await expect(page.locator('text=Telemetry Feedback Sent')).toBeVisible();
  });

  test('should verify queue status is visible in header', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=Queue:')).toBeVisible();
  });
});

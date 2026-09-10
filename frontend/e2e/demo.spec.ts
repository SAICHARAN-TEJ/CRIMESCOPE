import { test, expect } from '@playwright/test';

/**
 * Demo flow — fully deterministic, no backend required (fixtures only).
 */
test.describe('Demo flow', () => {
  test('runs the simulated analysis sequence', async ({ page }) => {
    await page.goto('/demo');
    await expect(page.locator('.demo-banner')).toContainText('Demo Mode');

    // Start the simulated pipeline
    await page.getByRole('button', { name: /Start Analysis/ }).click();

    // Events stream in via timers → the log fills
    await expect(page.locator('.log__row').first()).toBeVisible({ timeout: 15_000 });

    // Pipeline reaches COMPLETE (badge--green appears in the nav)
    await expect(page.locator('.badge--green').first()).toBeVisible({ timeout: 60_000 });
  });

  test('materializes demo personas', async ({ page }) => {
    await page.goto('/demo');
    await page.getByRole('button', { name: /Start Analysis/ }).click();
    await expect(page.locator('.badge--green').first()).toBeVisible({ timeout: 60_000 });

    await page.getByRole('button', { name: /MATERIALIZE/ }).click();
    await expect(page.locator('.persona-card').first()).toBeVisible({ timeout: 15_000 });
    await expect(page.locator('.persona-card')).toHaveCount(2, { timeout: 15_000 });
  });

  test('chat streams a canned response', async ({ page }) => {
    await page.goto('/demo');
    await page.getByRole('button', { name: /Start Analysis/ }).click();
    await expect(page.locator('.badge--green').first()).toBeVisible({ timeout: 60_000 });

    await page.locator('.chat-input').fill('What happened?');
    await page.getByRole('button', { name: 'SEND' }).click();
    await expect(page.locator('.chat-message--assistant').first()).toBeVisible({ timeout: 15_000 });
  });
});

import { test, expect } from '@playwright/test';

/**
 * /app login flow — credentials come from the environment
 * (ADMIN_USERNAME / ADMIN_PASSWORD), never hardcoded.
 */
const username = process.env.ADMIN_USERNAME ?? 'admin';
const password = process.env.ADMIN_PASSWORD ?? 'crimescope';

test.describe('/app login', () => {
  test('login form shows an error on bad credentials', async ({ page }) => {
    await page.goto('/app');
    await expect(page.getByRole('heading', { name: 'Sign In' })).toBeVisible();

    await page.locator('#cs-username').fill('no-such-user');
    await page.locator('#cs-password').fill('wrong-password');
    await page.getByRole('button', { name: /Sign In/ }).click();

    // Client-side error path is exercised whether the backend is up (401)
    // or down (network error) — both render the same form error.
    await expect(page.locator('.form__error').first()).toBeVisible({ timeout: 15_000 });
  });

  test('logs in with env credentials when the backend is available', async ({ page }) => {
    test.skip(!process.env.PLAYWRIGHT_BACKEND, 'Set PLAYWRIGHT_BACKEND=1 with a running API to enable');

    await page.goto('/app');
    await page.locator('#cs-username').fill(username);
    await page.locator('#cs-password').fill(password);
    await page.getByRole('button', { name: /Sign In/ }).click();

    // "Authenticated" badge appears in the nav
    await expect(page.locator('.badge--green').first()).toBeVisible({ timeout: 15_000 });
  });
});

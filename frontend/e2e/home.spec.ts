import { test, expect } from '@playwright/test';

test.describe('Homepage', () => {
  test('loads the homepage and displays correct links', async ({ page }) => {
    await page.goto('/');

    // Check title/headline
    await expect(page.locator('h1')).toContainText('Reconstruct the truth.');

    // Check primary CTA links to demo ("Run the live demo")
    const tryDemoBtn = page.locator('a.home-btn--primary', { hasText: 'Run the live demo' }).first();
    await expect(tryDemoBtn).toBeVisible();
    await expect(tryDemoBtn).toHaveAttribute('href', '/demo');

    // Check secondary CTA links to app ("Open the app")
    const openAppBtn = page.locator('a', { hasText: 'Open the app' }).first();
    await expect(openAppBtn).toBeVisible();
    await expect(openAppBtn).toHaveAttribute('href', '/app');

    // Check verify stage is marked SKIPPED - NOT IMPLEMENTED
    await expect(page.locator('.verify-badge')).toContainText('SKIPPED — NOT IMPLEMENTED');
  });

  test('respects prefers-reduced-motion', async ({ page }) => {
    // Emulate reduced motion
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('/');

    // Ensure the paper grain overlay is hidden
    const grainOverlay = page.locator('.case-grain-overlay');
    await expect(grainOverlay).toHaveCSS('display', 'none');
  });
});

import { test, expect } from '@playwright/test';

test.describe('Homepage', () => {
  test('loads the homepage and displays correct links', async ({ page }) => {
    await page.goto('/');

    // Check title/headline
    await expect(page.locator('h1')).toContainText('Reconstruct the truth.');

    // Check primary CTA links to demo
    const tryDemoBtn = page.locator('a.home-btn--primary', { hasText: 'Try the Demo' }).first();
    await expect(tryDemoBtn).toBeVisible();
    await expect(tryDemoBtn).toHaveAttribute('href', '/demo');

    // Check secondary CTA links to app
    const openAppBtn = page.locator('a.home-btn--secondary', { hasText: 'Open CrimeScope' }).first();
    await expect(openAppBtn).toBeVisible();
    await expect(openAppBtn).toHaveAttribute('href', '/app');
  });

  test('respects prefers-reduced-motion', async ({ page }) => {
    // Emulate reduced motion
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('/');

    // Ensure the ambient background is hidden or has no animation
    const ambientBg = page.locator('.hero-ambient-bg');
    await expect(ambientBg).toHaveCSS('display', 'none');
  });
});

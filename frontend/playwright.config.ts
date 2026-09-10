import { defineConfig, devices } from '@playwright/test';

/**
 * CrimeScope frontend e2e config.
 * - Spins up `vite dev` automatically unless PLAYWRIGHT_BASE_URL points at
 *   an already-running server (CI or local `vite preview`).
 * - The /app login spec is credential-driven via ADMIN_USERNAME /
 *   ADMIN_PASSWORD so wave-2 auth changes can't break it with hardcoded creds.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3000',
    trace: 'on-first-retry',
  },
  webServer: process.env.PLAYWRIGHT_BASE_URL
    ? undefined
    : {
        command: 'npm run dev',
        url: 'http://localhost:3000',
        reuseExistingServer: !process.env.CI,
        timeout: 60_000,
      },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    }
  ],
});

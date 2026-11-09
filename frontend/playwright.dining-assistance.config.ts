// MoulAI™ — reuse only the owned loopback review, never spawn an external service.
import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests/e2e',
  testMatch: ['dining-assistance.spec.ts', 'access-assistance.spec.ts'],
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 90000,
  outputDir: '../artifacts/assistance-options-20261107/browser',
  reporter: [
    ['list'],
    [
      'json',
      {
        outputFile:
          '../artifacts/assistance-options-20261107/browser-results.json',
      },
    ],
  ],
  use: {
    browserName: 'chromium',
    baseURL: 'http://127.0.0.1:5574',
    viewport: { width: 1440, height: 1000 },
    trace: 'off',
    screenshot: 'only-on-failure',
  },
});

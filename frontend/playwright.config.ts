// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { defineConfig } from '@playwright/test';
import { fileURLToPath } from 'node:url';

process.env.PLAYWRIGHT_BROWSERS_PATH ??= fileURLToPath(
  new URL('../artifacts/frontend-tooling/browsers', import.meta.url),
);

/** Two owned loopback servers: synthetic development and disconnected build. */
export default defineConfig({
  testDir: './tests/e2e',
  outputDir: '../artifacts/frontend-identity-validation/browser-results',
  reporter: [
    ['list'],
    [
      'json',
      {
        outputFile:
          '../artifacts/frontend-identity-validation/playwright-results.json',
      },
    ],
  ],
  fullyParallel: false,
  workers: 1,
  retries: 0,
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'desktop',
      use: { browserName: 'chromium', viewport: { width: 1440, height: 1000 } },
    },
    {
      name: 'mobile',
      use: {
        browserName: 'chromium',
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true,
      },
    },
  ],
  webServer: [
    {
      command: 'npm run dev:review',
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: false,
    },
    {
      command: 'npm run preview',
      url: 'http://127.0.0.1:4173',
      reuseExistingServer: false,
    },
  ],
});

// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { defineConfig } from '@playwright/test';
import base from './playwright.config';

/** Keep the accepted evidence intact and exercise only access/navigation changes. */
export default defineConfig({
  ...base,
  use: { ...base.use, baseURL: 'http://127.0.0.1:5273' },
  outputDir: '../artifacts/frontend-gateway-validation/browser-results',
  reporter: [
    ['list'],
    [
      'json',
      {
        outputFile:
          '../artifacts/frontend-gateway-validation/playwright-results.json',
      },
    ],
  ],
  projects: [
    {
      name: 'desktop',
      testMatch: 'gateway.spec.ts',
      use: { browserName: 'chromium', viewport: { width: 1440, height: 1000 } },
    },
  ],
  webServer: [
    {
      command:
        'node node_modules/vite/bin/vite.js --mode review --host 127.0.0.1 --port 5273',
      url: 'http://127.0.0.1:5273',
      reuseExistingServer: false,
    },
    {
      command:
        'node node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port 4273',
      url: 'http://127.0.0.1:4273',
      reuseExistingServer: false,
    },
  ],
});

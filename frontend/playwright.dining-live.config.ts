// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { defineConfig } from '@playwright/test';
import base from './playwright.config';

/** Signed local HTTP and disposable PostgreSQL; never record credential-bearing traces. */
export default defineConfig({
  ...base,
  timeout: 180000,
  use: {
    ...base.use,
    baseURL: 'http://127.0.0.1:5574',
    trace: 'off',
    screenshot: 'only-on-failure',
  },
  outputDir: '../artifacts/dining-integration-20261103/browser-results',
  reporter: [
    ['list'],
    [
      'json',
      {
        outputFile:
          '../artifacts/dining-integration-20261103/browser-results.json',
      },
    ],
  ],
  projects: [
    {
      name: 'dining-live',
      testMatch: 'dining-live.spec.ts',
      use: { browserName: 'chromium', viewport: { width: 1440, height: 1000 } },
    },
  ],
  webServer: {
    command:
      'node node_modules/vite/bin/vite.js --mode dining --host 127.0.0.1 --port 5574 --strictPort',
    url: 'http://127.0.0.1:5574',
    reuseExistingServer: false,
  },
});

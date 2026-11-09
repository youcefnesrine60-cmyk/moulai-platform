// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { defineConfig } from '@playwright/test';
import base from './playwright.config';
export default defineConfig({
  ...base,
  timeout: 60000,
  use: {
    ...base.use,
    baseURL: 'http://127.0.0.1:5474',
    trace: 'off',
    screenshot: 'only-on-failure',
  },
  outputDir: '../artifacts/dining-readability-20261103/synthetic-results',
  reporter: [
    ['list'],
    [
      'json',
      {
        outputFile:
          '../artifacts/dining-readability-20261103/synthetic-results.json',
      },
    ],
  ],
  projects: [
    {
      name: 'dining-synthetic-polish',
      testMatch: 'dining-readability-synthetic.spec.ts',
      use: { browserName: 'chromium' },
    },
  ],
  webServer: [
    {
      command:
        'node node_modules/vite/bin/vite.js --mode review --host 127.0.0.1 --port 5474 --strictPort',
      url: 'http://127.0.0.1:5474',
      reuseExistingServer: false,
    },
    {
      command:
        'node node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port 4474 --strictPort',
      url: 'http://127.0.0.1:4474',
      reuseExistingServer: false,
    },
  ],
});

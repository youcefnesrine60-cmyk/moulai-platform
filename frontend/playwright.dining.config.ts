// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { defineConfig } from '@playwright/test';
import base from './playwright.config';

/** Dedicated loopback review/build servers and separate evidence directory. */
export default defineConfig({
  ...base,
  use: { ...base.use, baseURL: 'http://127.0.0.1:5473' },
  timeout: 60000,
  outputDir: '../artifacts/dining-module-20261102/browser-results',
  reporter: [
    ['list'],
    [
      'json',
      {
        outputFile: '../artifacts/dining-module-20261102/browser-results.json',
      },
    ],
  ],
  projects: [
    {
      name: 'dining',
      testMatch: 'dining.spec.ts',
      use: { browserName: 'chromium' },
    },
  ],
  webServer: [
    {
      command:
        'node node_modules/vite/bin/vite.js --mode review --host 127.0.0.1 --port 5473 --strictPort',
      url: 'http://127.0.0.1:5473',
      reuseExistingServer: false,
    },
    {
      command:
        'node node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port 4473 --strictPort',
      url: 'http://127.0.0.1:4473',
      reuseExistingServer: false,
    },
  ],
});

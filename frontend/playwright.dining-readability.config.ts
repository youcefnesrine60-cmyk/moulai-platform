// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { defineConfig } from '@playwright/test';
import base from './playwright.config';
const phase = process.env.DINING_POLISH_PHASE === 'before' ? 'before' : 'after';
export default defineConfig({
  ...base,
  timeout: 45000,
  use: {
    ...base.use,
    baseURL: 'http://127.0.0.1:5574',
    trace: 'off',
    screenshot: 'only-on-failure',
  },
  outputDir: `../artifacts/dining-readability-20261103/${phase}-results`,
  reporter: [
    ['list'],
    [
      'json',
      {
        outputFile: `../artifacts/dining-readability-20261103/${phase}-results.json`,
      },
    ],
  ],
  projects: [
    {
      name: 'dining-presentation',
      testMatch: 'dining-readability.spec.ts',
      use: { browserName: 'chromium' },
    },
  ],
  webServer: {
    command:
      'node node_modules/vite/bin/vite.js --mode dining --host 127.0.0.1 --port 5574 --strictPort',
    url: 'http://127.0.0.1:5574',
    reuseExistingServer: true,
  },
});

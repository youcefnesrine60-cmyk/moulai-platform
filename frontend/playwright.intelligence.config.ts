// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { defineConfig } from '@playwright/test';
import gateway from './playwright.gateway.config';

/** Owned loopback servers and a separate evidence directory preserve accepted campaigns. */
export default defineConfig({
  ...gateway,
  metadata: {
    evidenceDirectory: '../artifacts/frontend-intelligence-validation',
  },
  outputDir: '../artifacts/frontend-intelligence-validation/browser-results',
  reporter: [
    ['list'],
    [
      'json',
      {
        outputFile:
          '../artifacts/frontend-intelligence-validation/playwright-results.json',
      },
    ],
  ],
  projects: [
    {
      name: 'intelligence',
      testMatch: 'intelligence.spec.ts',
      use: { browserName: 'chromium', viewport: { width: 1440, height: 1000 } },
    },
  ],
});

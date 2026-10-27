// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { defineConfig } from '@playwright/test';
import gateway from './playwright.gateway.config';

/** Keep earlier evidence intact and exercise only the approved brand integration. */
export default defineConfig({
  ...gateway,
  metadata: {
    evidenceDirectory: '../artifacts/frontend-presentation-01-validation',
  },
  outputDir: '../artifacts/frontend-presentation-01-validation/browser-results',
  reporter: [
    ['list'],
    [
      'json',
      {
        outputFile:
          '../artifacts/frontend-presentation-01-validation/playwright-results.json',
      },
    ],
  ],
  projects: [
    {
      name: 'signature',
      testMatch: 'brand-signature.spec.ts',
      use: { browserName: 'chromium', viewport: { width: 1440, height: 1000 } },
    },
    {
      name: 'existing-draft-regression',
      testMatch: 'polish.spec.ts',
      grep: /(1440|320)px:/,
      use: { browserName: 'chromium', viewport: { width: 1440, height: 1000 } },
    },
  ],
});

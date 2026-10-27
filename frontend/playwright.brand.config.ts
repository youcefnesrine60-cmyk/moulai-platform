// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { defineConfig } from '@playwright/test';
import gateway from './playwright.gateway.config';

/** Reuse owned loopback servers while retaining every previous delivery's evidence. */
export default defineConfig({
  ...gateway,
  outputDir: '../artifacts/frontend-platform-brand-validation/browser-results',
  reporter: [
    ['list'],
    [
      'json',
      {
        outputFile:
          '../artifacts/frontend-platform-brand-validation/playwright-results.json',
      },
    ],
  ],
  projects: [
    {
      name: 'responsive-brand',
      testMatch: ['gateway.spec.ts', 'brand-platform.spec.ts'],
      use: { browserName: 'chromium', viewport: { width: 1440, height: 1000 } },
    },
  ],
});

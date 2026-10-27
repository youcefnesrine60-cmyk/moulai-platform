// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { defineConfig } from '@playwright/test';
import brand from './playwright.brand.config';

/** Keep earlier evidence immutable while testing shared chrome and draft preservation. */
export default defineConfig({
  ...brand,
  metadata: { evidenceDirectory: '../artifacts/frontend-polish-validation' },
  outputDir: '../artifacts/frontend-polish-validation/browser-results',
  reporter: [
    ['list'],
    [
      'json',
      {
        outputFile:
          '../artifacts/frontend-polish-validation/playwright-results.json',
      },
    ],
  ],
  projects: [
    {
      name: 'polish',
      testMatch: [
        'gateway.spec.ts',
        'brand-platform.spec.ts',
        'polish.spec.ts',
      ],
      use: { browserName: 'chromium', viewport: { width: 1440, height: 1000 } },
    },
  ],
});

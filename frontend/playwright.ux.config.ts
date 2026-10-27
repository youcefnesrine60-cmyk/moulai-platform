// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { defineConfig } from '@playwright/test';
import signature from './playwright.signature.config';

/** Reuse focused brand/draft coverage while retaining previous delivery evidence. */
export default defineConfig({
  ...signature,
  metadata: { evidenceDirectory: '../artifacts/frontend-ux-final-validation' },
  outputDir: '../artifacts/frontend-ux-final-validation/browser-results',
  reporter: [
    ['list'],
    [
      'json',
      {
        outputFile:
          '../artifacts/frontend-ux-final-validation/playwright-results.json',
      },
    ],
  ],
});

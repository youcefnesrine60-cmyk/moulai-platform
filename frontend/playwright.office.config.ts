import { defineConfig } from '@playwright/test';
import base from './playwright.config';

/** Independent local servers/evidence; no accepted campaign or service is restarted. */
export default defineConfig({
  ...base,
  use: { ...base.use, baseURL: 'http://127.0.0.1:5373' },
  timeout: 90000,
  outputDir: '../artifacts/frontend-office-validation/browser-results',
  reporter: [
    ['list'],
    [
      'json',
      {
        outputFile:
          '../artifacts/frontend-office-validation/playwright-results.json',
      },
    ],
  ],
  projects: [
    {
      name: 'office',
      testMatch: 'office.spec.ts',
      use: { browserName: 'chromium' },
    },
  ],
  webServer: [
    {
      command:
        'node node_modules/vite/bin/vite.js --mode review --host 127.0.0.1 --port 5373',
      url: 'http://127.0.0.1:5373',
      reuseExistingServer: false,
    },
    {
      command:
        'node node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port 4373',
      url: 'http://127.0.0.1:4373',
      reuseExistingServer: false,
    },
  ],
});

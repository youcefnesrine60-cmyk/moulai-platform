import { defineConfig } from '@playwright/test';
import base from './playwright.config';

/** Only extension scenarios; previous office evidence/campaign remains intact. */
export default defineConfig({
  ...base,
  use: { ...base.use, baseURL: 'http://127.0.0.1:5473' },
  timeout: 60000,
  outputDir: '../artifacts/frontend-office-extension/browser-results',
  reporter: [
    ['list'],
    [
      'json',
      {
        outputFile:
          '../artifacts/frontend-office-extension/playwright-results.json',
      },
    ],
  ],
  projects: [
    {
      name: 'office-extension',
      testMatch: 'office-extension.spec.ts',
      use: { browserName: 'chromium' },
    },
  ],
  webServer: [
    {
      command:
        'node node_modules/vite/bin/vite.js --mode review --host 127.0.0.1 --port 5473',
      url: 'http://127.0.0.1:5473',
      reuseExistingServer: false,
    },
    {
      command:
        'node node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port 4473',
      url: 'http://127.0.0.1:4473',
      reuseExistingServer: false,
    },
  ],
});

// MoulAI™ — local service extensions and safe read-only presentation validation.
import { defineConfig } from '@playwright/test';
import base from './playwright.config';
export default defineConfig({
  ...base,
  timeout: 360000,
  retries: 0,
  testMatch: ['dining-service-presentation.spec.ts', 'dining-qr-live.spec.ts'],
  outputDir: '../artifacts/dining-qr-staff-20261105/browser-presentation',
  reporter: [
    ['list'],
    [
      'json',
      {
        outputFile:
          '../artifacts/dining-qr-staff-20261105/browser-presentation.json',
      },
    ],
  ],
  projects: [
    {
      name: 'service-presentation',
      use: { browserName: 'chromium', viewport: { width: 1440, height: 1000 } },
    },
  ],
  use: {
    ...base.use,
    baseURL: 'http://127.0.0.1:5574',
    trace: 'off',
    actionTimeout: 20000,
    screenshot: 'only-on-failure',
  },
  webServer: [
    {
      command:
        'node node_modules/vite/bin/vite.js --mode dining --host 127.0.0.1 --port 5574 --strictPort',
      url: 'http://127.0.0.1:5574',
      reuseExistingServer: true,
    },
    {
      command:
        'node node_modules/vite/bin/vite.js --mode review --host 127.0.0.1 --port 5173 --strictPort',
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: true,
    },
  ],
});

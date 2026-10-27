import { defineConfig } from '@playwright/test';
import base from './playwright.config';

const baseline = process.env.MOULAI_POLISH_STAGE === 'before';
/** Only reports and billing; keep the preceding accepted evidence intact. */
export default defineConfig({
  ...base,
  use: { ...base.use, baseURL: 'http://127.0.0.1:5573' },
  timeout: 60000,
  outputDir: `../artifacts/frontend-business-polish/${baseline ? 'before' : 'after'}-browser-results`,
  reporter: [
    ['list'],
    [
      'json',
      {
        outputFile: `../artifacts/frontend-business-polish/${baseline ? 'before' : 'after'}-results.json`,
      },
    ],
  ],
  projects: [
    {
      name: 'business-polish',
      testMatch: 'business-polish.spec.ts',
      use: { browserName: 'chromium' },
    },
  ],
  webServer: [
    {
      command:
        'node node_modules/vite/bin/vite.js --mode review --host 127.0.0.1 --port 5573',
      url: 'http://127.0.0.1:5573',
      reuseExistingServer: false,
    },
  ],
});

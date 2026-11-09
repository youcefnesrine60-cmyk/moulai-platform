// MoulAI™ — local UI rehearsal, credentials stay in memory and traces stay disabled.
import { defineConfig } from '@playwright/test';
import base from './playwright.config';
const suite = process.env.DINING_FINAL_SUITE ?? 'ui';
export default defineConfig({
  ...base,
  timeout: 300000,
  outputDir: `../artifacts/dining-final-rehearsal-20261104/browser-${suite}-results`,
  reporter: [
    ['list'],
    [
      'json',
      {
        outputFile: `../artifacts/dining-final-rehearsal-20261104/browser-${suite}-results.json`,
      },
    ],
  ],
  use: {
    ...base.use,
    baseURL: 'http://127.0.0.1:5574',
    trace: 'off',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'dining-final',
      testMatch: [
        'dining-final-rehearsal.spec.ts',
        'dining-final-presentation.spec.ts',
      ],
      use: { browserName: 'chromium', viewport: { width: 1440, height: 1000 } },
    },
  ],
  webServer: {
    command:
      'node node_modules/vite/bin/vite.js --mode dining --host 127.0.0.1 --port 5574 --strictPort',
    url: 'http://127.0.0.1:5574',
    reuseExistingServer: true,
  },
});

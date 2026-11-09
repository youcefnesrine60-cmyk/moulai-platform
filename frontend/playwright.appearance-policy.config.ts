import { defineConfig } from '@playwright/test';
import base from './playwright.dining-polish.config';
export default defineConfig({
  ...base,
  testMatch: [
    'appearance.spec.ts',
    'gateway.spec.ts',
    'office-extension.spec.ts',
    'business-polish.spec.ts',
    'dining-final-presentation.spec.ts',
  ],
  use: { ...base.use, baseURL: 'http://127.0.0.1:5173', timezoneId: 'UTC' },
  projects: [
    {
      name: 'gateway-policy',
      testMatch: 'gateway.spec.ts',
      use: {
        browserName: 'chromium',
        baseURL: 'http://127.0.0.1:5173',
        timezoneId: 'UTC',
      },
    },
    {
      name: 'policy',
      testMatch: 'appearance.spec.ts',
      use: {
        browserName: 'chromium',
        baseURL: 'http://127.0.0.1:5173',
        timezoneId: 'UTC',
      },
    },
    {
      name: 'business-policy',
      testMatch: 'business-polish.spec.ts',
      use: {
        browserName: 'chromium',
        baseURL: 'http://127.0.0.1:5173',
        timezoneId: 'UTC',
      },
    },
    {
      name: 'office-policy',
      testMatch: 'office-extension.spec.ts',
      use: {
        browserName: 'chromium',
        baseURL: 'http://127.0.0.1:5173',
        timezoneId: 'UTC',
      },
    },
    {
      name: 'dining-policy',
      testMatch: 'dining-final-presentation.spec.ts',
      use: {
        browserName: 'chromium',
        baseURL: 'http://127.0.0.1:5574',
        timezoneId: 'UTC',
      },
    },
  ],
  webServer: base.webServer,
  reporter: [['list']],
});

import { defineConfig } from '@playwright/test';
import base from './playwright.dining-service.config';
export default defineConfig({
  ...base,
  testMatch: 'dining-polish.spec.ts',
  outputDir: '../artifacts/dining-polish-20261105/browser',
  reporter: [['list']],
});

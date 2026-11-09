// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { installManualThemeFixture } from './manualThemeFixture';
import { test, expect } from '@playwright/test';
import { fileURLToPath } from 'node:url';
import AxeBuilder from '@axe-core/playwright';
import { fr } from '../../src/shared/i18n/fr';
import { en } from '../../src/shared/i18n/en';
import { ar } from '../../src/shared/i18n/ar';
import { diningFr } from '../../src/shared/i18n/dining.fr';
import { diningEn } from '../../src/shared/i18n/dining.en';
import { diningAr } from '../../src/shared/i18n/dining.ar';

const copies = {
  fr: { ...fr, ...diningFr },
  en: { ...en, ...diningEn },
  ar: { ...ar, ...diningAr },
};
test.beforeEach(async ({ page }) => {
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    expect(url.hostname).toBe('127.0.0.1');
    expect(['5473', '4473']).toContain(url.port);
    expect(['GET', 'HEAD']).toContain(route.request().method());
    expect(url.pathname).not.toMatch(/^\/api(?:\/|$)/);
    await route.continue();
  });
  page.on('pageerror', (error) => {
    throw error;
  });
});
for (const width of [1440, 390])
  for (const locale of ['fr', 'en', 'ar'] as const)
    for (const theme of ['light', 'dark'] as const)
      test(`dining ${width}/${locale}/${theme}`, async ({ page }) => {
        const copy = copies[locale];
        await page.setViewportSize({ width, height: 1000 });
        await page.addInitScript(
          ({ locale, theme }) => {
            localStorage.setItem('moulai.locale', locale);
            localStorage.setItem('moulai.theme', theme);
          },
          { locale, theme },
        );
        await page.goto('/access');
        await page
          .getByRole('button', { name: copy['review.open'], exact: true })
          .click();
        await expect(page).toHaveURL(/\/workspace$/);
        await page.evaluate(() => {
          history.pushState(
            null,
            '',
            '/workspace/organizations/9101/restaurants/9201/tables',
          );
          dispatchEvent(new PopStateEvent('popstate'));
        });
        await expect(
          page.getByRole('heading', { name: copy['dining.title'], level: 1 }),
        ).toBeVisible();
        await page
          .getByRole('combobox', { name: copy['dining.branch'] })
          .selectOption('920101');
        await expect(
          page.getByText('6000.00 DZD', { exact: true }),
        ).toHaveCount(2);
        await page
          .getByRole('button', { name: copy['dining.finalize'] })
          .click();
        await expect(
          page.getByText('4500.00 DZD', { exact: true }),
        ).toBeVisible();
        await expect(page.locator('html')).toHaveAttribute(
          'dir',
          locale === 'ar' ? 'rtl' : 'ltr',
        );
        await expect(page.locator('html')).toHaveAttribute('data-theme', theme);
        await page.evaluate(() => document.fonts.ready);
        expect(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
        ).toBe(true);
        expect(
          (
            await new AxeBuilder({ page })
              .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
              .analyze()
          ).violations,
        ).toEqual([]);
        await page.evaluate(() =>
          window.scrollTo({ top: 0, behavior: 'instant' }),
        );
        await page.screenshot({
          path: fileURLToPath(
            new URL(
              `../../../artifacts/dining-module-20261102/${width}-${locale}-${theme}.png`,
              import.meta.url,
            ),
          ),
          fullPage: true,
        });
      });

test('production build remains disconnected', async ({ page }) => {
  await page.goto(
    'http://127.0.0.1:4473/workspace/organizations/9101/restaurants/9201/tables',
  );
  await expect(page).toHaveURL(/\/access$/);
  await expect(
    page.getByRole('combobox', { name: copies.fr['dining.branch'] }),
  ).toHaveCount(0);
});

// Visual fixtures request a manual choice; opening policy is checked independently.
test.beforeEach(async ({ page }) => installManualThemeFixture(page));

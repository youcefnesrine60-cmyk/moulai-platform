// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { createHash } from 'node:crypto';
import { expect, test, type Page, type TestInfo } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { fr } from '../../src/shared/i18n/fr';
import { en } from '../../src/shared/i18n/en';
import { ar } from '../../src/shared/i18n/ar';
import { businessFr } from '../../src/shared/i18n/business.fr';
import { businessEn } from '../../src/shared/i18n/business.en';
import { businessAr } from '../../src/shared/i18n/business.ar';
import type { Locale } from '../../src/shared/access/contracts';
import type { Theme } from '../../src/shared/theme';
import logos from '../../brand-sources/logo-manifest.json' with { type: 'json' };
import { checkHeader, evidenceDirectory } from './polish-checks';

const resources: Record<Locale, Readonly<Record<string, string>>> = {
  fr: { ...fr, ...businessFr },
  en: { ...en, ...businessEn },
  ar: { ...ar, ...businessAr },
};
const base = '/workspace/organizations/9101/restaurants/9201';

/** Preserve the existing wording and fail if a tested translation is unavailable. */
function copy(locale: Locale, key: string): string {
  const text = resources[locale][key];
  if (!text) throw new Error(`Missing ${locale}:${key}`);
  return text;
}

/** Navigate without replacing the synthetic session or its selected context. */
async function go(page: Page, path: string): Promise<void> {
  await page.evaluate((destination) => {
    history.pushState(null, '', destination);
    dispatchEvent(new PopStateEvent('popstate'));
  }, path);
}

/** Inspect the real shared decoration, centered transparent logo, bounds and contrast. */
async function inspect(
  page: Page,
  theme: Theme,
  label: string,
  info: TestInfo,
): Promise<void> {
  await page.evaluate(() => document.fonts.ready);
  await expect(page.locator('[data-gateway]')).toHaveCount(1);
  await expect(page.locator('[data-gateway]')).toHaveAttribute(
    'data-gateway',
    theme,
  );
  const logo = page.locator('header img[alt="MoulAI™"]');
  await expect(logo).toHaveAttribute(
    'src',
    `/brand/moulai-logo-${theme}01.png`,
  );
  await expect
    .poll(() =>
      logo.evaluate(
        (image: HTMLImageElement) => image.complete && image.naturalWidth > 0,
      ),
    )
    .toBe(true);
  const measured = await logo.evaluate((image) => {
    const rect = image.getBoundingClientRect();
    const header = image.closest('header')!.getBoundingClientRect();
    return {
      center: rect.x + rect.width / 2,
      headerCenter: header.x + header.width / 2,
      ratio: rect.width / rect.height,
      filter: getComputedStyle(image).filter,
      transform: getComputedStyle(image).transform,
      backing: getComputedStyle(image.parentElement!).backgroundColor,
      overflow: document.documentElement.scrollWidth > innerWidth,
    };
  });
  expect(measured.center).toBeCloseTo(measured.headerCenter, 0);
  const source = logos.sources.find((source) => source.theme === theme)!;
  expect(measured.ratio).toBeCloseTo(source.width / source.height, 2);
  expect(measured.filter).toBe('none');
  expect(measured.transform).toBe('none');
  expect(measured.backing).toBe('rgba(0, 0, 0, 0)');
  expect(measured.overflow).toBe(false);
  if (info.config.metadata['evidenceDirectory']) await checkHeader(page, info);
  const result = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
    .analyze();
  expect(result.violations).toEqual([]);
  await info.attach(label, {
    body: JSON.stringify({ ...measured, axeViolations: 0 }),
    contentType: 'application/json',
  });
  await page.screenshot({
    path: `${evidenceDirectory(info)}/${label}.png`,
    fullPage: true,
  });
}

test.beforeEach(async ({ page }) => {
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    expect(['127.0.0.1', 'localhost']).toContain(url.hostname);
    expect(['5273', '4273']).toContain(url.port);
    await route.continue();
  });
  page.on('pageerror', (error) => {
    throw error;
  });
});

for (const width of [1440, 834, 360])
  for (const locale of ['fr', 'en', 'ar'] as const)
    for (const theme of ['light', 'dark'] as const)
      test(`Shared brand ${width}px ${locale}/${theme}: workspace, management and platform`, async ({
        page,
      }, info) => {
        test.setTimeout(120000);
        await page.setViewportSize({
          width,
          height: width === 360 ? 844 : 1000,
        });
        await page.addInitScript(
          ({ locale, theme }) => {
            localStorage.setItem('moulai.locale', locale);
            localStorage.setItem('moulai.theme', theme);
          },
          { locale, theme },
        );
        await page.goto('/access');
        await expect(
          page.getByRole('heading', { name: copy(locale, 'access.title') }),
        ).toBeVisible();
        const source = logos.sources.find((source) => source.theme === theme)!;
        const response = await page.request.get(`/brand/${source.file}`);
        expect(
          createHash('sha256')
            .update(await response.body())
            .digest('hex'),
        ).toBe(source.sha256);
        await page
          .getByRole('button', { name: copy(locale, 'review.open') })
          .click();
        await expect(
          page.getByRole('heading', { name: copy(locale, 'companies.title') }),
        ).toBeVisible();
        await inspect(
          page,
          theme,
          `${width}-${locale}-${theme}-workspace`,
          info,
        );
        await page
          .getByRole('link', {
            name: new RegExp(`^${copy(locale, 'companies.open')}`),
          })
          .first()
          .click();
        await expect(
          page
            .getByRole('link', {
              name: new RegExp(`^${copy(locale, 'restaurants.open')}`),
            })
            .first(),
        ).toBeVisible();
        await inspect(
          page,
          theme,
          `${width}-${locale}-${theme}-restaurants`,
          info,
        );
        await page
          .getByRole('link', {
            name: new RegExp(`^${copy(locale, 'restaurants.open')}`),
          })
          .first()
          .click();
        await expect(
          page.getByRole('button', {
            name: copy(locale, 'business.editProfile'),
          }),
        ).toBeVisible();
        await inspect(page, theme, `${width}-${locale}-${theme}-profile`, info);
        await go(page, `${base}/catalogue`);
        await expect(
          page.getByRole('heading', {
            name: copy(locale, 'business.catalogue'),
          }),
        ).toBeVisible();
        await inspect(
          page,
          theme,
          `${width}-${locale}-${theme}-catalogue`,
          info,
        );
        await go(page, `${base}/orders`);
        await expect(
          page.getByRole('heading', { name: copy(locale, 'business.orders') }),
        ).toBeVisible();
        await inspect(page, theme, `${width}-${locale}-${theme}-orders`, info);
        await go(page, `${base}/orders/920160`);
        await expect(
          page.getByRole('heading', { name: 'REV-9201-001' }),
        ).toBeVisible();
        await inspect(
          page,
          theme,
          `${width}-${locale}-${theme}-order-detail`,
          info,
        );
        await go(page, '/platform');
        await expect(
          page.getByRole('heading', {
            name: copy(locale, 'state.noAccess.title'),
          }),
        ).toBeVisible();
        // Leave from the denial screen using the existing approved session-exit action.
        await page
          .getByRole('button', { name: copy(locale, 'common.changeProfile') })
          .click();
        await expect(
          page.getByRole('heading', { name: copy(locale, 'access.title') }),
        ).toBeVisible();
        await page
          .getByRole('combobox', { name: copy(locale, 'review.profile') })
          .click();
        await page
          .getByRole('option', {
            name: copy(locale, 'profile.admin'),
            exact: true,
          })
          .click();
        await page
          .getByRole('button', { name: copy(locale, 'review.open') })
          .click();
        await expect(
          page.getByRole('heading', { name: copy(locale, 'platform.title') }),
        ).toBeVisible();
        await inspect(
          page,
          theme,
          `${width}-${locale}-${theme}-platform`,
          info,
        );
        await expect(page.getByText('Maison Safran')).toHaveCount(0);
      });

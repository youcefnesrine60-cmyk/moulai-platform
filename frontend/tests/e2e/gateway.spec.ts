// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { createHash } from 'node:crypto';
import { expect, test, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import manifest from '../../brand-sources/gateway/manifest.json' with { type: 'json' };
import logos from '../../brand-sources/logo-manifest.json' with { type: 'json' };
import type { Theme } from '../../src/shared/theme';
import { checkHeader, evidenceDirectory } from './polish-checks';

/** Wait for real decoded pixels, including after a live effective-theme change. */
async function gateway(page: Page, theme: Theme): Promise<void> {
  await expect(page.locator('html')).toHaveAttribute('data-theme', theme);
  const image = page.locator(`[data-gateway="${theme}"] img`);
  await expect(image).toBeVisible();
  await expect
    .poll(() =>
      image.evaluate(
        (node: HTMLImageElement) => node.complete && node.naturalWidth > 0,
      ),
    )
    .toBe(true);
  expect(
    await image.evaluate((node: HTMLImageElement) => node.currentSrc),
  ).toContain(`/brand/gateway/${theme}-`);
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

for (const width of [1440, 1920, 834, 390, 360])
  for (const locale of ['fr', 'en', 'ar'] as const)
    for (const theme of ['light', 'dark'] as const)
      test(`Gateway ${width}px ${locale}/${theme}: approved artwork, readable controls and RTL`, async ({
        page,
      }, info) => {
        test.setTimeout(45000);
        await page.setViewportSize({
          width,
          height: width <= 390 ? 844 : 1000,
        });
        await page.emulateMedia({
          colorScheme: theme === 'light' ? 'dark' : 'light',
        });
        await page.addInitScript(
          ({ locale, theme }) => {
            localStorage.setItem('moulai.locale', locale);
            localStorage.setItem('moulai.theme', theme);
            requestAnimationFrame(() =>
              Reflect.set(
                window,
                'gatewayFirstPaint',
                document.documentElement.dataset.theme,
              ),
            );
          },
          { locale, theme },
        );
        const requested: string[] = [];
        page.on('request', (request) => {
          if (request.url().includes('/brand/gateway/'))
            requested.push(request.url());
        });
        const [response] = await Promise.all([
          page.waitForResponse((response) =>
            response.url().includes('/brand/gateway/'),
          ),
          page.goto('/access'),
        ]);
        await gateway(page, theme);
        await page.evaluate(() => document.fonts.ready);
        await expect(page.locator('html')).toHaveAttribute('lang', locale);
        await expect(page.locator('html')).toHaveAttribute(
          'dir',
          locale === 'ar' ? 'rtl' : 'ltr',
        );
        expect(
          await page.evaluate(() => Reflect.get(window, 'gatewayFirstPaint')),
        ).toBe(theme);
        expect(requested).toHaveLength(1);
        expect(requested[0]).not.toContain(
          `${theme === 'dark' ? 'light' : 'dark'}-`,
        );
        const file = new URL(response.url()).pathname.split('/').at(-1);
        const variant = manifest.sources
          .find((source) => source.theme === theme)
          ?.variants.find((entry) => entry.file === file);
        expect(variant).toBeDefined();
        expect(
          createHash('sha256')
            .update(await response.body())
            .digest('hex'),
        ).toBe(variant?.sha256);
        expect((await response.body()).length).toBeLessThan(170000);
        const measured = await page.evaluate(() => {
          const image =
            document.querySelector<HTMLImageElement>('[data-gateway] img')!;
          const logo =
            document.querySelector<HTMLImageElement>('img[alt="MoulAI™"]')!;
          const frame = logo.getBoundingClientRect();
          const entry = document.querySelector('main section')!;
          return {
            overflow: document.documentElement.scrollWidth > innerWidth,
            gatewayFit: getComputedStyle(image).objectFit,
            gatewayTransform: getComputedStyle(image).transform,
            gatewayFilter: getComputedStyle(image).filter,
            logoTransform: getComputedStyle(logo).transform,
            logoFilter: getComputedStyle(logo).filter,
            logoRatio: frame.width / frame.height,
            logoWidth: frame.width,
            logoCenter: frame.x + frame.width / 2,
            logoBacking: getComputedStyle(logo.parentElement!).backgroundColor,
            entryBackground: getComputedStyle(entry).backgroundColor,
          };
        });
        expect(measured.overflow).toBe(false);
        expect(measured.gatewayFit).toBe('cover');
        expect(measured.gatewayTransform).toBe('none');
        expect(measured.gatewayFilter).toBe('none');
        expect(measured.logoTransform).toBe('none');
        expect(measured.logoFilter).toBe('none');
        const logoSource = logos.sources.find(
          (source) => source.theme === theme,
        )!;
        expect(measured.logoRatio).toBeCloseTo(
          logoSource.width / logoSource.height,
          2,
        );
        expect(measured.logoWidth).toBeGreaterThan(240);
        expect(measured.logoCenter).toBeCloseTo(width / 2, 0);
        expect(measured.logoBacking).toBe('rgba(0, 0, 0, 0)');
        expect(measured.entryBackground).toMatch(/(?:0\.84\)|\/ 0\.84\))/);
        if (info.config.metadata['evidenceDirectory'])
          await checkHeader(page, info);
        await page.keyboard.press('Tab');
        await expect(
          page.getByRole('combobox', {
            name: /Langue de l.interface|Interface language|لغة الواجهة/,
          }),
        ).toBeFocused();
        const focus = await page
          .getByRole('combobox', {
            name: /Langue de l.interface|Interface language|لغة الواجهة/,
          })
          .evaluate((button) => getComputedStyle(button).outlineStyle);
        expect(focus).toBe('solid');
        const accessibility = await new AxeBuilder({ page })
          .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
          .analyze();
        expect(accessibility.violations).toEqual([]);
        await info.attach('gateway-measurements', {
          body: JSON.stringify({
            ...measured,
            downloaded: variant,
            axeViolations: 0,
          }),
          contentType: 'application/json',
        });
        await page.screenshot({
          path: `${evidenceDirectory(info)}/access-${width}-${locale}-${theme}.png`,
          fullPage: true,
        });
      });

test('System follows OS live; explicit preferences and the selected review profile survive changes', async ({
  page,
}) => {
  await page.emulateMedia({ colorScheme: 'dark' });
  await page.goto('/access');
  await gateway(page, 'dark');
  await page.emulateMedia({ colorScheme: 'light' });
  await gateway(page, 'light');
  await page.getByRole('combobox', { name: 'Profil de test' }).click();
  await page
    .getByRole('option', { name: 'Manager · entreprise A', exact: true })
    .click();
  await page.getByRole('combobox', { name: 'Apparence' }).click();
  await page.getByRole('option', { name: 'Sombre', exact: true }).click();
  await gateway(page, 'dark');
  await page
    .getByRole('combobox', {
      name: /Langue de l.interface|Interface language|لغة الواجهة/,
    })
    .click();
  await page.getByRole('option', { name: 'English — EN', exact: true }).click();
  await expect(
    page.getByRole('combobox', { name: 'Test profile' }),
  ).toContainText('Manager');
  await page.emulateMedia({ colorScheme: 'light' });
  await gateway(page, 'dark');
  await page.reload();
  await gateway(page, 'dark');
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  await page.getByRole('combobox', { name: 'Appearance' }).click();
  await page
    .getByRole('option', { name: 'System preference', exact: true })
    .click();
  await gateway(page, 'light');
  await page.emulateMedia({ colorScheme: 'dark' });
  await gateway(page, 'dark');
});

test('normal build stays disconnected, uses the effective Gateway and retains palette if images fail', async ({
  page,
}) => {
  await page.emulateMedia({ colorScheme: 'dark' });
  await page.goto('http://127.0.0.1:4273/access');
  await gateway(page, 'dark');
  await expect(
    page.getByRole('button', { name: 'Ouvrir la revue locale' }),
  ).toHaveCount(0);
  await expect(
    page.getByRole('button', { name: 'Continuer avec Keycloak' }),
  ).toBeDisabled();
  await page.emulateMedia({ colorScheme: 'light' });
  await gateway(page, 'light');
  await page.route('**/brand/gateway/**', (route) => route.abort());
  await page.reload();
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await expect(page.getByRole('combobox', { name: 'Apparence' })).toBeVisible();
  const accessibility = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
    .analyze();
  expect(accessibility.violations).toEqual([]);
});

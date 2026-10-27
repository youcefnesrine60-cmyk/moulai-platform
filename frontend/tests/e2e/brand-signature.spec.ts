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
import type { Locale } from '../../src/shared/access/contracts';
import type { Theme } from '../../src/shared/theme';
import logos from '../../brand-sources/logo-manifest.json' with { type: 'json' };
import { checkHeader, evidenceDirectory } from './polish-checks';

const translations = { fr, en, ar } as const;
type CopyKey = keyof typeof fr;

/** Read the real catalog while independent unit assertions lock the approved wording. */
function copy(locale: Locale, key: CopyKey): string {
  return translations[locale][key];
}

/** Verify decoded bytes, native proportions, centered signature and shared layout. */
async function brand(
  page: Page,
  locale: Locale,
  theme: Theme,
  info: TestInfo,
): Promise<void> {
  await page.evaluate(() => document.fonts.ready);
  const source = logos.sources.find((entry) => entry.theme === theme)!;
  const logo = page.locator('header img[alt="MoulAI™"]');
  await expect(logo).toHaveAttribute('src', `/brand/${source.file}`);
  await expect
    .poll(() =>
      logo.evaluate(
        (node: HTMLImageElement) => node.complete && node.naturalWidth > 0,
      ),
    )
    .toBe(true);
  const response = await page.request.get(
    new URL(`/brand/${source.file}`, page.url()).href,
  );
  expect(
    createHash('sha256')
      .update(await response.body())
      .digest('hex'),
  ).toBe(source.sha256);
  const signature = page
    .locator('header')
    .getByText(copy(locale, 'brand.tagline'), { exact: true });
  await expect(signature).toBeVisible();
  await expect(signature).toHaveAttribute(
    'dir',
    locale === 'ar' ? 'rtl' : 'ltr',
  );
  const measured = await logo.evaluate((node: HTMLImageElement) => {
    const image = node.getBoundingClientRect();
    const text = node.parentElement!.nextElementSibling!;
    const tagline = text.getBoundingClientRect();
    return {
      width: image.width,
      height: image.height,
      naturalWidth: node.naturalWidth,
      naturalHeight: node.naturalHeight,
      filter: getComputedStyle(node).filter,
      transform: getComputedStyle(node).transform,
      center: image.x + image.width / 2,
      signatureCenter: tagline.x + tagline.width / 2,
      below: tagline.top >= image.bottom,
      font: getComputedStyle(text).fontFamily,
      fontSize: parseFloat(getComputedStyle(text).fontSize),
      weight: Number(getComputedStyle(text).fontWeight),
      background: getComputedStyle(text).backgroundColor,
      border: getComputedStyle(text).borderWidth,
      radius: getComputedStyle(text).borderRadius,
      padding: getComputedStyle(text).padding,
      shadow: getComputedStyle(text).boxShadow,
      size: node.parentElement!.parentElement!.getAttribute('data-brand-size'),
    };
  });
  expect(measured.naturalWidth).toBe(source.width);
  expect(measured.naturalHeight).toBe(source.height);
  expect(measured.width / measured.height).toBeCloseTo(
    source.width / source.height,
    3,
  );
  const compact = new URL(page.url()).pathname !== '/access';
  expect(measured.size).toBe(compact ? 'compact' : 'prominent');
  expect(measured.width).toBeLessThanOrEqual(compact ? 360 : 560);
  expect(measured.filter).toBe('none');
  expect(measured.transform).toBe('none');
  expect(measured.below).toBe(true);
  expect(measured.center).toBeCloseTo(measured.signatureCenter, 0);
  expect(measured.font).toContain(
    locale === 'ar' ? 'Tajawal' : 'Sora Variable',
  );
  expect(measured.fontSize).toBeGreaterThanOrEqual(
    locale === 'ar' ? (compact ? 16 : 18) : compact ? 14 : 16,
  );
  expect(measured.weight).toBeGreaterThanOrEqual(700);
  expect(measured.background).toBe('rgba(0, 0, 0, 0)');
  expect(measured.border).toBe('0px');
  expect(measured.radius).toBe('0px');
  expect(measured.padding).toBe('0px');
  expect(measured.shadow).toBe('none');
  await expect(page.locator('[data-gateway]')).toHaveAttribute(
    'data-gateway',
    theme,
  );
  await checkHeader(page, info);
  if (compact && page.viewportSize()!.width === 1440)
    expect(
      await page
        .locator('header')
        .evaluate((node) => node.getBoundingClientRect().height),
    ).toBeLessThan(175);
  await info.attach('brand-presentation', {
    body: JSON.stringify({
      path: new URL(page.url()).pathname,
      locale,
      theme,
      ...measured,
    }),
    contentType: 'application/json',
  });
}

/** Capture the real rendered interface and a WCAG scan without contacting any service. */
async function capture(
  page: Page,
  label: string,
  info: TestInfo,
): Promise<void> {
  const accessibility = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
    .analyze();
  expect(accessibility.violations).toEqual([]);
  await info.attach(label, {
    body: JSON.stringify({ axeViolations: 0 }),
    contentType: 'application/json',
  });
  await page.screenshot({
    path: `${evidenceDirectory(info)}/${label}.png`,
    fullPage: true,
  });
  if (
    label.startsWith('1440-fr-light-') &&
    /-(access|enterprise|platform)$/.test(label)
  )
    await page
      .locator('header')
      .screenshot({ path: `${evidenceDirectory(info)}/${label}-header.png` });
}

test.beforeEach(async ({ page }) => {
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    expect(url.hostname).toBe('127.0.0.1');
    expect(['5273', '4273']).toContain(url.port);
    await route.continue();
  });
  page.on('pageerror', (error) => {
    throw error;
  });
});

for (const width of [1440, 360, 390])
  for (const locale of ['fr', 'en', 'ar'] as const)
    for (const theme of ['light', 'dark'] as const)
      test(`${width}px ${locale}/${theme}: approved access, enterprise and platform brand`, async ({
        page,
      }, info) => {
        test.setTimeout(90000);
        await page.setViewportSize({
          width,
          height: width <= 390 ? 844 : 1000,
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
        await brand(page, locale, theme, info);
        const message = page.getByRole('region', {
          name: 'Agent-as-a-Service',
        });
        for (const key of [
          'access.serviceLead',
          'access.serviceTeam',
          'access.serviceCustomers',
          'access.serviceAppointments',
          'access.serviceOrders',
          'access.serviceContinuous',
          'access.serviceVision',
        ] as const)
          await expect(
            message.getByText(copy(locale, key), { exact: true }),
          ).toBeVisible();
        expect(
          await message.evaluate((node) => getComputedStyle(node).direction),
        ).toBe(locale === 'ar' ? 'rtl' : 'ltr');
        expect(
          await message.evaluate((node) => getComputedStyle(node).fontFamily),
        ).toContain(locale === 'ar' ? 'Tajawal' : 'Sora Variable');
        await expect(message.locator('img')).toHaveCount(0);
        await expect(message.getByRole('listitem')).toHaveCount(4);
        await expect(message.locator('li svg[aria-hidden="true"]')).toHaveCount(
          4,
        );
        const capabilities = await message.locator('li').evaluateAll((nodes) =>
          nodes.map((node) => {
            const icon = node.querySelector('svg')!;
            const box = icon.getBoundingClientRect();
            return {
              width: box.width,
              height: box.height,
              stroke: getComputedStyle(icon).strokeWidth,
              background: getComputedStyle(node).backgroundColor,
              radius: getComputedStyle(node).borderRadius,
              interactive:
                node.hasAttribute('tabindex') ||
                node.querySelector('button,a,input') !== null,
              x: node.getBoundingClientRect().x,
              y: node.getBoundingClientRect().y,
            };
          }),
        );
        for (const item of capabilities) {
          expect(item.width).toBe(28);
          expect(item.height).toBe(28);
          expect(item.stroke).toBe('1.5px');
          expect(item.background).toBe('rgba(0, 0, 0, 0)');
          expect(item.radius).toBe('0px');
          expect(item.interactive).toBe(false);
        }
        if (width === 1440) {
          expect(
            new Set(capabilities.map((item) => Math.round(item.y))).size,
          ).toBe(1);
          expect(capabilities[0]!.x < capabilities[3]!.x).toBe(locale !== 'ar');
        }
        const heading = message.locator('h2');
        expect(
          await heading.evaluate((node) =>
            Number(getComputedStyle(node).fontWeight),
          ),
        ).toBeGreaterThanOrEqual(700);
        expect(
          await heading.evaluate((node) =>
            parseFloat(getComputedStyle(node).fontSize),
          ),
        ).toBeGreaterThanOrEqual(20);
        expect(
          await message.evaluate((node) =>
            getComputedStyle(node)
              .getPropertyValue('--service-surface-opacity')
              .trim(),
          ),
        ).toBe(theme === 'light' ? '80%' : '84%');
        if (width <= 390) {
          await expect(
            page.getByRole('button', { name: copy(locale, 'access.signin') }),
          ).toBeInViewport({ ratio: 1 });
          await expect(page.locator('#connection-status')).toBeInViewport({
            ratio: 1,
          });
        }
        await expect(
          page.getByRole('button', { name: copy(locale, 'access.signin') }),
        ).toBeDisabled();
        await expect(
          page.getByText(copy(locale, 'review.banner'), { exact: true }),
        ).toBeVisible();
        await capture(page, `${width}-${locale}-${theme}-access`, info);
        await message.screenshot({
          path: `${evidenceDirectory(info)}/${width}-${locale}-${theme}-service.png`,
        });
        await page
          .getByRole('button', { name: copy(locale, 'review.open') })
          .click();
        await expect(
          page.getByRole('heading', { name: copy(locale, 'companies.title') }),
        ).toBeVisible();
        await brand(page, locale, theme, info);
        await capture(page, `${width}-${locale}-${theme}-enterprise`, info);
        await page.evaluate(() => {
          history.pushState(null, '', '/platform');
          dispatchEvent(new PopStateEvent('popstate'));
        });
        await expect(
          page.getByRole('heading', {
            name: copy(locale, 'state.noAccess.title'),
          }),
        ).toBeVisible();
        await page
          .getByRole('button', { name: copy(locale, 'common.changeProfile') })
          .click();
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
        await brand(page, locale, theme, info);
        await expect(page.getByText('Maison Safran')).toHaveCount(0);
        await capture(page, `${width}-${locale}-${theme}-platform`, info);
      });

for (const width of [834, 320])
  for (const theme of ['light', 'dark'] as const)
    test(`${width}px ar/${theme}: Arabic signature and editorial section stay within bounds`, async ({
      page,
    }, info) => {
      await page.setViewportSize({ width, height: 1000 });
      await page.addInitScript(
        ({ theme }) => {
          localStorage.setItem('moulai.locale', 'ar');
          localStorage.setItem('moulai.theme', theme);
        },
        { theme },
      );
      await page.goto('/access');
      await brand(page, 'ar', theme, info);
      await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
      await capture(page, `${width}-ar-${theme}-access`, info);
    });

test('live language and System changes preserve the selected review profile and form', async ({
  page,
}, info) => {
  test.setTimeout(60000);
  await page.emulateMedia({ colorScheme: 'light' });
  await page.goto('/access');
  await page
    .getByRole('combobox', { name: copy('fr', 'review.profile') })
    .click();
  await page
    .getByRole('option', { name: copy('fr', 'profile.manager'), exact: true })
    .click();
  await page
    .locator('form')
    .evaluate((node) => node.setAttribute('data-retained-form', 'true'));
  let previous: Locale = 'fr';
  for (const locale of ['en', 'ar', 'fr'] as const) {
    await page
      .getByRole('combobox', { name: copy(previous, 'preferences.language') })
      .click();
    await page
      .getByRole('option', {
        name: { en: 'English — EN', ar: 'العربية — AR', fr: 'Français — FR' }[
          locale
        ],
      })
      .click();
    previous = locale;
    await expect(page.locator('html')).toHaveAttribute('lang', locale);
    await expect(page.locator('form[data-retained-form="true"]')).toHaveCount(
      1,
    );
    await expect(
      page.getByRole('combobox', { name: copy(locale, 'review.profile') }),
    ).toContainText(copy(locale, 'profile.manager'));
    await expect(
      page.getByText(copy(locale, 'access.serviceLead'), { exact: true }),
    ).toBeVisible();
    for (const theme of ['dark', 'light'] as const) {
      await page.emulateMedia({ colorScheme: theme });
      await expect(page.locator('html')).toHaveAttribute('data-theme', theme);
      await brand(page, locale, theme, info);
      await expect(
        page.getByRole('combobox', { name: copy(locale, 'preferences.theme') }),
      ).toContainText(copy(locale, 'theme.system'));
    }
  }
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('lang', 'fr');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
});

test('normal build exposes the approved brand and presentation without synthetic review', async ({
  page,
}, info) => {
  await page.goto('http://127.0.0.1:4273/access');
  await expect(
    page.getByRole('heading', { name: copy('fr', 'access.title') }),
  ).toBeVisible();
  await expect(
    page.getByRole('button', { name: copy('fr', 'review.open') }),
  ).toHaveCount(0);
  await expect(
    page.getByRole('button', { name: copy('fr', 'access.signin') }),
  ).toBeDisabled();
  await expect(
    page.getByRole('region', { name: 'Agent-as-a-Service' }),
  ).toHaveAccessibleDescription(copy('fr', 'access.serviceVision'));
  const theme = await page.locator('html').getAttribute('data-theme');
  expect(theme === 'light' || theme === 'dark').toBe(true);
  await brand(page, 'fr', theme as Theme, info);
  await capture(page, 'normal-build-disconnected-access', info);
});

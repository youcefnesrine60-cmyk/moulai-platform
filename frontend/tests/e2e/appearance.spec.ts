// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { expect, test, type Page, type TestInfo } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { fr } from '../../src/shared/i18n/fr';
import { en } from '../../src/shared/i18n/en';
import { ar } from '../../src/shared/i18n/ar';
import { businessFr } from '../../src/shared/i18n/business.fr';
import { businessEn } from '../../src/shared/i18n/business.en';
import { businessAr } from '../../src/shared/i18n/business.ar';
import type { Locale, ReviewProfile } from '../../src/shared/access/contracts';
import type { Theme } from '../../src/shared/theme';

const resources: Record<Locale, Readonly<Record<string, string>>> = {
  fr: { ...fr, ...businessFr },
  en: { ...en, ...businessEn },
  ar: { ...ar, ...businessAr },
};
const base = '/workspace/organizations/9101/restaurants/9201';

/** Copy lookup fails instead of silently validating a missing translation key. */
function copy(locale: Locale, key: string): string {
  const value = resources[locale][key];
  if (!value) throw new Error(`Missing ${locale}:${key}`);
  return value;
}

/** Select appearance through the actual accessible Radix control. */
async function chooseTheme(
  page: Page,
  locale: Locale,
  theme: Theme | 'system',
  dialog = false,
): Promise<void> {
  const control = dialog
    ? page
        .getByRole('dialog')
        .getByRole('combobox', { name: copy(locale, 'preferences.theme') })
    : page.getByRole('combobox', { name: copy(locale, 'preferences.theme') });
  await control.click();
  await page
    .getByRole('option', { name: copy(locale, `theme.${theme}`), exact: true })
    .click();
}

/** Open a labeled fixture profile; no real sign-in or endpoint is involved. */
async function open(
  page: Page,
  locale: Locale,
  profile: ReviewProfile = 'owner',
): Promise<void> {
  if (profile !== 'owner') {
    await page
      .getByRole('combobox', { name: copy(locale, 'review.profile') })
      .click();
    await page
      .getByRole('option', {
        name: copy(locale, `profile.${profile}`),
        exact: true,
      })
      .click();
  }
  await page.getByRole('button', { name: copy(locale, 'review.open') }).click();
  await expect(
    page.getByRole('heading', {
      name: copy(
        locale,
        profile === 'admin' ? 'platform.title' : 'companies.title',
      ),
    }),
  ).toBeVisible();
}

/** Explicit company and restaurant links preserve the approved access flow. */
async function selectRestaurant(page: Page, locale: Locale): Promise<void> {
  await page
    .getByRole('link', {
      name: new RegExp(`^${copy(locale, 'companies.open')}`),
    })
    .first()
    .click();
  await page
    .getByRole('link', {
      name: new RegExp(`^${copy(locale, 'restaurants.open')}`),
    })
    .first()
    .click();
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
}

/** In-app navigation exercises scope tampering without reloading ephemeral identity. */
async function go(page: Page, path: string): Promise<void> {
  await page.evaluate((destination) => {
    history.pushState(null, '', destination);
    dispatchEvent(new PopStateEvent('popstate'));
  }, path);
}

/** Leave through the visible navigation, including the keyboard-managed mobile drawer. */
async function leave(page: Page, locale: Locale): Promise<void> {
  const menu = page.getByRole('button', {
    name: copy(locale, 'nav.menu'),
    exact: true,
  });
  if (await menu.isVisible()) await menu.click();
  await page.getByRole('button', { name: copy(locale, 'nav.signout') }).click();
  await expect(
    page.getByRole('heading', { name: copy(locale, 'access.title') }),
  ).toBeVisible();
}

/** Record measured accessibility results and enforce responsive content bounds. */
async function check(page: Page, label: string, info: TestInfo): Promise<void> {
  await page.evaluate(() => document.fonts.ready);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  const result = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
    .analyze();
  await info.attach(label, {
    body: JSON.stringify({
      violations: result.violations,
      checkedRules: result.passes.length,
    }),
    contentType: 'application/json',
  });
  expect(result.violations).toEqual([]);
}

test.beforeEach(async ({ page }) => {
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    expect(['127.0.0.1', 'localhost']).toContain(url.hostname);
    expect(['5173', '4173']).toContain(url.port);
    await route.continue();
  });
  page.on('pageerror', (error) => {
    throw error;
  });
});

for (const locale of ['fr', 'en', 'ar'] as const)
  for (const theme of ['light', 'dark'] as const) {
    test(`${locale}/${theme}: all delivered views, roles, forms, focus and scope`, async ({
      page,
    }, info) => {
      test.setTimeout(120000);
      if (info.project.name === 'mobile')
        await page.setViewportSize({ width: 360, height: 800 });
      await page.addInitScript(
        ({ locale: language, theme: appearance }) => {
          localStorage.setItem('moulai.locale', language);
          localStorage.setItem('moulai.theme', appearance);
        },
        { locale, theme },
      );
      await page.goto('/access');
      await expect(page.locator('html')).toHaveAttribute('lang', locale);
      await expect(page.locator('html')).toHaveAttribute(
        'dir',
        locale === 'ar' ? 'rtl' : 'ltr',
      );
      await expect(page.locator('html')).toHaveAttribute('data-theme', theme);
      await check(page, 'access', info);
      await open(page, locale);
      await selectRestaurant(page, locale);
      await expect(
        page.getByRole('button', {
          name: copy(locale, 'business.editProfile'),
        }),
      ).toBeVisible();
      await go(page, `${base}/catalogue`);
      await expect(
        page.getByRole('heading', { name: copy(locale, 'business.catalogue') }),
      ).toBeVisible();
      await check(page, 'catalogue', info);
      await page.screenshot({
        path: `../artifacts/frontend-identity-validation/${info.project.name}-${locale}-${theme}-catalogue.png`,
        fullPage: true,
      });
      await page
        .getByRole('button', {
          name: copy(locale, 'business.categories'),
          exact: true,
        })
        .click();
      await page
        .getByRole('button', { name: copy(locale, 'business.addCategory') })
        .click();
      await page
        .getByRole('dialog')
        .getByRole('textbox', {
          name: copy(locale, 'business.name'),
          exact: true,
        })
        .fill('Draft · مسودة');
      await page
        .getByRole('dialog')
        .getByRole('button', { name: copy(locale, 'business.confirm') })
        .click();
      await expect(
        page.getByRole('dialog').getByRole('heading', {
          name: copy(locale, 'business.confirmTitle'),
        }),
      ).toBeVisible();
      await expect(
        page.getByRole('dialog').getByText('Draft · مسودة', { exact: true }),
      ).toBeVisible();
      await page
        .getByRole('dialog')
        .getByRole('button', { name: copy(locale, 'business.backEdit') })
        .click();
      await expect(
        page.getByRole('dialog').getByRole('textbox', {
          name: copy(locale, 'business.name'),
          exact: true,
        }),
      ).toHaveValue('Draft · مسودة');
      await page.keyboard.press('Escape');
      await page
        .getByRole('button', {
          name: copy(locale, 'business.options'),
          exact: true,
        })
        .click();
      await page
        .getByRole('button', {
          name: copy(locale, 'business.addGroup'),
          exact: true,
        })
        .click();
      await expect(
        page
          .getByRole('dialog')
          .getByRole('checkbox', { name: copy(locale, 'business.required') }),
      ).toBeVisible();
      await page.keyboard.press('Escape');
      await page
        .getByRole('button', {
          name: copy(locale, 'business.products'),
          exact: true,
        })
        .click();
      const trigger = page.getByRole('button', {
        name: copy(locale, 'business.addProduct'),
      });
      await trigger.click();
      const dialog = page.getByRole('dialog');
      await dialog
        .getByRole('textbox', {
          name: copy(locale, 'business.name'),
          exact: true,
        })
        .fill('Kept draft · مسودة');
      await dialog
        .getByRole('textbox', { name: copy(locale, 'business.price') })
        .fill('0');
      await dialog
        .getByRole('button', { name: copy(locale, 'business.confirm') })
        .click();
      await expect(
        dialog.getByText(copy(locale, 'business.invalid')),
      ).toBeVisible();
      await check(page, 'invalid-form', info);
      if (locale === 'en' && theme === 'dark') {
        await dialog.getByRole('button', { name: 'العربية' }).click();
        await chooseTheme(page, 'ar', 'light', true);
        await expect(
          dialog.getByRole('textbox', {
            name: copy('ar', 'business.name'),
            exact: true,
          }),
        ).toHaveValue('Kept draft · مسودة');
        await expect(
          dialog.getByRole('textbox', { name: copy('ar', 'business.price') }),
        ).toHaveValue('0');
        await dialog.getByRole('button', { name: 'EN' }).click();
        await chooseTheme(page, 'en', 'dark', true);
        await expect(page).toHaveURL(new RegExp(`${base}/catalogue$`));
      }
      await page.screenshot({
        path: `../artifacts/frontend-identity-validation/${info.project.name}-${locale}-${theme}-form.png`,
        fullPage: true,
      });
      await page.keyboard.press('Escape');
      await expect(trigger).toBeFocused();
      await go(page, `${base}/orders`);
      await page
        .getByRole('combobox', { name: copy(locale, 'business.orderStatus') })
        .selectOption('pending');
      await page.getByRole('link', { name: /REV-9201-001/ }).click();
      await expect(
        page.getByRole('heading', { name: copy(locale, 'business.items') }),
      ).toBeVisible();
      await check(page, 'order-detail', info);
      await page.screenshot({
        path: `../artifacts/frontend-identity-validation/${info.project.name}-${locale}-${theme}-order.png`,
        fullPage: true,
      });
      await leave(page, locale);
      await open(page, locale, 'manager');
      await expect(page.getByText('Comptoir Atlas')).toHaveCount(0);
      await selectRestaurant(page, locale);
      await expect(
        page.getByRole('button', {
          name: copy(locale, 'business.editProfile'),
        }),
      ).toBeVisible();
      await go(
        page,
        '/workspace/organizations/9102/restaurants/9203/catalogue',
      );
      await expect(
        page.getByRole('heading', {
          name: copy(locale, 'state.notFound.title'),
        }),
      ).toBeVisible();
      await leave(page, locale);
      await open(page, locale, 'employee');
      await selectRestaurant(page, locale);
      await expect(
        page.getByRole('button', {
          name: copy(locale, 'business.editProfile'),
        }),
      ).toHaveCount(0);
      await go(
        page,
        '/workspace/organizations/9101/restaurants/9202/catalogue',
      );
      await expect(
        page.getByRole('heading', { name: copy(locale, 'business.catalogue') }),
      ).toBeVisible();
      await expect(
        page.getByRole('button', { name: copy(locale, 'business.addProduct') }),
      ).toHaveCount(0);
      await go(
        page,
        '/workspace/organizations/9101/restaurants/9202/orders/920260',
      );
      await expect(
        page.getByRole('heading', { name: 'REV-9202-001' }),
      ).toBeVisible();
      await expect(
        page.getByRole('button', { name: copy(locale, 'business.editNote') }),
      ).toHaveCount(0);
      await leave(page, locale);
      await open(page, locale, 'admin');
      await check(page, 'platform', info);
      await page.screenshot({
        path: `../artifacts/frontend-identity-validation/${info.project.name}-${locale}-${theme}-platform.png`,
        fullPage: true,
      });
      await expect(page.getByText('Maison Safran')).toHaveCount(0);
      await go(page, '/workspace');
      await expect(
        page.getByRole('heading', {
          name: copy(locale, 'state.noAccess.title'),
        }),
      ).toBeVisible();
      await check(page, 'denied', info);
      await expect(page.locator('html')).toHaveAttribute('data-theme', theme);
    });

    test(`${locale}/${theme}: normal build first frame and persisted preferences`, async ({
      page,
    }) => {
      await page.emulateMedia({
        colorScheme: theme === 'dark' ? 'light' : 'dark',
      });
      await page.addInitScript(
        ({ locale: language, theme: appearance }) => {
          localStorage.setItem('moulai.locale', language);
          localStorage.setItem('moulai.theme', appearance);
          requestAnimationFrame(() =>
            Reflect.set(window, 'firstAppearance', {
              theme: document.documentElement.dataset.theme,
              background: getComputedStyle(document.documentElement)
                .backgroundColor,
            }),
          );
        },
        { locale, theme },
      );
      await page.goto('http://127.0.0.1:4173/access');
      await expect(
        page.getByRole('heading', { name: copy(locale, 'access.title') }),
      ).toBeVisible();
      expect(
        await page.evaluate(() => Reflect.get(window, 'firstAppearance')),
      ).toEqual({
        theme,
        background: theme === 'dark' ? 'rgb(11, 19, 36)' : 'rgb(230, 246, 227)',
      });
      await expect(
        page.getByRole('button', { name: copy(locale, 'access.signin') }),
      ).toBeDisabled();
      await expect(
        page.getByRole('button', { name: copy(locale, 'review.open') }),
      ).toHaveCount(0);
      await page.reload();
      await expect(page.locator('html')).toHaveAttribute('data-theme', theme);
      await expect(page.locator('html')).toHaveAttribute('lang', locale);
    });
  }

test('system preference, explicit override, live OS change and cross-tab synchronization', async ({
  page,
  context,
}) => {
  await page.emulateMedia({ colorScheme: 'dark' });
  await page.goto('/access');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await chooseTheme(page, 'fr', 'light');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  const second = await context.newPage();
  await second.goto('http://127.0.0.1:5173/access');
  await expect(second.locator('html')).toHaveAttribute('data-theme', 'light');
  await chooseTheme(page, 'fr', 'dark');
  await expect(second.locator('html')).toHaveAttribute('data-theme', 'dark');
  await chooseTheme(page, 'fr', 'system');
  await page.emulateMedia({ colorScheme: 'light' });
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await page.emulateMedia({ colorScheme: 'dark' });
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await second.close();
});

test('blocked storage preserves system theme and working language/theme controls', async ({
  page,
}) => {
  await page.emulateMedia({ colorScheme: 'dark' });
  await page.addInitScript(() => {
    Object.defineProperty(window, 'localStorage', {
      get() {
        throw new DOMException('Denied', 'SecurityError');
      },
    });
  });
  await page.goto('/access');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await chooseTheme(page, 'fr', 'light');
  await page.getByRole('button', { name: 'EN' }).click();
  await expect(
    page.getByRole('heading', { name: 'Welcome to your workspace.' }),
  ).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
});

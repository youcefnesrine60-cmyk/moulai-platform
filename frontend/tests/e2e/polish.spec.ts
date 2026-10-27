// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { fr } from '../../src/shared/i18n/fr';
import { en } from '../../src/shared/i18n/en';
import { ar } from '../../src/shared/i18n/ar';
import { businessFr } from '../../src/shared/i18n/business.fr';
import { businessEn } from '../../src/shared/i18n/business.en';
import { businessAr } from '../../src/shared/i18n/business.ar';
import type { Locale } from '../../src/shared/access/contracts';
import { checkHeader, evidenceDirectory } from './polish-checks';

const translations: Record<Locale, Readonly<Record<string, string>>> = {
  fr: { ...fr, ...businessFr },
  en: { ...en, ...businessEn },
  ar: { ...ar, ...businessAr },
};

/** Fail explicitly if a tested visible label is absent from the real catalog. */
function copy(locale: Locale, key: string): string {
  const value = translations[locale][key];
  if (!value) throw new Error(`Missing ${locale}:${key}`);
  return value;
}

for (const width of [1440, 1101, 834, 360, 320]) {
  test(`${width}px: keyboard language menus preserve a draft, context and System preference`, async ({
    page,
  }, info) => {
    test.setTimeout(90000);
    await page.setViewportSize({ width, height: 1000 });
    await page.route('**/*', async (route) => {
      const url = new URL(route.request().url());
      expect(url.hostname).toBe('127.0.0.1');
      expect(url.port).toBe('5273');
      await route.continue();
    });
    page.on('pageerror', (error) => {
      throw error;
    });
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.goto('/access');
    await page.getByRole('button', { name: copy('fr', 'review.open') }).click();
    await page
      .getByRole('link', {
        name: new RegExp(`^${copy('fr', 'companies.open')}`),
      })
      .first()
      .click();
    await page
      .getByRole('link', {
        name: new RegExp(`^${copy('fr', 'restaurants.open')}`),
      })
      .first()
      .click();
    const path = '/workspace/organizations/9101/restaurants/9201/catalogue';
    await page.evaluate((destination) => {
      history.pushState(null, '', destination);
      dispatchEvent(new PopStateEvent('popstate'));
    }, path);
    await page
      .getByRole('button', { name: copy('fr', 'business.addProduct') })
      .click();
    const dialog = page.getByRole('dialog');
    await dialog
      .getByRole('textbox', { name: copy('fr', 'business.name'), exact: true })
      .fill('Draft · مسودة');
    await dialog
      .getByRole('textbox', { name: copy('fr', 'business.price') })
      .fill('0');
    await dialog
      .getByRole('button', { name: copy('fr', 'business.confirm') })
      .click();
    // Wait for validation focus before keyboard navigation; RHF schedules error focus.
    const invalidPrice = dialog.getByRole('textbox', {
      name: copy('fr', 'business.price'),
    });
    await expect(invalidPrice).toHaveAttribute('aria-invalid', 'true');
    await expect(invalidPrice).toBeFocused();
    let current: Locale = 'fr';
    for (const locale of ['en', 'ar', 'fr'] as const) {
      const language = dialog.getByRole('combobox', {
        name: copy(current, 'preferences.language'),
      });
      await language.press('Enter');
      await expect(page.getByRole('listbox')).toBeVisible();
      await page.keyboard.press('Home');
      await expect(
        page.getByRole('option', { name: 'Français — FR' }),
      ).toBeFocused();
      const labels = ['Français — FR', 'English — EN', 'العربية — AR'];
      for (let index = 0; index < ['fr', 'en', 'ar'].indexOf(locale); index++) {
        await page.keyboard.press('ArrowDown');
        await expect(
          page.getByRole('option', { name: labels[index + 1]! }),
        ).toBeFocused();
      }
      await expect(
        page.getByRole('option', {
          name: { fr: 'Français — FR', en: 'English — EN', ar: 'العربية — AR' }[
            locale
          ],
        }),
      ).toBeFocused();
      await page.keyboard.press('Enter');
      current = locale;
      await expect(page.locator('html')).toHaveAttribute('lang', locale);
      await expect(page.locator('html')).toHaveAttribute(
        'dir',
        locale === 'ar' ? 'rtl' : 'ltr',
      );
      await expect(
        dialog.getByRole('combobox', {
          name: copy(locale, 'preferences.language'),
        }),
      ).toContainText(locale.toUpperCase());
      await expect(
        dialog.getByRole('textbox', {
          name: copy(locale, 'business.name'),
          exact: true,
        }),
      ).toHaveValue('Draft · مسودة');
      await expect(
        dialog.getByRole('textbox', { name: copy(locale, 'business.price') }),
      ).toHaveValue('0');
      await expect(page).toHaveURL(new RegExp(`${path}$`));
      for (const theme of ['light', 'dark'] as const) {
        await page.emulateMedia({ colorScheme: theme });
        await expect(page.locator('html')).toHaveAttribute('data-theme', theme);
        await expect(
          dialog.getByRole('combobox', {
            name: copy(locale, 'preferences.theme'),
          }),
        ).toContainText(copy(locale, 'theme.system'));
        const result = await new AxeBuilder({ page })
          .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
          .analyze();
        expect(result.violations).toEqual([]);
        await info.attach(`${locale}-${theme}-draft`, {
          body: JSON.stringify({ axeViolations: 0 }),
          contentType: 'application/json',
        });
      }
    }
    await page.keyboard.press('Escape');
    await expect(dialog).toHaveCount(0);
    await checkHeader(page, info);
    await page.screenshot({
      path: `${evidenceDirectory(info)}/${width}-keyboard-context.png`,
      fullPage: true,
    });
    await page.reload();
    await expect(page.locator('html')).toHaveAttribute('lang', 'fr');
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  });
}

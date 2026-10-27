import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { fr } from '../../src/shared/i18n/fr';
import { en } from '../../src/shared/i18n/en';
import { ar } from '../../src/shared/i18n/ar';
import { officeFr } from '../../src/shared/i18n/office.fr';
import { officeEn } from '../../src/shared/i18n/office.en';
import { officeAr } from '../../src/shared/i18n/office.ar';

const copies = {
  fr: { ...fr, ...officeFr },
  en: { ...en, ...officeEn },
  ar: { ...ar, ...officeAr },
};
const base = '/workspace/organizations/9101/restaurants/9201';
async function navigate(page: Page, path: string) {
  await page.evaluate((destination) => {
    history.pushState(null, '', destination);
    dispatchEvent(new PopStateEvent('popstate'));
  }, path);
}
async function capture(page: Page, label: string) {
  await page.evaluate(() => document.fonts.ready);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  const scan = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
    .analyze();
  expect(scan.violations).toEqual([]);
  await page.screenshot({
    path: `../artifacts/frontend-office-extension/${label}.png`,
    fullPage: true,
  });
}
test.beforeEach(async ({ page }) => {
  await page.route('**/*', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    expect(url.hostname).toBe('127.0.0.1');
    expect(['5473', '4473']).toContain(url.port);
    expect(['GET', 'HEAD']).toContain(request.method());
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
      test(`zero-cost extended workflows ${width}/${locale}/${theme}`, async ({
        page,
      }) => {
        const copy = copies[locale];
        const label = `${width}-${locale}-${theme}`;
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
        await navigate(page, `${base}/reports`);
        await expect(
          page.getByRole('figure', { name: copy['office.orderChart'] }),
        ).toBeVisible();
        await expect(
          page.getByRole('figure', { name: copy['office.categoryChart'] }),
        ).toBeVisible();
        await expect(page.locator('html')).toHaveAttribute(
          'dir',
          locale === 'ar' ? 'rtl' : 'ltr',
        );
        await expect(page.locator('html')).toHaveAttribute('data-theme', theme);
        await capture(page, `${label}-charts`);
        await navigate(page, `${base}/billing`);
        const checkout = page.getByRole('form', {
          name: copy['office.offerPreview'],
        });
        await checkout
          .getByRole('combobox', { name: copy['office.cycle'] })
          .selectOption('yearly');
        await expect(page.getByText('SYNTHETIC-CCP-NOT-PAYABLE')).toBeVisible();
        await checkout
          .getByRole('combobox', { name: copy['office.method'] })
          .selectOption('baridimob');
        await expect(page.getByText('SYNTHETIC-RIP-NOT-PAYABLE')).toBeVisible();
        await checkout
          .getByRole('button', { name: copy['office.simulateCheckout'] })
          .click();
        await expect(checkout.getByRole('status')).toHaveText(
          copy['office.checkoutPreview'],
        );
        await expect(
          page.getByRole('button', {
            name: copy['office.checkout'],
            exact: true,
          }),
        ).toBeDisabled();
        await capture(page, `${label}-subscription-instructions`);
        await page.goto('/access');
        await page
          .getByRole('combobox', { name: copy['review.profile'] })
          .click();
        await page
          .getByRole('option', { name: copy['profile.admin'], exact: true })
          .click();
        await page
          .getByRole('button', { name: copy['review.open'], exact: true })
          .click();
        await expect(
          page.getByRole('heading', { name: copy['platform.title'], level: 1 }),
        ).toBeVisible();
        await navigate(page, '/platform/receipts');
        await page.locator('summary').click();
        const form = page.getByRole('form', {
          name: copy['office.verification'],
        });
        await form
          .getByRole('button', { name: copy['office.simulateReview'] })
          .click();
        await expect(form.getByRole('alert')).toHaveText(
          copy['office.simulationError'],
        );
        const hypothesis = form.getByRole('checkbox', {
          name: copy['office.fundsHypothesis'],
        });
        await hypothesis.focus();
        await page.keyboard.press('Space');
        await expect(hypothesis).toBeChecked();
        await form
          .getByRole('textbox', { name: copy['office.bankReference'] })
          .fill('BILLING-REVIEW-9201');
        await form
          .getByRole('textbox', { name: copy['office.receivedAmount'] })
          .fill('2500.00');
        await form
          .getByRole('combobox', { name: copy['office.currency'] })
          .selectOption('DZD');
        await form
          .getByRole('textbox', { name: copy['office.note'] })
          .fill('Synthetic verification only — aucun fonds réel');
        await form
          .getByRole('button', { name: copy['office.simulateReview'] })
          .focus();
        await page.keyboard.press('Enter');
        await expect(form.getByRole('status')).toHaveText(
          copy['office.simulationApproved'],
        );
        await expect(
          page.getByRole('button', {
            name: copy['office.approve'],
            exact: true,
          }),
        ).toBeDisabled();
        await expect(
          page
            .locator('article')
            .first()
            .getByText(copy['office.pending'], { exact: true }),
        ).toHaveCount(3);
        await capture(page, `${label}-verification-approval`);
        await form
          .getByRole('combobox', { name: copy['office.decision'] })
          .selectOption('reject');
        await form
          .getByRole('button', { name: copy['office.simulateReview'] })
          .click();
        await expect(form.getByRole('status')).toHaveText(
          copy['office.simulationRejected'],
        );
        await expect(
          page
            .locator('article')
            .first()
            .getByText(copy['office.pending'], { exact: true }),
        ).toHaveCount(3);
        await capture(page, `${label}-verification-rejection`);
      });

test('System follows the OS while a localized subscription preview retains its selection', async ({
  page,
}) => {
  await page.emulateMedia({ colorScheme: 'light' });
  await page.addInitScript(() => {
    localStorage.setItem('moulai.theme', 'system');
  });
  await page.goto('/access');
  await page
    .getByRole('button', { name: fr['review.open'], exact: true })
    .click();
  await navigate(page, `${base}/billing`);
  const form = page.getByRole('form', {
    name: officeFr['office.offerPreview'],
  });
  await form
    .getByRole('combobox', { name: officeFr['office.cycle'] })
    .selectOption('yearly');
  await form
    .getByRole('button', { name: officeFr['office.simulateCheckout'] })
    .click();
  await page
    .getByRole('combobox', { name: fr['preferences.language'] })
    .click();
  await page.getByRole('option', { name: 'العربية — AR', exact: true }).click();
  await page.emulateMedia({ colorScheme: 'dark' });
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
  await expect(
    page
      .getByRole('form', { name: officeAr['office.offerPreview'] })
      .getByRole('combobox', { name: officeAr['office.cycle'] }),
  ).toHaveValue('yearly');
  await expect(page.getByRole('status')).toHaveText(
    officeAr['office.checkoutPreview'],
  );
});

test('normal build stays disconnected for the extended workflows', async ({
  page,
}) => {
  await page.goto(`http://127.0.0.1:4473${base}/billing`);
  await expect(
    page.getByRole('heading', { name: fr['access.title'] }),
  ).toBeVisible();
  await expect(
    page.getByRole('button', { name: fr['review.open'] }),
  ).toHaveCount(0);
  await expect(
    page.getByText(/SYNTHETIC-CCP-NOT-PAYABLE|SYNTHETIC-RIP-NOT-PAYABLE/),
  ).toHaveCount(0);
});

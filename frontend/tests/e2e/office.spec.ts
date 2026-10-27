import { test, expect, type Page, type TestInfo } from '@playwright/test';
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
async function capture(page: Page, label: string, info: TestInfo) {
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
    path: `../artifacts/frontend-office-validation/${label}.png`,
    fullPage: true,
  });
  await info.attach(label, {
    body: JSON.stringify({ axeViolations: 0, overflow: false }),
    contentType: 'application/json',
  });
}
test.beforeEach(async ({ page }) => {
  await page.route('**/*', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    expect(url.hostname).toBe('127.0.0.1');
    expect(['5373', '4373']).toContain(url.port);
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
      test(`reports, billing and administration ${width}/${locale}/${theme}`, async ({
        page,
      }, info) => {
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
        await navigate(page, `${base}/reports`);
        await expect(
          page.getByRole('heading', { name: copy['nav.reports'], level: 1 }),
        ).toBeVisible();
        await expect(
          page.getByText(copy['office.unavailable'], { exact: true }),
        ).toHaveCount(2);
        await expect(page.locator('html')).toHaveAttribute(
          'dir',
          locale === 'ar' ? 'rtl' : 'ltr',
        );
        await expect(page.locator('html')).toHaveAttribute('data-theme', theme);
        await capture(page, `${width}-${locale}-${theme}-reports`, info);
        await navigate(page, `${base}/billing`);
        await expect(
          page.getByRole('heading', { name: copy['nav.billing'], level: 1 }),
        ).toBeVisible();
        await expect(
          page.getByRole('heading', { name: /920101/ }),
        ).toBeVisible();
        await capture(page, `${width}-${locale}-${theme}-billing`, info);
        await page
          .locator('summary')
          .filter({ hasText: copy['office.localDraft'] })
          .click();
        await page
          .getByLabel(copy['office.reference'], { exact: true })
          .fill('SYNTHETIC-ONLY-001');
        await page
          .getByLabel(copy['office.file'], { exact: true })
          .setInputFiles({
            name: 'review.pdf',
            mimeType: 'application/pdf',
            buffer: Buffer.from('synthetic file, no upload'),
          });
        await page
          .getByRole('button', { name: copy['office.preview'] })
          .click();
        await expect(page.getByRole('status')).toHaveText(
          copy['office.previewReady'],
        );
        await expect(
          page.getByRole('button', { name: copy['office.send'] }),
        ).toBeDisabled();
        await capture(
          page,
          `${width}-${locale}-${theme}-receipt-preview`,
          info,
        );
        // Full reload starts another fresh synthetic RAM session, without retaining a real identity.
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
        for (const section of ['requests', 'receipts', 'audit'] as const) {
          await navigate(page, `/platform/${section}`);
          await expect(
            page.getByRole('heading', {
              name: copy[`nav.${section}`],
              level: 1,
            }),
          ).toBeVisible();
          await page.locator('summary').click();
          if (section !== 'audit')
            await expect(
              page.getByRole('button', { name: copy['office.approve'] }),
            ).toBeDisabled();
          await capture(
            page,
            `${width}-${locale}-${theme}-platform-${section}`,
            info,
          );
        }
      });

test('normal build has neither review access nor financial fixture data', async ({
  page,
}) => {
  await page.goto(`http://127.0.0.1:4373${base}/billing`);
  await expect(
    page.getByRole('heading', { name: fr['access.title'] }),
  ).toBeVisible();
  await expect(
    page.getByRole('button', { name: fr['review.open'] }),
  ).toHaveCount(0);
  await expect(page.getByText(/BILLING-REVIEW-|PAYMENT-REVIEW-/)).toHaveCount(
    0,
  );
});

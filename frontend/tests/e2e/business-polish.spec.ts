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
const before = process.env.MOULAI_POLISH_STAGE === 'before';
const base = '/workspace/organizations/9101/restaurants/9201';
async function navigate(page: Page, path: string) {
  await page.evaluate((destination) => {
    history.pushState(null, '', destination);
    dispatchEvent(new PopStateEvent('popstate'));
  }, path);
}
async function capture(page: Page, label: string) {
  await page.evaluate(() => document.fonts.ready);
  await page.locator('img').evaluateAll(async (images) => {
    await Promise.all(
      images.map((img) =>
        (img as HTMLImageElement).decode().catch(() => undefined),
      ),
    );
  });
  if (!before) {
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    const scan = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
      .analyze();
    expect(scan.violations).toEqual([]);
  }
  await page.screenshot({
    path: `../artifacts/frontend-business-polish/${before ? 'before' : 'after'}-${label}.png`,
    fullPage: true,
  });
}
test.beforeEach(async ({ page }) => {
  await page.route('**/*', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    expect(url.hostname).toBe('127.0.0.1');
    expect(url.port).toBe('5573');
    expect(['GET', 'HEAD']).toContain(request.method());
    expect(url.pathname).not.toMatch(/^\/api(?:\/|$)/);
    await route.continue();
  });
  page.on('pageerror', (error) => {
    throw error;
  });
});

for (const width of [1440, 320, 360, 390])
  for (const locale of ['fr', 'en', 'ar'] as const)
    for (const theme of ['light', 'dark'] as const)
      test(`${before ? 'baseline' : 'polished'} reports and billing ${width}/${locale}/${theme}`, async ({
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
        const orders = page.getByRole('figure', {
          name: copy['office.orderChart'],
        });
        await expect(orders).toBeVisible();
        await expect(
          page.getByRole('figure', { name: copy['office.categoryChart'] }),
        ).toBeVisible();
        if (!before) {
          await expect(
            page.locator('[data-metric-state="unavailable"]'),
          ).toHaveCount(2);
          const typography = await page
            .locator('[data-metric-state="unavailable"]')
            .evaluateAll((nodes) =>
              nodes.map((n) => {
                const s = getComputedStyle(n);
                return {
                  break: s.wordBreak,
                  wrap: s.overflowWrap,
                  hyphens: s.hyphens,
                  overflow: n.scrollWidth > n.clientWidth,
                };
              }),
            );
          for (const style of typography)
            expect(style).toEqual({
              break: 'normal',
              wrap: 'normal',
              hyphens: 'none',
              overflow: false,
            });
          const splitWords = await page
            .locator('[data-metric-state="unavailable"]')
            .evaluateAll((nodes) =>
              nodes.flatMap((element) => {
                const text = element.firstChild;
                if (!text || text.nodeType !== Node.TEXT_NODE)
                  return ['missing-text'];
                const value = text.textContent ?? '';
                return Array.from(value.matchAll(/\S+/gu))
                  .filter((match) => {
                    const range = document.createRange();
                    range.setStart(text, match.index);
                    range.setEnd(text, match.index + match[0].length);
                    return (
                      new Set(
                        Array.from(range.getClientRects(), (rect) =>
                          Math.round(rect.top),
                        ),
                      ).size > 1
                    );
                  })
                  .map((match) => match[0]);
              }),
            );
          expect(splitWords).toEqual([]);
          const widths = await orders
            .locator('[data-proportion]')
            .evaluateAll((nodes) =>
              nodes.map((n) => Number(n.getAttribute('data-proportion'))),
            );
          expect(widths).toEqual(Array(8).fill(12.5));
          const categories = await page
            .getByRole('figure', { name: copy['office.categoryChart'] })
            .locator('[data-proportion]')
            .evaluateAll((nodes) =>
              nodes.map((n) => Number(n.getAttribute('data-proportion'))),
            );
          expect(categories[0]).toBeCloseTo(200 / 3);
          expect(categories[1]).toBeCloseTo(100 / 3);
        }
        await capture(page, `${label}-reports`);
        await navigate(page, `${base}/billing`);
        await expect(
          page.getByRole('heading', { name: /920101/ }),
        ).toBeVisible();
        await expect(
          page.getByRole('form', { name: copy['office.offerPreview'] }),
        ).toBeVisible();
        if (!before) {
          const row = page.locator('[data-payment-row]').first();
          expect(
            await row.evaluate((n) => n.getBoundingClientRect().height),
          ).toBeLessThan(width >= 1000 ? 270 : 420);
          await expect(
            row.getByText('BILLING-REVIEW-9201', { exact: true }),
          ).toBeVisible();
          await expect(
            row.getByText(copy['office.pending'], { exact: true }),
          ).toHaveCount(2);
          await expect(row.locator('details')).not.toHaveAttribute('open');
          await expect(row.getByRole('textbox')).toHaveCount(0);
        }
        await capture(page, `${label}-billing`);
      });

if (!before)
  test('keyboard receipt disclosure and System preserve the localized billing draft', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 320, height: 1000 });
    await page.emulateMedia({ colorScheme: 'light' });
    await page.addInitScript(() => {
      localStorage.setItem('moulai.theme', 'system');
      localStorage.setItem('moulai.locale', 'fr');
    });
    await page.goto('/access');
    await page
      .getByRole('button', { name: fr['review.open'], exact: true })
      .click();
    await navigate(page, `${base}/billing`);
    const row = page.locator('[data-payment-row]').first();
    await row.locator('summary').focus();
    await page.keyboard.press('Enter');
    await expect(row.locator('details')).toHaveAttribute('open');
    await row
      .getByRole('textbox', { name: officeFr['office.reference'] })
      .fill('SYNTHETIC-LOCAL-DRAFT');
    await page
      .getByRole('combobox', { name: officeFr['office.status'] })
      .selectOption('pending');
    await page
      .getByRole('combobox', { name: fr['preferences.language'] })
      .click();
    await page
      .getByRole('option', { name: 'العربية — AR', exact: true })
      .click();
    await page.emulateMedia({ colorScheme: 'dark' });
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
    await expect(
      row.getByRole('textbox', { name: officeAr['office.reference'] }),
    ).toHaveValue('SYNTHETIC-LOCAL-DRAFT');
    await expect(
      page.getByRole('combobox', { name: officeAr['office.status'] }),
    ).toHaveValue('pending');
    await row.getByLabel(officeAr['office.file']).setInputFiles({
      name: 'test.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('synthetic file; never transmitted'),
    });
    await row.getByRole('button', { name: officeAr['office.preview'] }).click();
    await expect(row.getByRole('status')).toHaveText(
      officeAr['office.previewReady'],
    );
    await expect(
      row.getByRole('button', { name: officeAr['office.send'] }),
    ).toBeDisabled();
    await expect(
      row.getByText(officeAr['office.pending'], { exact: true }),
    ).toHaveCount(2);
    await capture(page, '320-ar-system-dark-receipt-preview');
    await navigate(page, `${base}/reports`);
    await expect(
      page.getByRole('figure', { name: officeAr['office.orderChart'] }),
    ).toBeVisible();
    await capture(page, '320-ar-system-dark-reports');
  });

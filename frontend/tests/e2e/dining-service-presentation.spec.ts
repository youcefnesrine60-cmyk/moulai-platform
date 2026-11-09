// MoulAI™ — simulated reads are labelled; live reviews do not mock business successes.
import { installManualThemeFixture } from './manualThemeFixture';
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { openPresentationCase } from './diningPresentationHarness';
import { diningPresentationFixture } from '../fixtures/diningPresentation';
import { fr } from '../../src/shared/i18n/fr';
const output = '../artifacts/dining-qr-staff-20261105';
for (const locale of ['fr', 'en', 'ar'] as const)
  for (const theme of ['light', 'dark'] as const)
    for (const width of [1440, 390])
      test(`enlarged identity ${locale}/${theme}/${width}`, async ({
        page,
      }) => {
        await page.setViewportSize({ width, height: 1000 });
        await openPresentationCase(
          page,
          diningPresentationFixture(locale),
          undefined,
          { locale, theme },
        );
        await page.evaluate(() => document.fonts.ready);
        const header = page.locator('main > header'),
          brand = header.locator('[data-brand-size]');
        const h = (await header.boundingBox())!,
          b = (await brand.boundingBox())!;
        expect(Math.abs(b.x + b.width / 2 - h.x - h.width / 2)).toBeLessThan(2);
        const image = brand.locator('img'),
          size = (await image.boundingBox())!;
        expect(size.width).toBeGreaterThan(width === 1440 ? 330 : 270);
        expect(size.width / size.height).toBeCloseTo(3, 1);
        const tagline = brand.locator(':scope > span').last();
        expect(
          await tagline.evaluate((el) => el.scrollWidth <= el.clientWidth),
        ).toBe(true);
        expect(
          await tagline.evaluate(
            (el) =>
              el.getBoundingClientRect().height <=
              parseFloat(getComputedStyle(el).lineHeight) * 1.1,
          ),
        ).toBe(true);
        expect(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
        ).toBe(true);
        await expect(page.locator('html')).toHaveAttribute(
          'dir',
          locale === 'ar' ? 'rtl' : 'ltr',
        );
        expect(
          (
            await new AxeBuilder({ page })
              .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
              .analyze()
          ).violations,
        ).toEqual([]);
        await page.evaluate(() => {
          const p = document.createElement('p');
          p.textContent =
            'PRESENTATION FIXTURE — HTTP reads simulated; no business writes';
          p.style.cssText = 'background:#0b1424;color:white;padding:12px';
          document.body.prepend(p);
        });
        await page.screenshot({
          path: `${output}/identity-${locale}-${theme}-${width}.png`,
          fullPage: true,
        });
      });
test('synthetic review renders its real time-only projection', async ({
  page,
}) => {
  await page.addInitScript(() => {
    localStorage.setItem('moulai.locale', 'fr');
    localStorage.setItem('moulai.theme', 'light');
  });
  await page.goto('http://127.0.0.1:5173/access');
  await page
    .getByRole('button', { name: fr['review.open'], exact: true })
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
  await page
    .locator('select')
    .filter({ has: page.locator('option[value="920101"]') })
    .selectOption('920101');
  await expect(page.getByTestId('operational-board')).toBeVisible();
  await expect(page.locator('[data-table-card]').first()).toBeVisible();
  await expect(page.getByTestId('render-recovery')).toHaveCount(0);
  await page.screenshot({
    path: `${output}/planning-synthetic-fixed.png`,
    fullPage: true,
  });
});
test('persisted local review reads actual dates without mock responses', async ({
  page,
}) => {
  await page.addInitScript(() => localStorage.setItem('moulai.locale', 'fr'));
  await page.goto('/dining-local');
  const settings = page.getByTestId('session-settings');
  if ((await settings.getAttribute('open')) === null)
    await settings.locator('summary').click();
  await settings.locator('[name="actor"]').selectOption('owner');
  await settings
    .getByRole('button', { name: 'Ouvrir cette session locale', exact: true })
    .click();
  await settings.locator('[name="branch"]').selectOption('7000300');
  await expect(page.getByTestId('operational-board')).toBeVisible();
  await expect(page.getByTestId('render-recovery')).toHaveCount(0);
  await page.screenshot({
    path: `${output}/planning-postgres-fixed.png`,
    fullPage: true,
  });
});
test('malformed server planning is contained, with diagnostic and explicit retry', async ({
  page,
}) => {
  const f = diningPresentationFixture('fr');
  await openPresentationCase(page, f);
  const claim = f.planning[0]!.claims[0]!;
  const original = claim.start;
  claim.start = 'invalid-date';
  await page.getByRole('button', { name: 'Actualiser', exact: true }).click();
  await expect(page.getByTestId('render-recovery')).toBeVisible();
  await expect(page.getByTestId('physical-badge')).toHaveCount(0);
  await expect(page.getByTestId('render-recovery')).toContainText('UI-');
  await page.screenshot({
    path: `${output}/date-recovery.png`,
    fullPage: true,
  });
  claim.start = original;
  await page.getByRole('button', { name: 'Actualiser', exact: true }).click();
  await page.getByRole('button', { name: 'Réessayer', exact: true }).click();
  await expect(page.getByTestId('table-card-1')).toBeVisible();
});

// Visual fixtures request a manual choice; opening policy is checked independently.
test.beforeEach(async ({ page }) => installManualThemeFixture(page));

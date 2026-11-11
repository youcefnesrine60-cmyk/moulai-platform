// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { openPresentationCase } from './diningPresentationHarness';
import { diningPresentationFixture } from '../fixtures/diningPresentation';
const output = '../artifacts/dining-final-rehearsal-20261104';
for (const locale of ['fr', 'en', 'ar'] as const)
  for (const theme of ['light', 'dark'] as const)
    for (const width of [1440, 390])
      test(`final visual ${locale}/${theme}/${width}`, async ({ page }) => {
        await page.setViewportSize({ width, height: 1000 });
        await openPresentationCase(
          page,
          diningPresentationFixture(locale),
          undefined,
          { locale, theme },
        );
        const header = page.locator('main > header');
        const brand = header.locator('[data-brand-size]');
        const container = await header.boundingBox();
        const box = await brand.boundingBox();
        expect(container).not.toBeNull();
        expect(box).not.toBeNull();
        expect(
          Math.abs(
            box!.x + box!.width / 2 - container!.x - container!.width / 2,
          ),
        ).toBeLessThan(2);
        expect(container!.height).toBeLessThan(210);
        const artwork = brand.locator('img');
        await expect(artwork).toHaveAttribute(
          'src',
          theme === 'dark'
            ? '/brand/moulai-logo-dark-approved-20261111.png'
            : '/brand/moulai-logo-light01.png',
        );
        const size = await artwork.boundingBox();
        expect(size!.width / size!.height).toBeCloseTo(3, 1);
        await expect(page.locator('html')).toHaveAttribute(
          'dir',
          locale === 'ar' ? 'rtl' : 'ltr',
        );
        await expect(
          page.getByTestId('table-card-1').getByTestId('planning-full'),
        ).toBeVisible();
        const cards = page.locator('[data-table-card]');
        expect(
          await cards.evaluateAll((elements) =>
            Math.max(
              ...elements.map(
                (element) => element.getBoundingClientRect().height,
              ),
            ),
          ),
        ).toBeLessThan(900);
        await page.getByTestId('table-card-2').locator('footer button').click();
        const panel = page.getByTestId('table-actions');
        await expect(panel).toContainText('T02');
        await expect(
          panel.locator('form[data-operation="arrival"]'),
        ).toHaveCount(0);
        await expect(
          panel.locator('form[data-operation="physical"] [name="occupation"]'),
        ).toHaveValue('21');
        const physical = panel.locator('form[data-operation="physical"]');
        if ((await physical.locator('..').getAttribute('open')) === null)
          await physical.locator('..').locator('summary').click();
        await expect(physical.locator('button[type="submit"]')).toBeVisible();
        await expect(
          panel.locator('form[data-operation="extend"] [name="occupation"]'),
        ).toHaveValue('21');
        await page.getByTestId('table-card-1').locator('footer button').focus();
        await page.keyboard.press('Enter');
        await expect(panel).toContainText('T01');
        const arrival = panel.locator('form[data-operation="arrival"]');
        if ((await arrival.locator('..').getAttribute('open')) === null)
          await arrival.locator('..').locator('summary').click();
        expect(
          await page.locator('select[multiple][name="tables"]').count(),
        ).toBe(0);
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
        await page.evaluate(() => {
          const notice = document.createElement('p');
          notice.textContent =
            'VISUAL FIXTURE — HTTP reads simulated / données de présentation ; no business writes';
          notice.style.cssText = 'background:#0b1324;color:white;padding:12px';
          document.body.prepend(notice);
        });
        await page.screenshot({
          path: `${output}/final-${locale}-${theme}-${width}.png`,
          fullPage: true,
        });
      });

test('device schedule, ignored branch timezone and manual priority preserve the form draft', async ({
  page,
}) => {
  await page.clock.install({ time: new Date('2026-11-03T06:58:00Z') });
  await page.clock.pauseAt(new Date('2026-11-03T06:59:59Z'));
  const fixture = diningPresentationFixture('fr');
  fixture.workspace.policy!.timezone = 'UTC';
  fixture.session.scopes.push({
    ...fixture.session.scopes[0]!,
    branch_id: 301,
    branch_name: 'Second simulated timezone',
  });
  await page.addInitScript(() => {
    sessionStorage.setItem(
      'moulai.appearance.context',
      JSON.stringify({ context: '300', timezone: 'UTC' }),
    );
    const seen: string[] = [];
    (window as unknown as { seenThemes: string[] }).seenThemes = seen;
    new MutationObserver(() => {
      const theme = document.documentElement?.dataset.theme;
      if (theme) seen.push(theme);
    }).observe(document, {
      attributes: true,
      subtree: true,
      attributeFilter: ['data-theme'],
    });
  });
  await openPresentationCase(page, fixture, undefined, {
    locale: 'fr',
    theme: 'opening',
  });
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  expect(
    await page.evaluate(
      () => (window as unknown as { seenThemes: string[] }).seenThemes[0],
    ),
  ).toBe('dark');
  const arrival = page.locator('form[data-operation="arrival"]');
  await arrival.locator('..').locator('summary').click();
  await arrival.locator('[name="party"]').fill('3');
  await page.clock.runFor(1000);
  console.log(
    'scheduled boundary proof',
    await page.evaluate(() => ({
      time: new Date().toString(),
      theme: window.moulaiTheme.getSnapshot(),
    })),
  );
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await expect(arrival.locator('[name="party"]')).toHaveValue('3');
  await page.getByRole('combobox', { name: 'Apparence' }).click();
  await page.getByRole('option', { name: 'Clair', exact: true }).click();
  await page.clock.fastForward(12 * 3600000);
  console.log(
    'manual boundary proof',
    await page.evaluate(() => ({
      time: new Date().toString(),
      theme: window.moulaiTheme.getSnapshot(),
    })),
  );
  await page.evaluate(() =>
    document.dispatchEvent(new Event('visibilitychange')),
  );
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await page.getByRole('combobox', { name: 'Apparence' }).click();
  await page.getByRole('option', { name: 'Sombre', exact: true }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await expect(arrival.locator('[name="party"]')).toHaveValue('3');
  fixture.workspace.policy!.timezone = 'Pacific/Honolulu';
  const settings = page.getByTestId('session-settings');
  await settings.locator('summary').click();
  await page.locator('[name="branch"]').selectOption('301');
  await expect(page.getByTestId('operational-board')).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.clock.resume();
});

test.use({ timezoneId: 'UTC' });

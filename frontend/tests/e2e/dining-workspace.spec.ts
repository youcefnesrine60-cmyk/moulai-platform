// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { installManualThemeFixture } from './manualThemeFixture';
import { test, expect } from '@playwright/test';
import { d1Fr } from '../../src/shared/i18n/d1.fr';
import { d1En } from '../../src/shared/i18n/d1.en';
import { d1Ar } from '../../src/shared/i18n/d1.ar';
import AxeBuilder from '@axe-core/playwright';
import { fileURLToPath } from 'node:url';
import { writeFile } from 'node:fs/promises';
import { operationalContrasts } from './operationalContrasts';
import { openPresentationCase } from './diningPresentationHarness';
import { diningPresentationFixture } from '../fixtures/diningPresentation';
const phase = process.env.DINING_POLISH_PHASE === 'before' ? 'before' : 'after';
for (const locale of ['fr', 'en', 'ar'] as const)
  for (const theme of ['light', 'dark'] as const)
    for (const width of [1440, 390])
      test(`${phase} ${locale}/${theme}/${width}`, async ({ page }) => {
        const fixture = diningPresentationFixture(locale);
        const writes: string[] = [];
        await page.route('**/*', async (route) => {
          const request = route.request();
          const url = new URL(request.url());
          expect(url.hostname).toBe('127.0.0.1');
          expect(url.port).toBe('5574');
          if (url.pathname.startsWith('/local-d1/')) {
            if (request.method() !== 'GET') {
              writes.push(url.pathname);
              await route.abort();
              throw new Error('Presentation review forbids business writes');
            }
            let body: unknown;
            if (url.pathname === '/local-d1/session') body = fixture.session;
            else if (url.pathname.endsWith('/workspace'))
              body = fixture.workspace;
            else if (url.pathname.endsWith('/planning'))
              body = fixture.planning;
            else if (url.pathname.endsWith('/instant'))
              body = {
                instant: new Date(
                  url.searchParams.get('day') +
                    'T' +
                    url.searchParams.get('wall_time') +
                    '+01:00',
                ).toISOString(),
                timezone: 'Africa/Algiers',
              };
            else throw new Error('Unexpected presentation read');
            await route.fulfill({ json: body });
            return;
          }
          await route.continue();
        });
        page.on('pageerror', (error) => {
          throw error;
        });
        await page.setViewportSize({ width, height: 1000 });
        await page.addInitScript(
          ({ locale, theme }) => {
            localStorage.setItem('moulai.locale', locale);
            localStorage.setItem('moulai.theme', theme);
          },
          { locale, theme },
        );
        await page.goto('/dining-local?branch=300');
        await expect(page.locator('[name="planning_date"]')).toHaveValue(
          '2026-11-03',
        );
        await expect(
          page.getByRole('heading', { name: 'T07', exact: true }),
        ).toBeVisible();
        await page.evaluate(() => {
          const label = document.createElement('aside');
          label.setAttribute('data-visual-fixture', 'true');
          label.textContent =
            'VISUAL TEST — réponses HTTP simulées / simulated read responses / بيانات عرض محاكية — aucune opération métier';
          label.style.cssText =
            'background:#0b1324;color:#ffffff;padding:8px 16px;font:12px system-ui;position:relative;z-index:2';
          document.body.prepend(label);
        });
        if (phase === 'after') {
          await expect(page.getByTestId('physical-count-all')).toHaveAttribute(
            'data-count',
            '7',
          );
          await expect(
            page.getByTestId('physical-count-available'),
          ).toHaveAttribute('data-count', '2');
          const combined = page.getByTestId('table-card-1');
          await expect(combined.getByTestId('physical-badge')).toHaveAttribute(
            'data-state',
            'available',
          );
          await expect(combined.getByTestId('planning-full')).toBeVisible();
          await expect(combined).toContainText(/20:00|٢٠:٠٠/);
          await page.getByTestId('physical-filter-maintenance').click();
          await expect(page.locator('[data-table-card]')).toHaveCount(1);
          await expect(page.getByTestId('table-card-4')).toBeVisible();
          await page.getByTestId('physical-filter-reset').focus();
          await page.keyboard.press('Enter');
          await expect(page.locator('[data-table-card]')).toHaveCount(7);
          const reset = page.getByTestId('physical-filter-reset');
          await reset.focus();
          expect(
            await reset.evaluate((el) => getComputedStyle(el).outlineStyle),
          ).not.toBe('none');
          await expect(page.locator('[data-ui-tone="danger"]')).not.toHaveCount(
            0,
          );
          const contrasts = await operationalContrasts(page);
          for (const metric of contrasts.metrics) {
            expect(metric.text, `text: ${metric.kind}`).toBeGreaterThanOrEqual(
              4.5,
            );
            expect(
              metric.border,
              `border: ${metric.kind}`,
            ).toBeGreaterThanOrEqual(3);
          }
          expect(contrasts.focus).toBeGreaterThanOrEqual(3);
          expect(contrasts.disabledText).toBeGreaterThanOrEqual(4.5);
          await writeFile(
            fileURLToPath(
              new URL(
                `../../../artifacts/dining-workspace-20261104/contrast-${locale}-${theme}-${width}.json`,
                import.meta.url,
              ),
            ),
            JSON.stringify(contrasts, null, 2),
          );
          expect(
            (
              await new AxeBuilder({ page })
                .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
                .analyze()
            ).violations,
          ).toEqual([]);
        }
        await expect(page.locator('html')).toHaveAttribute(
          'dir',
          locale === 'ar' ? 'rtl' : 'ltr',
        );
        await expect(page.locator('html')).toHaveAttribute('data-theme', theme);
        await page.evaluate(() => document.fonts.ready);
        expect(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
        ).toBe(true);
        await page.screenshot({
          path: fileURLToPath(
            new URL(
              `../../../artifacts/dining-workspace-20261104/${phase}-${locale}-${theme}-${width}.png`,
              import.meta.url,
            ),
          ),
          fullPage: true,
        });
        if (phase === 'after') {
          const copy = locale === 'fr' ? d1Fr : locale === 'en' ? d1En : d1Ar;
          for (const section of [
            'requests',
            'finance',
            'configuration',
          ] as const) {
            await page
              .getByRole('button', {
                name: copy[`d1.section_${section}`],
                exact: true,
              })
              .click();
            await expect(page.locator('table')).not.toHaveCount(0);
            for (const table of await page.locator('table').all()) {
              expect(
                await table
                  .locator('..')
                  .evaluate((el) => getComputedStyle(el).backgroundColor),
              ).toMatch(/^rgb\(/);
            }
            const first = page
              .locator('details')
              .filter({ has: page.locator('form[data-operation]') })
              .first();
            if (await first.count()) await first.locator('summary').click();
            expect(
              await page.evaluate(
                () => document.documentElement.scrollWidth <= innerWidth,
              ),
            ).toBe(true);
            expect(
              (
                await new AxeBuilder({ page })
                  .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
                  .analyze()
              ).violations,
            ).toEqual([]);
            await page.screenshot({
              path: fileURLToPath(
                new URL(
                  `../../../artifacts/dining-workspace-20261104/after-${section}-${locale}-${theme}-${width}.png`,
                  import.meta.url,
                ),
              ),
              fullPage: true,
            });
          }
        }
        expect(writes).toEqual([]);
      });

if (phase === 'after') {
  test('empty filter and read-only actions are explicit; keyboard reset keeps physical counts', async ({
    page,
  }) => {
    const fixture = diningPresentationFixture('fr');
    fixture.workspace.tables = fixture.workspace.tables?.slice(0, 1);
    fixture.workspace.capabilities = ['read'];
    delete fixture.workspace.requests;
    delete fixture.workspace.receipts;
    const writes = await openPresentationCase(page, fixture);
    const all = page.getByTestId('physical-filter-all');
    await all.focus();
    await page.keyboard.press('Tab');
    await expect(page.getByTestId('physical-filter-available')).toBeFocused();
    await page.keyboard.press(' ');
    await expect(page.getByTestId('physical-filter-available')).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    await page.getByTestId('physical-filter-dirty').focus();
    await page.keyboard.press('Enter');
    await expect(page.getByTestId('physical-filter-empty')).toBeVisible();
    await expect(page.locator('[data-table-card]')).toHaveCount(0);
    await expect(page.getByTestId('physical-count-available')).toHaveAttribute(
      'data-count',
      '1',
    );
    await page.getByTestId('physical-filter-reset').focus();
    await page.keyboard.press('Enter');
    await expect(page.getByTestId('table-card-1')).toBeVisible();
    await expect(
      page.getByTestId('table-card-1').getByRole('link'),
    ).toHaveCount(0);
    await expect(page.locator('form[data-operation="arrival"]')).toHaveCount(0);
    await expect(page.locator('form[data-operation="physical"]')).toHaveCount(
      0,
    );
    expect(writes).toEqual([]);
  });
  test('late planning response never labels an earlier date as the current selection', async ({
    page,
  }) => {
    const fixture = diningPresentationFixture('fr');
    let release: () => void = () => {};
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const requested: string[] = [];
    const old = fixture.planning;
    const empty = old.map((row) => ({
      ...row,
      fully_reserved: false,
      closed: false,
      claims: [],
    }));
    const writes = await openPresentationCase(page, fixture, async (day) => {
      requested.push(day);
      if (day === '2026-11-04') {
        await gate;
        return old;
      }
      return day === '2026-11-03' ? old : empty;
    });
    await expect(
      page.getByTestId('table-card-1').getByTestId('planning-full'),
    ).toBeVisible();
    await page.locator('[name="planning_date"]').fill('2026-11-04');
    await expect.poll(() => requested.includes('2026-11-04')).toBe(true);
    const delayed = page.waitForResponse(
      (response) =>
        response.url().includes('/planning?') &&
        new URL(response.url()).searchParams
          .get('starts_at')
          ?.startsWith('2026-11-03T23:00:00') === true,
    );
    await page.locator('[name="planning_date"]').fill('2026-11-05');
    await expect.poll(() => requested.includes('2026-11-05')).toBe(true);
    await expect(
      page
        .getByTestId('table-card-1')
        .getByText(
          'Aucun blocage ni réservation enregistré pour cette date. Disponibilité à confirmer.',
        ),
    ).toBeVisible();
    release();
    await delayed;
    await expect(page.locator('[name="planning_date"]')).toHaveValue(
      '2026-11-05',
    );
    await expect(
      page.getByTestId('table-card-1').getByTestId('planning-full'),
    ).toHaveCount(0);
    await expect(page.getByTestId('physical-count-available')).toHaveAttribute(
      'data-count',
      '2',
    );
    expect(writes).toEqual([]);
  });
}

if (phase === 'after' && process.env.DINING_LIVE_SMOKE === '1')
  test('live read-only review uses real local PostgreSQL and no business mutation', async ({
    page,
  }) => {
    const businessWrites: string[] = [];
    await page.route('**/*', async (route) => {
      const request = route.request();
      const url = new URL(request.url());
      expect(url.hostname).toBe('127.0.0.1');
      expect(url.port).toBe('5574');
      if (
        !['GET', 'HEAD'].includes(request.method()) &&
        url.pathname !== '/local-d1/session'
      ) {
        businessWrites.push(url.pathname);
        await route.abort();
        throw new Error('Live review is read-only');
      }
      await route.continue();
    });
    await page.addInitScript(() => {
      localStorage.setItem('moulai.locale', 'fr');
      localStorage.setItem('moulai.theme', 'dark');
    });
    await page.goto('/dining-local');
    await page.locator('[name="actor"]').selectOption('owner');
    await page
      .getByRole('button', { name: 'Ouvrir cette session locale', exact: true })
      .click();
    await page.locator('[name="branch"]').selectOption({ index: 1 });
    await expect(page.getByTestId('operational-board')).toBeVisible();
    await expect(page.getByTestId('physical-count-all')).toHaveAttribute(
      'data-count',
      '2',
    );
    await page.getByTestId('physical-filter-occupied').click();
    await expect(page.getByTestId('physical-filter-empty')).toBeVisible();
    await page.getByTestId('physical-filter-reset').click();
    await page.getByRole('button', { name: 'Actualiser', exact: true }).click();
    await expect(page.getByTestId('physical-count-all')).toHaveAttribute(
      'data-count',
      '2',
    );
    await page.reload();
    await expect(page.getByTestId('physical-count-all')).toHaveAttribute(
      'data-count',
      '2',
    );
    await page.screenshot({
      path: fileURLToPath(
        new URL(
          '../../../artifacts/dining-workspace-20261104/live-local-dark-1440.png',
          import.meta.url,
        ),
      ),
      fullPage: true,
    });
    expect(businessWrites).toEqual([]);
  });

// Visual fixtures request a manual choice; opening policy is checked independently.
test.beforeEach(async ({ page }) => installManualThemeFixture(page));

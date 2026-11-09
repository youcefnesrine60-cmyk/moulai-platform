// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { installManualThemeFixture } from './manualThemeFixture';
import { test, expect, type Page, type Locator } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { fileURLToPath } from 'node:url';
import { d1Fr } from '../../src/shared/i18n/d1.fr';
import { d1En } from '../../src/shared/i18n/d1.en';
import { d1Ar } from '../../src/shared/i18n/d1.ar';

/** Reject all browser egress outside the owned local proxy; no API stubs or optimistic fixtures. */
test.beforeEach(async ({ page }) => {
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    expect(url.hostname).toBe('127.0.0.1');
    expect(['5574', '5581']).toContain(url.port);
    await route.continue();
  });
  page.on('pageerror', (error) => {
    throw error;
  });
});
async function login(page: Page, actor: string, branch?: string) {
  // Expand the compact identity disclosure; authority and workflow assertions stay unchanged.
  const settings = page.getByTestId('session-settings');
  await expect(settings).toBeVisible();
  if ((await settings.getAttribute('open')) === null)
    await settings.locator('summary').click();
  await page.locator('[name="actor"]').selectOption(actor);
  await page
    .getByRole('button', { name: d1Fr['d1.signIn'], exact: true })
    .click();
  await expect(page.getByTestId('active-session')).toContainText(
    d1Fr[`d1.actor_${actor}` as keyof typeof d1Fr],
  );
  const picker = page.locator('[name="branch"]');
  if (!(await picker.isVisible())) await settings.locator('summary').click();
  if (branch) await picker.selectOption(branch);
  else {
    await expect(picker.locator('option')).not.toHaveCount(1);
    const value = await picker.locator('option').nth(1).getAttribute('value');
    if (!value) throw new Error('scope_required');
    await picker.selectOption(value);
  }
  await expect(
    page.getByText(d1Fr['d1.permissionsVerified'] + ':', { exact: false }),
  ).toBeVisible();
}
async function tab(page: Page, name: string) {
  await page.getByRole('button', { name, exact: true }).click();
}
async function form(page: Page, operation: string): Promise<Locator> {
  const form = page.locator(`form[data-operation="${operation}"]`);
  await form.locator('..').locator('summary').click();
  return form;
}
async function save(page: Page, form: Locator) {
  await form
    .getByRole('button', { name: d1Fr['d1.save'], exact: true })
    .click();
  await expect(
    page.getByRole('status').filter({ hasText: d1Fr['d1.persistedReloaded'] }),
  ).toBeVisible();
  await expect(page.getByRole('alert')).toHaveCount(0);
}
async function first(form: Locator, name: string) {
  const field = form.locator(`[name="${name}"]`);
  const index = (await field.getAttribute('multiple')) === null ? 1 : 0;
  const value = await field.locator('option').nth(index).getAttribute('value');
  if (!value) throw new Error('option_required');
  await field.selectOption(value);
  return value;
}
async function snapshot(page: Page) {
  return page.evaluate(async () => {
    const session = await (await fetch('/local-d1/session')).json();
    const scope = session.scopes.find(
      (s: { branch_id: number }) =>
        String(s.branch_id) ===
        new URLSearchParams(location.search).get('branch'),
    );
    const root = `/local-d1/organizations/${scope.organization_id}/restaurants/${scope.restaurant_id}/branches/${scope.branch_id}/dining`;
    const value = await (await fetch(root + '/workspace')).json();
    return { root, value };
  });
}
function wall(ms: number) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Africa/Algiers',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(new Date(ms));
  const value = (kind: string) =>
    parts.find((row) => row.type === kind)?.value ?? '';
  const base = `${value('year')}-${value('month')}-${value('day')}T${value('hour')}:${value('minute')}`;
  return value('second') === '00' ? base : `${base}:${value('second')}`;
}

test('real UI nominal workflow and persistent invoice/cleaning', async ({
  page,
}) => {
  await page.addInitScript(() => {
    localStorage.setItem('moulai.locale', 'fr');
    localStorage.setItem('moulai.theme', 'light');
  });
  await page.goto('/dining-local');
  await login(page, 'owner');
  const branch = await page.locator('[name="branch"]').inputValue();
  await tab(page, d1Fr['d1.section_configuration']);
  const reference = await form(page, 'reference');
  const referenceCode = `local-ui-view-${Date.now()}`;
  await reference.locator('[name="kind"]').selectOption('view');
  for (const [name, value] of Object.entries({
    code: referenceCode,
    fr: 'Vue locale',
    en: 'Local view',
    ar: 'إطلالة محلية',
  }))
    await reference.locator(`[name="${name}"]`).fill(value);
  await save(page, reference);
  expect(
    (await snapshot(page)).value.references.some(
      (r: { code: string }) => r.code === referenceCode,
    ),
  ).toBe(true);
  await tab(page, d1Fr['d1.section_requests']);
  const request = await form(page, 'request');
  const starts = Date.now() + 30000;
  await request
    .locator('[name="customer"]')
    .fill('Client synthétique navigateur');
  await request.locator('[name="contact"]').fill('browser@example.invalid');
  await request.locator('[name="start"]').fill(wall(starts));
  await request.locator('[name="minutes"]').fill('90');
  await request.locator('[name="party"]').fill('4');
  await first(request, 'tables');
  await save(page, request);
  const stored = (await snapshot(page)).value.requests.at(-1);
  expect(stored.status).toBe('pending');
  const quote = await form(page, 'quote');
  await quote.locator('[name="request"]').selectOption(String(stored.id));
  await quote.locator('[name="currency"]').selectOption('DZD');
  await quote.locator('[name="expires"]').fill(wall(Date.now() + 3600000));
  await save(page, quote);
  await login(page, 'customer', branch);
  await tab(page, d1Fr['d1.section_requests']);
  const consent = await form(page, 'customer_consent');
  await first(consent, 'quote');
  await consent.locator('[name="consent"]').check();
  await save(page, consent);
  await login(page, 'service', branch);
  await tab(page, d1Fr['d1.section_requests']);
  const hold = await form(page, 'hold');
  await first(hold, 'quote');
  await save(page, hold);
  await login(page, 'collector', branch);
  await tab(page, d1Fr['d1.section_finance']);
  const receipt = await form(page, 'receipt');
  await first(receipt, 'quote');
  for (const [name, value] of Object.entries({
    amount: '1500',
    reference: 'LOCAL-BROWSER-RECEIPT',
    received: wall(Date.now()),
  }))
    await receipt.locator(`[name="${name}"]`).fill(value);
  await receipt.locator('[name="currency"]').selectOption('DZD');
  await receipt.locator('[name="mode"]').selectOption('cash');
  await receipt.locator('[name="received_observed"]').check();
  await save(page, receipt);
  await login(page, 'service_cleaner', branch);
  await tab(page, d1Fr['d1.section_requests']);
  const proof = await form(page, 'human_proof');
  await proof.locator('[name="request"]').selectOption(String(stored.id));
  await proof.locator('input[type="checkbox"]').check();
  await save(page, proof);
  const confirm = await form(page, 'confirm_human');
  await first(confirm, 'quote');
  await first(confirm, 'receipt');
  await save(page, confirm);
  for (const locale of ['fr', 'en', 'ar']) {
    const response = await page.request.get(
      (await snapshot(page)).root +
        `/requests/${stored.id}/confirmation?locale=${locale}`,
    );
    expect(response.status()).toBe(200);
    const html = await response.text();
    expect(html).toContain(`lang="${locale}"`);
    expect(html).toContain('<svg');
    if (locale === 'ar') expect(html).toContain('dir="rtl"');
  }
  const printRoot = (await snapshot(page)).root;
  for (const locale of ['fr', 'en', 'ar']) {
    await page.goto(
      printRoot + `/requests/${stored.id}/confirmation?locale=${locale}`,
    );
    await expect(page.locator('html')).toHaveAttribute('lang', locale);
    await expect(page.locator('svg')).toBeVisible();
    await page.screenshot({
      path: fileURLToPath(
        new URL(
          `../../../artifacts/dining-workspace-20261104/nominal/confirmation-${locale}.png`,
          import.meta.url,
        ),
      ),
      fullPage: true,
    });
  }
  await page.goto('/dining-local?branch=' + branch);
  await expect(
    page.getByText(d1Fr['d1.permissionsVerified'] + ':', { exact: false }),
  ).toBeVisible();
  await tab(page, d1Fr['d1.section_planning']);
  const arrival = await form(page, 'arrival');
  await arrival.locator('[name="request"]').selectOption(String(stored.id));
  await arrival.locator('[name="party"]').fill('4');
  await arrival.locator('[name="end"]').fill(wall(starts + 5400000));
  await expect
    .poll(() => Date.now(), { timeout: 40000, intervals: [1000] })
    .toBeGreaterThanOrEqual(starts);
  await save(page, arrival);
  await tab(page, d1Fr['d1.section_finance']);
  const invoice = await form(page, 'invoice');
  await invoice.locator('[name="request"]').selectOption(String(stored.id));
  await first(invoice, 'orders');
  await invoice.locator('[name="currency"]').selectOption('DZD');
  await invoice.locator('input[name^="price_"]').fill('6000');
  await invoice
    .locator('input[name^="source_"]')
    .fill('Pièce exacte synthétique contrôlée');
  for (const [name, value] of Object.entries({
    currency_source: 'Devise DZD synthétique',
    rounding_source: 'HALF_UP final approuvé',
    reconciliation: 'Rapprochement humain local',
  }))
    await invoice.locator(`[name="${name}"]`).fill(value);
  await save(page, invoice);
  const finalize = await form(page, 'finalize_invoice');
  await first(finalize, 'invoice');
  await save(page, finalize);
  await save(page, finalize);
  await page.reload();
  await expect(
    page.getByText(d1Fr['d1.permissionsVerified'] + ':', { exact: false }),
  ).toBeVisible();
  await tab(page, d1Fr['d1.section_finance']);
  let state = (await snapshot(page)).value;
  expect(state.allocations).toHaveLength(1);
  expect(Number(state.allocations[0].balance)).toBe(4500);
  expect(Number(state.invoices[0].total)).toBe(6000);
  expect(state.receipts).toHaveLength(1);
  await tab(page, d1Fr['d1.section_planning']);
  const physical = await form(page, 'physical');
  const installed = state.occupations.find(
    (row: { id: number; request_id: number | null }) =>
      row.request_id === stored.id,
  );
  expect(installed).toBeTruthy();
  await physical
    .locator('[name="occupation"]')
    .selectOption(String(installed.id));
  for (const action of ['departure', 'start_cleaning', 'finish_cleaning']) {
    await physical
      .locator(`[name="physical_action"][value="${action}"]`)
      .check();
    await save(page, physical);
  }
  state = (await snapshot(page)).value;
  expect(state.tables[0].physical_state).toBe('available');
  expect(
    state.events.some(
      (r: { kind: string }) => r.kind === 'availability.human_confirmed',
    ),
  ).toBe(true);
  expect(
    state.events.some((r: { kind: string }) => r.kind === 'cleaning.completed'),
  ).toBe(true);
  await expect(page.getByTestId('active-session')).toContainText(
    'Bistro MoulAI',
  );
  await expect(page.getByTestId('physical-count-all')).toHaveAttribute(
    'data-count',
    '8',
  );
  for (const state of [
    'available',
    'occupied',
    'dirty',
    'maintenance',
    'out_of_service',
  ])
    await expect(
      page
        .locator(`[data-testid="physical-badge"][data-state="${state}"]`)
        .first(),
    ).toBeVisible();
  await expect(page.getByTestId('planning-full').first()).toBeVisible();
  await page.screenshot({
    path: '../artifacts/dining-workspace-20261104/live-local-light-1440.png',
    fullPage: true,
  });
  await page.getByRole('combobox', { name: 'Apparence' }).click();
  await page.getByRole('option', { name: 'Sombre', exact: true }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await expect(page.getByTestId('operational-board')).toBeVisible();
  await page.screenshot({
    path: '../artifacts/dining-workspace-20261104/live-local-dark-1440.png',
    fullPage: true,
  });
});

for (const locale of ['fr', 'en', 'ar'] as const)
  for (const theme of ['light', 'dark'] as const)
    for (const width of [1440, 390])
      test(`persisted forms ${locale}/${theme}/${width}`, async ({ page }) => {
        const copy = { fr: d1Fr, en: d1En, ar: d1Ar }[locale];
        await page.setViewportSize({ width, height: 1000 });
        await page.addInitScript(
          ({ locale, theme }) => {
            localStorage.setItem('moulai.locale', locale);
            localStorage.setItem('moulai.theme', theme);
          },
          { locale, theme },
        );
        await page.goto('/dining-local');
        await page.locator('[name="actor"]').selectOption('owner');
        await page
          .getByRole('button', { name: copy['d1.signIn'], exact: true })
          .click();
        const picker = page.locator('[name="branch"]');
        await expect(picker.locator('option')).not.toHaveCount(1);
        await picker.selectOption({ index: 1 });
        await expect(
          page.getByText(copy['d1.permissionsVerified'] + ':', {
            exact: false,
          }),
        ).toBeVisible();
        await page
          .getByRole('button', {
            name: copy['d1.section_requests'],
            exact: true,
          })
          .click();
        await page
          .locator('form[data-operation="request"]')
          .locator('..')
          .locator('summary')
          .click();
        await page.evaluate(() => document.fonts.ready);
        expect(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
        ).toBe(true);
        await expect(page.locator('html')).toHaveAttribute(
          'dir',
          locale === 'ar' ? 'rtl' : 'ltr',
        );
        await expect(page.locator('html')).toHaveAttribute('data-theme', theme);
        expect(
          (
            await new AxeBuilder({ page })
              .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
              .analyze()
          ).violations,
        ).toEqual([]);
        await page.screenshot({
          path: fileURLToPath(
            new URL(
              `../../../artifacts/dining-workspace-20261104/nominal/${locale}-${theme}-${width}.png`,
              import.meta.url,
            ),
          ),
          fullPage: true,
        });
      });

// Visual fixtures request a manual choice; opening policy is checked independently.
test.beforeEach(async ({ page }) => installManualThemeFixture(page));

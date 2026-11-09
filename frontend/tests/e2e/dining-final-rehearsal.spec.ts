// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { installManualThemeFixture } from './manualThemeFixture';
import { test, expect, type Page, type Locator } from '@playwright/test';
import { writeFile } from 'node:fs/promises';
import { d1Fr as copy } from '../../src/shared/i18n/d1.fr';
import type {
  Snapshot,
  LocalSession,
} from '../../src/shared/dining/local/client';
import { shortReference } from '../../src/shared/dining/referenceValue';
const output = '../artifacts/dining-final-rehearsal-20261104';
const rows: {
  step: string;
  profile: string;
  action: string;
  result: string;
  proof: string;
  limit: string;
}[] = [];
const text = (key: string) => copy[`d1.${key}` as keyof typeof copy];
async function login(page: Page, actor: string) {
  const settings = page.getByTestId('session-settings');
  await expect(settings).toBeVisible();
  if ((await settings.getAttribute('open')) === null)
    await settings.locator('summary').click();
  await settings.locator('[name="actor"]').selectOption(actor);
  await page.getByRole('button', { name: text('signIn'), exact: true }).click();
  await expect(page.getByTestId('active-session')).toContainText(
    text(`actor_${actor}`),
  );
  const branch = page.locator('[name="branch"]');
  if ((await branch.inputValue()) !== '7000300')
    await branch.selectOption('7000300');
  await expect(
    page.getByRole('button', { name: text('reload'), exact: true }),
  ).toBeVisible();
  if ((await settings.getAttribute('open')) !== null)
    await settings.locator('summary').click();
}
async function tab(page: Page, name: string) {
  await page
    .getByRole('button', { name: text(`section_${name}`), exact: true })
    .click();
}
async function form(page: Page, operation: string): Promise<Locator> {
  const element = page.locator(`form[data-operation="${operation}"]`);
  await expect(element).toBeAttached();
  const details = element.locator('..');
  if ((await details.getAttribute('open')) === null)
    await details.locator('summary').click();
  return element;
}
async function save(page: Page, element: Locator) {
  const response = page.waitForResponse(
    (r) =>
      r.request().method() === 'POST' &&
      r.url().includes('/local-d1/') &&
      (r.url().endsWith('/commands') ||
        r.url().endsWith('/receipts') ||
        r.url().endsWith('/accept')),
  );
  await element.locator('button[type="submit"]').click();
  const reply = await response;
  expect(reply.status(), await reply.text()).toBe(200);
  await expect(
    page.getByText(text('persistedReloaded'), { exact: true }),
  ).toBeVisible();
  return (await reply.json()) as Record<string, unknown>;
}
async function state(page: Page) {
  return page.evaluate(async () => {
    const session: LocalSession = await (
      await fetch('/local-d1/session')
    ).json();
    const scope = session.scopes.find((row) => row.branch_id === 7000300)!;
    const root = `/local-d1/organizations/${scope.organization_id}/restaurants/${scope.restaurant_id}/branches/${scope.branch_id}/dining`;
    const url =
      session.actor === 'customer'
        ? `/local-d1/dining/restaurants/${scope.restaurant_id}/branches/${scope.branch_id}/customer-workspace`
        : root + '/workspace';
    const value: Snapshot = await (await fetch(url)).json();
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
  const get = (kind: string) =>
    parts.find((row) => row.type === kind)?.value ?? '';
  return (
    `${get('year')}-${get('month')}-${get('day')}T${get('hour')}:${get('minute')}` +
    (get('second') === '00' ? '' : `:${get('second')}`)
  );
}
async function fields(element: Locator, values: Record<string, string>) {
  for (const [name, value] of Object.entries(values))
    await element.locator(`[name="${name}"]`).fill(value);
}
async function grant(page: Page, member: number, cap: string, active = true) {
  const element = await form(page, 'grant');
  await element.locator('[name="member"]').selectOption(String(member));
  await element.locator('[name="capability"]').selectOption(cap);
  await element.locator('[name="active"]').setChecked(active);
  await save(page, element);
}
async function evidence(
  page: Page,
  step: string,
  profile: string,
  action: string,
  limit = 'Identité locale simulée ; opérations PostgreSQL réelles, données fictives.',
) {
  const image = `ui-${String(rows.length + 1).padStart(2, '0')}.png`;
  await page.screenshot({ path: `${output}/${image}`, fullPage: true });
  rows.push({ step, profile, action, result: 'PASS', proof: image, limit });
  await writeFile(`${output}/ui-matrix.json`, JSON.stringify(rows, null, 2));
}
async function makeBooking(page: Page, tableId: number, special: boolean) {
  await login(page, 'service');
  await tab(page, 'requests');
  const request = await form(page, 'request');
  const starts = Date.now() + (special ? 90000 : 3600000);
  await fields(request, {
    customer: 'Client fictif de recette',
    contact: 'rehearsal@example.invalid',
    start: wall(starts),
    minutes: '90',
    party: '4',
  });
  await request.locator(`[name="tables"][value="${tableId}"]`).check();
  if (special) {
    const snapshot = (await state(page)).value;
    const event = snapshot.references!.find(
      (row) => row.code === 'ui-final-event',
    )!;
    const feature = snapshot.references!.find(
      (row) => row.code === 'ui-final-quiet',
    )!;
    await request.locator('[name="event"]').selectOption(String(event.id));
    await request.locator('[name="preparation"]').check();
    await request.locator(`[name="features"][value="${feature.id}"]`).check();
    await request
      .getByRole('button', { name: text('addDish'), exact: true })
      .click();
    await request
      .locator('[name="menu_product_0"]')
      .selectOption(String(snapshot.products![0]!.id));
    await request.locator('[name="menu_quantity_0"]').fill('2');
  }
  const saved = await save(page, request);
  const id = Number(saved.identifier);
  const reference = shortReference(id);
  await page.locator('[name="request_search"]').fill(reference);
  await expect(
    page.getByRole('region', { name: text('requests'), exact: true }),
  ).toContainText(reference);
  const quote = await form(page, 'quote');
  await quote.locator('[name="request"]').selectOption(String(id));
  await quote.locator('[name="currency"]').selectOption('DZD');
  await quote.locator('[name="expires"]').fill(wall(Date.now() + 7200000));
  const quoted = await save(page, quote);
  const quoteId = Number(quoted.identifier);
  const stored = (await state(page)).value.quotes!.find(
    (row) => row.id === quoteId,
  )!;
  expect(Number(stored.amount)).toBe(1500);
  expect(stored.components.find((row) => row.kind === 'table')?.quantity).toBe(
    '1.5',
  );
  if (special) {
    expect(stored.components.some((row) => row.kind === 'menu')).toBe(true);
    await evidence(
      page,
      'Demande et devis',
      'Service manager',
      `Demande ${reference}, durée exacte 90 minutes ; devis DZD détaillé, événement et critères.`,
    );
  }
  await login(page, 'customer');
  await tab(page, 'requests');
  await page.locator('[name="request_search"]').fill(reference);
  const consent = await form(page, 'customer_consent');
  await consent.locator('[name="quote"]').selectOption(String(quoteId));
  await consent.locator('[name="consent"]').check();
  await save(page, consent);
  await login(page, 'service');
  await tab(page, 'requests');
  if (special) {
    const restaurant = await form(page, 'restaurant_consent');
    await restaurant.locator('[name="quote"]').selectOption(String(quoteId));
    await restaurant.locator('[name="consent"]').check();
    await save(page, restaurant);
  }
  const proof = await form(page, 'human_proof');
  await proof.locator('[name="request"]').selectOption(String(id));
  await proof.locator('input[type="checkbox"]').check();
  await save(page, proof);
  const hold = await form(page, 'hold');
  await hold.locator('[name="quote"]').selectOption(String(quoteId));
  await save(page, hold);
  const held = (await state(page)).value;
  expect(
    held.claims?.some(
      (row) => row.request_id === id && row.kind === 'hold' && row.expires_at,
    ),
  ).toBe(true);
  if (special)
    await evidence(
      page,
      'Accords, validation et blocage',
      'Client puis service manager',
      'Même version acceptée par les deux parties ; validation humaine de toute la période protégée ; blocage avant paiement.',
    );
  await login(page, 'collector');
  await tab(page, 'finance');
  const receipt = await form(page, 'receipt');
  await receipt.locator('[name="quote"]').selectOption(String(quoteId));
  await fields(receipt, {
    amount: '1500',
    reference: `LOCAL-UI-${reference}`,
    received: wall(Date.now()),
  });
  await receipt.locator('[name="currency"]').selectOption('DZD');
  await receipt.locator('[name="mode"]').selectOption('cash');
  await receipt.locator('[name="received_observed"]').check();
  await save(page, receipt);
  if (special)
    await evidence(
      page,
      'Avance',
      'Responsable d’encaissement',
      'Réception fictive de 1 500 DZD explicitement observée, sans activation automatique.',
    );
  await login(page, 'service');
  await tab(page, 'requests');
  const confirm = await form(page, 'confirm_human');
  await confirm.locator('[name="quote"]').selectOption(String(quoteId));
  const received = (await state(page)).value.receipts!.find(
    (row) => row.request_id === id,
  )!;
  await confirm.locator('[name="receipt"]').selectOption(String(received.id));
  const result = await save(page, confirm);
  return {
    id,
    quoteId,
    starts,
    reference,
    receiptId: received.id,
    token: String(result.qr_token),
  };
}

test('complete UI rehearsal with real role switches, permissions, financial persistence and cancelled QR', async ({
  page,
  browser,
}) => {
  rows.length = 0;
  await page.route('**/*', (route) => {
    const url = new URL(route.request().url());
    expect(url.origin).toBe('http://127.0.0.1:5574');
    return route.continue();
  });
  await page.addInitScript(() => {
    localStorage.setItem('moulai.locale', 'fr');
    localStorage.setItem('moulai.theme', 'light');
  });
  await page.goto('/dining-local?branch=7000300');
  await login(page, 'owner');
  await tab(page, 'configuration');
  const initial = (await state(page)).value;
  const first = initial.tables!.find((row) => row.code === 'T1')!;
  const second = initial.tables!.find((row) => row.code === 'T2')!;
  for (const [member, cap] of [
    [7000031, 'finance.read'],
    [7000033, 'collect'],
    [7000033, 'finance.read'],
    [7000038, 'finance.read'],
    [7000038, 'invoices.create'],
    [7000038, 'invoices.finalize'],
    [7000038, 'advances.allocate'],
    [7000039, 'finance.read'],
    [7000032, 'clean'],
    [7000037, 'reservations.cancel_before_arrival'],
  ] as const)
    await grant(page, member, cap);
  const policy = await form(page, 'policy');
  await fields(policy, {
    timezone: 'Africa/Algiers',
    preparation_seconds: '0',
    cleaning_seconds: '300',
    hold_seconds: '1200',
  });
  await save(page, policy);
  const calendar = await form(page, 'calendar');
  await calendar.locator('[name="calendar_kind"]').selectOption('weekly');
  for (let day = 0; day < 7; day++) {
    await calendar.locator('[name="weekday"]').selectOption(String(day));
    await fields(calendar, { start_0: '00:00', end_0: '00:00' });
    await calendar.locator('[name="next_0"]').check();
    await save(page, calendar);
  }
  for (const [kind, code, fr, en, ar, pricing] of [
    [
      'feature',
      'ui-final-quiet',
      'Espace calme',
      'Quiet area',
      'مكان هادئ',
      '',
    ],
    [
      'event',
      'ui-final-event',
      'Anniversaire',
      'Birthday',
      'عيد ميلاد',
      'ui-final-preparation',
    ],
  ]) {
    const reference = await form(page, 'reference');
    await reference.locator('[name="kind"]').selectOption(kind!);
    await fields(reference, {
      code: code!,
      fr: fr!,
      en: en!,
      ar: ar!,
      pricing: pricing!,
    });
    await save(page, reference);
  }
  const references = (await state(page)).value.references!;
  const feature = references.find((row) => row.code === 'ui-final-quiet')!;
  const table = await form(page, 'table');
  await table.locator('[name="table_edit"]').selectOption(String(first.id));
  await fields(table, {
    name: 'Table de recette UI',
    pricing: 'ui-final-table',
  });
  await table.locator(`[name="traits"][value="${feature.id}"]`).check();
  await save(page, table);
  const tariff = await form(page, 'tariff');
  for (const [reference, component, unit, price] of [
    ['ui-final-table', 'table', 'per_hour', '986.66'],
    ['ui-final-preparation', 'preparation', 'flat', '0'],
  ]) {
    await fields(tariff, {
      reference: reference!,
      price: price!,
      start: wall(Date.now() - 3600000),
      end: '',
    });
    await tariff.locator('[name="component"]').selectOption(component!);
    await tariff.locator('[name="currency"]').selectOption('DZD');
    await tariff.locator('[name="unit"]').selectOption(unit!);
    await save(page, tariff);
  }
  await evidence(
    page,
    'Configuration',
    'Propriétaire',
    'Horaires, devise/paramètres, table, critère, événement, tarifs fictifs et habilitations enregistrés depuis les formulaires.',
    'Bootstrap des identités, référentiels initiaux et commande alimentaire historique par le script local ; aucun tarif commercial.',
  );
  const booking = await makeBooking(page, first.id, true);
  for (const locale of ['fr', 'en', 'ar'] as const) {
    const document = await page.request.get(
      (await state(page)).root +
        `/requests/${booking.id}/confirmation?locale=${locale}`,
    );
    expect(document.status()).toBe(200);
    expect(await document.text()).toContain('<svg');
    expect(await document.text()).toContain(`lang="${locale}"`);
  }
  await evidence(
    page,
    'Confirmation',
    'Service manager',
    `Confirmation atomique ${booking.reference}, QR réel généré localement et documents FR/EN/AR consultables.`,
  );
  await tab(page, 'planning');
  await page
    .getByTestId(`table-card-${first.id}`)
    .getByRole('button', { name: 'Voir les actions autorisées', exact: true })
    .click();
  const panel = page.getByTestId('table-actions');
  await expect(panel).toContainText(first.code);
  const arrival = await form(page, 'arrival');
  await expect(arrival.locator('[name="request"]')).toHaveValue(
    String(booking.id),
  );
  await arrival.locator('[name="end"]').fill(wall(booking.starts + 5400000));
  await expect
    .poll(() => Date.now(), { timeout: 120000, intervals: [1000] })
    .toBeGreaterThanOrEqual(booking.starts);
  await save(page, arrival);
  await evidence(
    page,
    'Arrivée contextualisée',
    'Service manager',
    'Même table/réservation présélectionnées ; installation réelle et fin prévue enregistrées.',
  );
  await login(page, 'finance_reader');
  await tab(page, 'finance');
  await expect(page.locator('form[data-operation="receipt"]')).toHaveCount(0);
  await expect(page.locator('form[data-operation="invoice"]')).toHaveCount(0);
  await expect(
    page.locator('form[data-operation="finalize_invoice"]'),
  ).toHaveCount(0);
  await expect(page.locator('form[data-operation="allocate"]')).toHaveCount(0);
  await evidence(
    page,
    'Consultation financière',
    'Consultation uniquement',
    'Les documents sont visibles ; les quatre actions financières restent absentes.',
  );
  await login(page, 'finance');
  await tab(page, 'finance');
  const adminContext = await browser.newContext({
    baseURL: 'http://127.0.0.1:5574',
  });
  const admin = await adminContext.newPage();
  await admin.goto('/dining-local?branch=7000300');
  await login(admin, 'owner');
  await tab(admin, 'configuration');
  await grant(admin, 7000038, 'invoices.finalize', false);
  await page.getByRole('button', { name: text('reload'), exact: true }).click();
  await expect(
    page.locator('form[data-operation="finalize_invoice"]'),
  ).toHaveCount(0);
  await grant(admin, 7000038, 'invoices.finalize', true);
  await page.getByRole('button', { name: text('reload'), exact: true }).click();
  await adminContext.close();
  const invoice = await form(page, 'invoice');
  await invoice.locator('[name="request"]').selectOption(String(booking.id));
  const food = (await state(page)).value.food_orders![0]!;
  await invoice.locator(`[name="orders"][value="${food.id}"]`).check();
  await invoice.locator('input[name^="price_"]').fill('6000');
  await invoice
    .locator('input[name^="source_"]')
    .fill('Pièce exacte fictive de recette');
  await fields(invoice, {
    currency_source: 'DZD — preuve fictive locale',
    rounding_source: 'HALF_UP final',
    reconciliation: 'Rapprochement humain de recette',
  });
  await invoice.locator('[name="currency"]').selectOption('DZD');
  const draft = await save(page, invoice);
  const finalize = await form(page, 'finalize_invoice');
  await finalize
    .locator('[name="invoice"]')
    .selectOption(String(draft.identifier));
  await save(page, finalize);
  await save(page, finalize);
  await page.reload();
  await expect(
    page.getByRole('button', { name: text('reload'), exact: true }),
  ).toBeVisible();
  await tab(page, 'finance');
  const checked = (await state(page)).value;
  expect(
    checked.invoices?.find((row) => row.id === Number(draft.identifier))?.total,
  ).toMatch(/^6000(?:\.0+)?$/);
  expect(
    checked.allocations?.filter((row) => row.request_id === booking.id),
  ).toHaveLength(1);
  expect(
    Number(
      checked.allocations!.find((row) => row.request_id === booking.id)!
        .balance,
    ),
  ).toBe(4500);
  expect(
    checked.receipts?.filter((row) => row.request_id === booking.id),
  ).toHaveLength(1);
  await evidence(
    page,
    'Facture et révocation',
    'Responsable de facturation',
    'Révocation en session observée ; ventes 6 000 DZD, avance 1 500, solde 4 500 après rechargement et double finalisation, affectation unique.',
  );
  await login(page, 'cleaner');
  await expect(
    page.getByRole('button', { name: text('section_finance'), exact: true }),
  ).toHaveCount(0);
  await page
    .getByTestId(`table-card-${first.id}`)
    .getByRole('button', { name: 'Voir les actions autorisées', exact: true })
    .click();
  await expect(page.locator('form[data-operation="human_proof"]')).toHaveCount(
    0,
  );
  for (const label of [
    'saveObservation',
    'saveStartCleaning',
    'saveFinishCleaning',
  ]) {
    const physical = await form(page, 'physical');
    await expect(physical.locator('button[type="submit"]')).toHaveText(
      text(label),
    );
    await save(page, physical);
  }
  await expect(
    page.getByTestId(`table-card-${first.id}`).getByTestId('physical-badge'),
  ).toHaveAttribute('data-state', 'available');
  await evidence(
    page,
    'Départ et nettoyage',
    'Agent de nettoyage',
    'Trois transitions physiques distinctes, aucun droit de confirmation de disponibilité.',
  );
  await login(page, 'service');
  await tab(page, 'requests');
  const proof = await form(page, 'human_proof');
  await proof.locator(`[name="tables"][value="${first.id}"]`).check();
  await fields(proof, {
    start: wall(Date.now() + 10800000),
    end: wall(Date.now() + 14400000),
  });
  await proof
    .locator('input[type="checkbox"]')
    .filter({ hasNot: page.locator('[name="tables"]') })
    .last()
    .check();
  await save(page, proof);
  await evidence(
    page,
    'Validation séparée',
    'Service manager',
    'Nouvelle validation humaine explicite après le nettoyage ; auteurs et événements distincts.',
  );
  const cancelled = await makeBooking(page, second.id, false);
  await login(page, 'canceller');
  await tab(page, 'requests');
  const cancel = await form(page, 'cancel_before_arrival');
  await cancel.locator('[name="request"]').selectOption(String(cancelled.id));
  await fields(cancel, { reason: 'Annulation fictive avant arrivée' });
  await cancel.locator('[name="origin"]').selectOption('customer');
  await save(page, cancel);
  await save(page, cancel);
  const cancelledState = (await state(page)).value;
  expect(
    cancelledState.claims?.filter(
      (row) => row.request_id === cancelled.id && row.active,
    ),
  ).toHaveLength(0);
  await page.goto(`/verify-reservation?locale=fr#${cancelled.token}`);
  await expect(page.locator('#result')).toHaveAttribute('data-valid', 'false');
  await page.screenshot({ path: `${output}/cancelled-qr.png`, fullPage: true });
  await page.goto('/dining-local?branch=7000300');
  await login(page, 'collector');
  await tab(page, 'finance');
  expect(
    (await state(page)).value.receipts?.some(
      (row) => row.id === cancelled.receiptId && row.status === 'verified',
    ),
  ).toBe(true);
  await evidence(
    page,
    'Annulation avant arrivée',
    'Personne habilitée puis encaissement',
    'Annulation répétée sans doublon, créneau libéré, QR invalide ; avance conservée pour traitement humain.',
  );
});

test('real confirmation pages print in French English and Arabic', async ({
  page,
}) => {
  await page.route('**/*', (route) => {
    expect(new URL(route.request().url()).origin).toBe('http://127.0.0.1:5574');
    return route.continue();
  });
  await page.addInitScript(() => localStorage.setItem('moulai.locale', 'fr'));
  await page.goto('/dining-local?branch=7000300');
  await login(page, 'service');
  await tab(page, 'requests');
  for (const locale of ['fr', 'en', 'ar'] as const) {
    await page
      .getByRole('combobox', {
        name: /Langue de l’interface|Interface language|لغة الواجهة/,
      })
      .click();
    await page
      .getByRole('option', {
        name: { fr: 'Français — FR', en: 'English — EN', ar: 'العربية — AR' }[
          locale
        ],
        exact: true,
      })
      .click();
    const link = page.locator('a[href*="/confirmation?"]').first();
    await expect(link).toBeVisible();
    const opened = page.waitForEvent('popup');
    await link.click();
    const document = await opened;
    await document.waitForLoadState('domcontentloaded');
    await expect(document.locator('html')).toHaveAttribute('lang', locale);
    await expect(document.locator('html')).toHaveAttribute(
      'dir',
      locale === 'ar' ? 'rtl' : 'ltr',
    );
    await expect(document.locator('svg')).toBeVisible();
    await document.emulateMedia({ media: 'print' });
    await document.screenshot({
      path: `${output}/confirmation-print-${locale}.png`,
      fullPage: true,
    });
    await document.close();
  }
});

test('real server daylight saving resolution only exposes necessary choices', async ({
  page,
}) => {
  await page.route('**/*', (route) => {
    expect(new URL(route.request().url()).origin).toBe('http://127.0.0.1:5574');
    return route.continue();
  });
  await page.addInitScript(() => localStorage.setItem('moulai.locale', 'fr'));
  await page.goto('/dining-local?branch=7000300');
  await login(page, 'owner');
  const settings = page.getByTestId('session-settings');
  await settings.locator('summary').click();
  await page.locator('[name="branch"]').selectOption('7000301');
  await settings.locator('summary').click();
  await tab(page, 'configuration');
  const policy = await form(page, 'policy');
  await fields(policy, {
    timezone: 'Europe/Paris',
    response_seconds: '60',
    hold_seconds: '1200',
    lateness_seconds: '300',
    preparation_seconds: '0',
    cleaning_seconds: '300',
    confirmation_seconds: '7200',
    offsets: '0,60',
    terms: 'Configuration fictive DST locale.',
  });
  await policy.locator('[name="services"][value="7000031"]').check();
  await policy
    .getByRole('button', { name: text('addCurrency'), exact: true })
    .click();
  await fields(policy, { currency_0: 'DZD', precision_0: '2' });
  await policy
    .getByRole('button', { name: text('addMode'), exact: true })
    .click();
  await fields(policy, {
    mode_0: 'cash',
    instructions_0: 'Fonds fictifs uniquement.',
  });
  await save(page, policy);
  const calendar = await form(page, 'calendar');
  await calendar.locator('[name="calendar_kind"]').selectOption('dated');
  await fields(calendar, {
    date: '2027-10-31',
    start_0: '02:30',
    end_0: '04:00',
  });
  const fold = calendar.locator('[name="start_fold_0"]');
  await expect(fold).toBeVisible();
  await fold.selectOption('1');
  await page.screenshot({
    path: `${output}/dst-ambiguous.png`,
    fullPage: true,
  });
  await calendar.locator('[name="start_0"]').fill('03:30');
  await expect(fold).toHaveCount(0);
  await fields(calendar, { date: '2027-03-28', start_0: '02:30' });
  await expect(
    calendar.getByText(text('nonexistentTime'), { exact: true }),
  ).toBeVisible();
  await expect(fold).toHaveCount(0);
  await page.screenshot({
    path: `${output}/dst-nonexistent.png`,
    fullPage: true,
  });
  await writeFile(
    `${output}/dst-ui.json`,
    JSON.stringify(
      {
        result: 'PASS',
        timezone: 'Europe/Paris',
        ambiguous: '2027-10-31T02:30',
        ordinary: '2027-10-31T03:30',
        nonexistent: '2027-03-28T02:30',
        calendar_saved: false,
        external_calls: 0,
      },
      null,
      2,
    ),
  );
});

// Visual fixtures request a manual choice; opening policy is checked independently.
test.beforeEach(async ({ page }) => installManualThemeFixture(page));

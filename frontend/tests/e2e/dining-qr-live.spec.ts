// MoulAI™ — actual local UI and PostgreSQL operations; no mocked business success.
import { installManualThemeFixture } from './manualThemeFixture';
import { test, expect, type Page, type Locator } from '@playwright/test';
import { writeFile, readFile } from 'node:fs/promises';
import AxeBuilder from '@axe-core/playwright';
import { z } from 'zod';
import { d1Fr } from '../../src/shared/i18n/d1.fr';
import {
  serviceFr,
  serviceEn,
  serviceAr,
} from '../../src/shared/i18n/diningService';
import type { Snapshot } from '../../src/shared/dining/local/client';
const copy = { ...d1Fr, ...serviceFr };
const text = (key: string) => copy[('d1.' + key) as keyof typeof copy];
const output = '../artifacts/dining-qr-staff-20261105';
test.describe.configure({ mode: 'serial' });
const root =
  '/local-d1/organizations/7000010/restaurants/7000200/branches/7000300/dining';
async function login(page: Page, actor: string) {
  const settings = page.getByTestId('session-settings');
  if ((await settings.getAttribute('open')) === null)
    await settings.locator('summary').click();
  await settings.locator('[name="actor"]').selectOption(actor);
  await settings
    .getByRole('button', { name: text('signIn'), exact: true })
    .click();
  await expect(page.getByTestId('active-session')).toContainText(
    text('actor_' + actor),
  );
  const branch = settings.locator('[name="branch"]');
  if (
    actor !== 'new_employee' &&
    (await branch.count()) &&
    (await branch.isVisible())
  )
    await branch.selectOption('7000300');
  if ((await settings.getAttribute('open')) !== null)
    await settings.locator('summary').click();
}
async function tab(page: Page, name: string) {
  await page
    .getByRole('button', { name: text('section_' + name), exact: true })
    .click();
}
async function form(page: Page, operation: string): Promise<Locator> {
  const f = page.locator('form[data-operation="' + operation + '"]');
  await expect(f).toBeAttached();
  const d = f.locator('..');
  if ((await d.getAttribute('open')) === null)
    await d.locator('summary').click();
  return f;
}
async function save(page: Page, f: Locator) {
  const reply = page.waitForResponse(
    (r) =>
      r.request().method() === 'POST' &&
      r.url().includes('/local-d1/') &&
      !r.url().endsWith('/public/visit'),
  );
  await f.locator('button[type="submit"]').click();
  const response = await reply;
  expect(response.status(), await response.text()).toBe(200);
  await expect(
    page.getByText(text('persistedReloaded'), { exact: true }),
  ).toBeVisible();
  return response.json() as Promise<Record<string, unknown>>;
}
async function state(page: Page): Promise<Snapshot> {
  return page.evaluate(
    async (root) => (await fetch(root + '/workspace')).json(),
    root,
  );
}
function wall(milliseconds: number) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Africa/Algiers',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(new Date(milliseconds));
  const get = (key: string) => parts.find((p) => p.type === key)!.value;
  return `${get('year')}-${get('month')}-${get('day')}T${get('hour')}:${get('minute')}`;
}
async function grant(page: Page, member: number, cap: string) {
  const f = await form(page, 'grant');
  await f.locator('[name="member"]').selectOption(String(member));
  await f.locator('[name="capability"]').selectOption(cap);
  await f.locator('[name="active"]').check();
  await save(page, f);
}

test('actual QR browser journey with distinct service kitchen finance and cleaning', async ({
  page,
  context,
}) => {
  await page.route('**/*', (route) => {
    expect(new URL(route.request().url()).origin).toBe('http://127.0.0.1:5574');
    return route.continue();
  });
  await page.addInitScript(() => localStorage.setItem('moulai.locale', 'fr'));
  await page.goto('/dining-local?branch=7000300');
  await login(page, 'owner');
  await tab(page, 'configuration');
  for (const [member, caps] of [
    [7000031, ['orders.read', 'orders.approve', 'orders.complete']],
    [7000040, ['orders.read', 'orders.prepare']],
    [
      7000038,
      [
        'finance.read',
        'invoices.create',
        'invoices.finalize',
        'documents.issue',
      ],
    ],
    [7000030, ['documents.issue']],
  ] as const)
    for (const cap of caps) await grant(page, member, cap);
  const current = await state(page),
    table = current.tables!.find((row) => row.code === 'T1')!,
    product = current.products![0]!;
  if (
    !(current.tariffs ?? []).some(
      (row) => row.reference === 'public-product:' + product.id,
    )
  ) {
    const rate = await form(page, 'tariff');
    await rate
      .locator('[name="reference"]')
      .fill('public-product:' + product.id);
    await rate.locator('[name="component"]').selectOption('menu');
    await rate.locator('[name="currency"]').selectOption('DZD');
    await rate.locator('[name="unit"]').selectOption('per_item');
    await rate.locator('[name="price"]').fill('125.125');
    await rate.locator('[name="start"]').fill(wall(Date.now() - 86400000));
    await save(page, rate);
  }
  await tab(page, 'visits');
  const issue = await form(page, 'public_link');
  await issue
    .locator('[name="document_resource"]')
    .selectOption(String(table.id));
  await issue.locator('[name="document_action"]').selectOption('rotate');
  await issue
    .locator('[name="reason"]')
    .fill('Publication explicite de l’état physique — recette');
  await issue.locator('[name="publish_physical"]').check();
  const issued = await save(page, issue);
  const linkId = Number(issued.identifier);
  const snapshot = await state(page),
    link = snapshot.public_links!.find((row) => row.id === linkId)!;
  await page.screenshot({
    path: output + '/qr-table-management.png',
    fullPage: true,
  });
  const guest = await context.newPage();
  await guest.goto('/menu?locale=fr#' + link.public_id);
  await expect(guest.getByRole('heading', { name: /T1/ })).toBeVisible();
  await guest.getByLabel(text('currency'), { exact: true }).selectOption('DZD');
  await guest.getByLabel(text('partySize'), { exact: true }).fill('4');
  await guest
    .getByRole('button', { name: text('signalPresence'), exact: true })
    .click();
  await expect(
    guest.getByRole('heading', {
      name: text('visitStatus_pending'),
      exact: true,
    }),
  ).toBeVisible();
  await login(page, 'service');
  await tab(page, 'visits');
  const install = await form(page, 'install_presence');
  await install.locator('[name="presence"]').selectOption({ index: 1 });
  await install.locator('[name="end"]').fill(wall(Date.now() + 5400000));
  await install.locator('[name="observed"]').check();
  await save(page, install);
  await guest
    .getByRole('button', { name: text('refresh'), exact: true })
    .click();
  await expect(
    guest.getByRole('heading', {
      name: text('visitStatus_active'),
      exact: true,
    }),
  ).toBeVisible();
  await guest.getByLabel(product.name + ' — ' + text('quantity')).fill('2');
  await guest
    .getByRole('button', { name: text('requestFood'), exact: true })
    .click();
  await expect(guest.getByRole('heading', { name: / — / })).toContainText(
    text('orderStatus_pending'),
  );
  await guest.reload();
  await expect(guest.getByRole('heading', { name: / — / })).toContainText(
    text('orderStatus_pending'),
  );
  await guest.screenshot({
    path: output + '/public-visit-order.png',
    fullPage: true,
  });
  await page.getByRole('button', { name: text('reload'), exact: true }).click();
  await tab(page, 'visits');
  const prepared = await state(page),
    order = prepared.visit_orders!.at(-1)!,
    visit = prepared.visits!.find((row) => row.id === order.visit_id)!;
  const service = await form(page, 'visit_order_transition');
  await service
    .locator('[name="visit_order"]')
    .selectOption(String(order.order_id));
  await service.locator('[name="visit_action"]').selectOption('approve');
  await service.locator('[name="observed_order"]').check();
  await save(page, service);
  await login(page, 'kitchen');
  await tab(page, 'visits');
  let kitchen = await form(page, 'visit_order_transition');
  await kitchen
    .locator('[name="visit_order"]')
    .selectOption(String(order.order_id));
  await kitchen.locator('[name="observed_order"]').check();
  for (const action of ['prepare', 'ready']) {
    await kitchen.locator('[name="visit_action"]').selectOption(action);
    await save(page, kitchen);
  }
  await page.screenshot({
    path: output + '/kitchen-order-ready.png',
    fullPage: true,
  });
  await login(page, 'service');
  await tab(page, 'visits');
  const served = await form(page, 'visit_order_transition');
  await served
    .locator('[name="visit_order"]')
    .selectOption(String(order.order_id));
  await served.locator('[name="visit_action"]').selectOption('served');
  await served.locator('[name="observed_order"]').check();
  await save(page, served);
  await login(page, 'finance');
  await tab(page, 'finance');
  const invoice = await form(page, 'invoice');
  await invoice.locator('input[type="checkbox"]').first().check();
  await invoice
    .locator('[name="occupation"]')
    .selectOption(String(visit.occupation_id));
  await invoice
    .locator('[name="orders"][value="' + order.order_id + '"]')
    .check();
  await invoice
    .locator('[name="currency_source"]')
    .fill('Tarif public DZD fictif exact');
  await invoice
    .locator('[name="rounding_source"]')
    .fill('Arrondi final HALF_UP — deux décimales');
  await invoice
    .locator('[name="reconciliation"]')
    .fill('Recette locale — instantané tarifaire QR vérifié');
  const drafted = await save(page, invoice);
  const invoiceId = Number(drafted.identifier);
  const finalize = await form(page, 'finalize_invoice');
  await finalize.locator('[name="invoice"]').selectOption(String(invoiceId));
  await save(page, finalize);
  await page.screenshot({
    path: output + '/visit-invoice-finalized.png',
    fullPage: true,
  });
  await tab(page, 'visits');
  const doc = await form(page, 'public_link');
  await doc.locator('[name="document_kind"]').selectOption('food_invoice');
  await doc
    .locator('[name="document_resource"]')
    .selectOption(String(invoiceId));
  const docResult = await save(page, doc);
  const docLink = (await state(page)).public_links!.find(
    (row) => row.id === Number(docResult.identifier),
  )!;
  await guest.goto('/verify-document?locale=fr#' + docLink.public_id);
  await expect(
    guest.getByRole('heading', {
      name: text('documentStatus_valid'),
      exact: true,
    }),
  ).toBeVisible();
  await login(page, 'cleaner');
  await tab(page, 'planning');
  const physical = await form(page, 'physical');
  await physical
    .locator('[name="occupation"]')
    .selectOption(String(visit.occupation_id));
  for (const action of ['departure', 'start_cleaning', 'finish_cleaning']) {
    await expect(physical).toContainText(text(action));
    await save(page, physical);
  }
  const finalState = await state(page);
  expect(
    finalState.tables!.find((row) => row.id === table.id)!.physical_state,
  ).toBe('available');
  await guest.goto('/menu?locale=fr#' + link.public_id);
  await expect(
    guest.getByRole('heading', {
      name: text('visitStatus_ended'),
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    guest.getByRole('button', { name: text('requestFood'), exact: true }),
  ).toHaveCount(0);
  await page.screenshot({
    path: output + '/physical-cleaning-complete.png',
    fullPage: true,
  });
  await writeFile(
    output + '/ui-qr-journey.json',
    JSON.stringify(
      {
        result: 'PASS',
        root,
        tableLink: link,
        invoiceLink: docLink,
        orderId: order.order_id,
        occupationId: visit.occupation_id,
        invoiceId,
        invoiceTotal: '250.25',
        identity: 'simulated local RS256',
        persistence: 'real disposable PostgreSQL',
        notifications: 'local stored events only',
      },
      null,
      2,
    ),
  );
});

test('real QR and document views FR EN AR Light Dark mobile', async ({
  page,
}) => {
  const data = JSON.parse(
    await readFile(output + '/ui-qr-journey.json', 'utf-8'),
  );
  // A new browser tab has no earlier visit proof: menu stays public and cannot order.
  for (const locale of ['fr', 'en', 'ar'])
    for (const theme of ['light', 'dark'])
      for (const view of ['menu', 'verify-document']) {
        await page.setViewportSize({ width: 390, height: 900 });
        await page.addInitScript(
          ({ locale, theme }) => {
            localStorage.setItem('moulai.locale', locale);
            localStorage.setItem('moulai.theme', theme);
          },
          { locale, theme },
        );
        await page.goto(
          '/' +
            view +
            '?locale=' +
            locale +
            '#' +
            (view === 'menu'
              ? data.tableLink.public_id
              : data.invoiceLink.public_id),
        );
        await expect(page.locator('h2').first()).toBeVisible();
        await expect(page.locator('html')).toHaveAttribute(
          'dir',
          locale === 'ar' ? 'rtl' : 'ltr',
        );
        await page.evaluate(() => document.fonts.ready);
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
          path: output + '/' + view + '-' + locale + '-' + theme + '-390.png',
          fullPage: true,
        });
      }
});

test('actual retained prints and PDF QR rasters FR EN AR', async ({ page }) => {
  const data = JSON.parse(
    await readFile(output + '/ui-qr-journey.json', 'utf-8'),
  );
  await page.goto('/dining-local?branch=7000300');
  await login(page, 'owner');
  const manifest: Record<string, unknown>[] = [];
  for (const locale of ['fr', 'en', 'ar'])
    for (const [kind, link] of [
      ['table', data.tableLink],
      ['invoice', data.invoiceLink],
    ] as const) {
      await page.setViewportSize({ width: 794, height: 1123 });
      await page.goto(
        root + '/public-links/' + link.id + '/print?locale=' + locale,
      );
      await expect(page.locator('html')).toHaveAttribute('lang', locale);
      await expect(page.locator('html')).toHaveAttribute(
        'dir',
        locale === 'ar' ? 'rtl' : 'ltr',
      );
      const qr = page.locator('svg');
      await expect(qr).toBeVisible();
      await qr.screenshot({
        path: output + '/qr-' + kind + '-' + locale + '.png',
      });
      const url = await page.locator('a').getAttribute('href');
      manifest.push({
        image: 'qr-' + kind + '-' + locale + '.png',
        expected_url: url,
        source: 'screen raster',
        locale,
        kind,
      });
      await page.emulateMedia({ media: 'print' });
      const box = (await qr.boundingBox())!;
      await page.pdf({
        path: output + '/print-' + kind + '-' + locale + '.pdf',
        width: '794px',
        height: '1123px',
        margin: { top: 0, right: 0, bottom: 0, left: 0 },
        printBackground: true,
      });
      manifest.push({
        image: 'pdf-' + kind + '-' + locale + '-1.png',
        expected_url: url,
        source: 'actual PDF rendered at 96 DPI',
        crop: [box.x, box.y, box.width, box.height],
        locale,
        kind,
      });
      await page.screenshot({
        path: output + '/print-' + kind + '-' + locale + '.png',
        fullPage: true,
      });
      await page.emulateMedia({ media: 'screen' });
    }
  await writeFile(
    output + '/qr-image-manifest.json',
    JSON.stringify(manifest, null, 2),
  );
});

test('existing identity consents before owner activates professional functions', async ({
  page,
}) => {
  await page.addInitScript(() => localStorage.setItem('moulai.locale', 'fr'));
  await page.goto('/dining-local?branch=7000300');
  await login(page, 'owner');
  await tab(page, 'staff');
  const previous = (await state(page)).staff_profiles?.find(
    (row) => row.employee_code === 'EMP-UI-QR',
  );
  if (previous) {
    const revoke = await form(page, 'staff_status');
    await revoke
      .locator('[name="status_member"]')
      .selectOption(String(previous.membership_id));
    await revoke.locator('[name="staff_state"]').selectOption('revoked');
    await revoke
      .locator('[name="reason"]')
      .fill('Nouveau rattachement fictif pour vérifier le consentement');
    await save(page, revoke);
  }
  const invite = await form(page, 'staff_invite');
  await invite
    .locator('[name="issuer"]')
    .fill('https://dining.example.invalid/realms/synthetic');
  await invite
    .locator('[name="subject"]')
    .fill('synthetic-dining-7000000-new_employee');
  await invite.locator('[name="code"]').fill('EMP-UI-QR');
  await invite.locator('[name="name"]').fill('Employé fictif — recette QR');
  await save(page, invite);
  const member = (await state(page)).staff_profiles!.find(
    (row) => row.employee_code === 'EMP-UI-QR',
  )!.membership_id;
  await login(page, 'new_employee');
  const invitations = page
    .locator('details')
    .filter({ has: page.getByText(text('staffInvitations'), { exact: true }) });
  if ((await invitations.getAttribute('open')) === null)
    await invitations.locator('summary').click();
  await invitations
    .getByRole('button', { name: text('staffAccept'), exact: true })
    .click();
  await expect(invitations).toContainText(text('staffAccepted'));
  await login(page, 'owner');
  await tab(page, 'staff');
  const status = await form(page, 'staff_status');
  await status.locator('[name="status_member"]').selectOption(String(member));
  await status.locator('[name="staff_state"]').selectOption('active');
  await status
    .locator('[name="reason"]')
    .fill('Acceptation personnelle vérifiée localement');
  await save(page, status);
  for (const [code, fr, en, ar] of [
    ['ui-service', 'Service', 'Service', 'الخدمة'],
    ['ui-clean', 'Nettoyage', 'Cleaning', 'التنظيف'],
  ]) {
    const f = await form(page, 'staff_function');
    for (const [key, value] of Object.entries({
      functionCode: code,
      fr,
      en,
      ar,
      tasks: 'Responsabilité descriptive sans permission implicite',
    }))
      await f.locator('[name="' + key + '"]').fill(value!);
    await save(page, f);
    const definition = (await state(page)).staff_functions!.find(
      (row) => row.code === code,
    )!;
    const assign = await form(page, 'staff_assignment');
    await assign
      .locator('[name="assignment_member"]')
      .selectOption(String(member));
    await assign
      .locator('[name="function"]')
      .selectOption(String(definition.id));
    await save(page, assign);
  }
  const value = await state(page);
  expect(
    value.staff_assignments!.filter(
      (row) => row.membership_id === member && row.active,
    ),
  ).toHaveLength(2);
  expect(
    value.grants!.filter((row) => row.membership_id === member && row.active),
  ).toHaveLength(0);
  await page.screenshot({
    path: output + '/staff-consent-and-functions.png',
    fullPage: true,
  });
  const suspend = await form(page, 'staff_status');
  await suspend.locator('[name="status_member"]').selectOption(String(member));
  await suspend.locator('[name="staff_state"]').selectOption('suspended');
  await suspend.locator('[name="reason"]').fill('Suspension locale de recette');
  await save(page, suspend);
  expect(
    (await state(page)).memberships!.find((row) => row.id === member)!.status,
  ).toBe('suspended');
  await page.screenshot({
    path: output + '/staff-suspended.png',
    fullPage: true,
  });
});

test('persisted staff forms FR EN AR themes responsive and keyboard', async ({
  page,
}) => {
  await page.addInitScript(() => localStorage.setItem('moulai.locale', 'fr'));
  await page.goto('/dining-local?branch=7000300');
  await login(page, 'owner');
  // Remove no identities and submit no business commands in this visual read pass.
  for (const locale of ['fr', 'en', 'ar'] as const)
    for (const theme of ['light', 'dark'])
      for (const width of [1440, 390]) {
        await page.setViewportSize({ width, height: 1000 });
        await page.evaluate(
          ({ locale, theme }) => {
            localStorage.setItem('moulai.locale', locale);
            localStorage.setItem('moulai.theme', theme);
          },
          { locale, theme },
        );
        // The locale query is handled by the public page only, so change the actual preference after load.
        await page.goto('/dining-local?branch=7000300');
        const language = page.getByRole('combobox', {
          name: /Langue de l’interface|Interface language|لغة الواجهة/,
        });
        await language.click();
        await page
          .getByRole('option', {
            name: {
              fr: 'Français — FR',
              en: 'English — EN',
              ar: 'العربية — AR',
            }[locale],
            exact: true,
          })
          .click();
        const labels = { fr: serviceFr, en: serviceEn, ar: serviceAr }[locale];
        await page
          .getByRole('button', {
            name: labels['d1.section_staff'],
            exact: true,
          })
          .click();
        await expect(page.locator('html')).toHaveAttribute(
          'dir',
          locale === 'ar' ? 'rtl' : 'ltr',
        );
        const f = await form(page, 'staff_function');
        await f.locator('[name="functionCode"]').focus();
        await page.keyboard.press('Tab');
        await expect(f.locator('[name="fr"]')).toBeFocused();
        expect(
          await f
            .locator('[name="fr"]')
            .evaluate((el) => getComputedStyle(el).outlineStyle),
        ).not.toBe('none');
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
          path:
            output + '/staff-' + locale + '-' + theme + '-' + width + '.png',
          fullPage: true,
        });
      }
});

test('real reservation and receipt QR retain funds after cancellation', async ({
  page,
}) => {
  await page.addInitScript(() => localStorage.setItem('moulai.locale', 'fr'));
  await page.goto('/dining-local?branch=7000300');
  await login(page, 'owner');
  const origin = 'http://127.0.0.1:5574';
  const post = async (
    path: string,
    body: unknown,
    headers: Record<string, string> = {},
  ) => {
    const response = await page.request.post(path, {
      data: body,
      headers: { Origin: origin, ...headers },
    });
    expect(response.status(), await response.text()).toBe(200);
    return response.json() as Promise<unknown>;
  };
  const identifier = z.object({ identifier: z.number().int().positive() });
  const initial = await state(page),
    table = initial.tables!.find((row) => row.code === 'T2')!;
  const session = z
    .object({ customer_proofs: z.record(z.string()) })
    .parse(await (await page.request.get('/local-d1/session')).json());
  const start = new Date(Date.now() + 7200000).toISOString(),
    end = new Date(Date.parse(start) + 5400000).toISOString();
  const request = identifier.parse(
    await post(
      root + '/commands',
      {
        operation: 'request',
        data: {
          customer_name: 'Client fictif du reçu QR',
          contact: 'receipt-qr@example.invalid',
          starts_at: start,
          duration_seconds: 5400,
          party_size: 4,
          table_ids: [table.id],
          criteria: {},
          event_id: null,
          preparation: false,
          menu: [],
        },
      },
      { 'X-Customer-Proof': session.customer_proofs['7000300']! },
    ),
  ).identifier;
  const quote = identifier.parse(
    await post(root + '/commands', {
      operation: 'quote',
      request_id: request,
      currency: 'DZD',
      expires_at: new Date(Date.now() + 1200000).toISOString(),
    }),
  ).identifier;
  const proposal = (await state(page)).quotes!.find((row) => row.id === quote)!;
  await post('/local-d1/session', { actor: 'customer' });
  await post(
    '/local-d1/dining/restaurants/7000200/branches/7000300/quotes/' +
      quote +
      '/accept',
    { digest: proposal.digest },
  );
  await post('/local-d1/session', { actor: 'owner' });
  await post(root + '/commands', {
    operation: 'hold',
    request_id: request,
    quote_id: quote,
  });
  const receipt = z.object({ receipt_id: z.number().int().positive() }).parse(
    await post(root + '/receipts', {
      request_id: request,
      quote_id: quote,
      received_amount: proposal.amount,
      currency: 'DZD',
      mode: 'cash',
      reference: 'SYNTHETIC-QR-' + Date.now(),
      received_at: new Date().toISOString(),
    }),
  ).receipt_id;
  await post(root + '/commands', {
    operation: 'human_proof',
    request_id: request,
    table_ids: [table.id],
    starts_at: start,
    ends_at: end,
  });
  await post(root + '/commands', {
    operation: 'confirm_human',
    request_id: request,
    quote_id: quote,
    receipt_id: receipt,
  });
  const emitted = z.object({
    identifier: z.number().int().positive(),
    public_id: z.string(),
    reference: z.string(),
  });
  const issuedReceipt = emitted.parse(
    await post(root + '/public-links', {
      operation: 'issue',
      kind: 'receipt',
      resource_id: receipt,
    }),
  );
  const issuedReservation = emitted.parse(
    await post(root + '/public-links', {
      operation: 'issue',
      kind: 'reservation',
      resource_id: request,
    }),
  );
  for (const [kind, document] of [
    ['receipt', issuedReceipt],
    ['reservation', issuedReservation],
  ] as const) {
    await page.goto(
      root + '/public-links/' + document.identifier + '/print?locale=fr',
    );
    await expect(page.locator('svg')).toBeVisible();
    await page
      .locator('svg')
      .screenshot({ path: output + '/qr-' + kind + '-extra.png' });
    await page.screenshot({
      path: output + '/print-' + kind + '-extra.png',
      fullPage: true,
    });
    const url = await page.locator('a').getAttribute('href');
    const manifest = JSON.parse(
      await readFile(output + '/qr-image-manifest.json', 'utf-8'),
    ) as Record<string, unknown>[];
    manifest.push({
      image: 'qr-' + kind + '-extra.png',
      expected_url: url,
      source: 'actual private document screenshot',
      locale: 'fr',
      kind,
    });
    await writeFile(
      output + '/qr-image-manifest.json',
      JSON.stringify(manifest, null, 2),
    );
  }
  await post(root + '/commands', {
    operation: 'cancel_before_arrival',
    request_id: request,
    reason: 'Annulation de recette locale avant arrivée',
    origin: 'customer',
  });
  const verification = z.object({ status: z.string(), reference: z.string() });
  expect(
    verification.parse(
      await post('/local-d1/dining/public/verify', {
        public_id: issuedReservation.public_id,
      }),
    ).status,
  ).toBe('cancelled');
  expect(
    verification.parse(
      await post('/local-d1/dining/public/verify', {
        public_id: issuedReceipt.public_id,
      }),
    ).status,
  ).toBe('valid');
  const final = await state(page);
  expect(final.receipts!.find((row) => row.id === receipt)!.status).toBe(
    'verified',
  );
  await page.goto('/verify-document?locale=fr#' + issuedReservation.public_id);
  await expect(
    page.getByRole('heading', {
      name: text('documentStatus_cancelled'),
      exact: true,
    }),
  ).toBeVisible();
  await page.screenshot({
    path: output + '/cancelled-issued-document.png',
    fullPage: true,
  });
  await writeFile(
    output + '/receipt-document-proof.json',
    JSON.stringify(
      {
        result: 'PASS',
        reservation: request,
        receipt,
        issuedReceipt,
        issuedReservation,
        receipt_retained: true,
        automatic_refund: false,
        remote_payment: false,
        synthetic_receipt_recorded: true,
        identity: 'simulated local RS256',
        data: 'fictional only',
      },
      null,
      2,
    ),
  );
});

// Visual fixtures request a manual choice; opening policy is checked independently.
test.beforeEach(async ({ page }) => installManualThemeFixture(page));

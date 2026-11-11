// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Positive integrated journey with distinct real local identities and a real lost-response retry.
import assert from 'node:assert/strict';
import { redactLocalMessage } from '../src/shared/access/logSafety.ts';
import { d1Fr } from '../src/shared/i18n/d1.fr.ts';
import { serviceFr } from '../src/shared/i18n/diningService.ts';
import { interfaceQuality } from '../src/shared/i18n/interfaceQuality.ts';
import fs from 'node:fs';
import path from 'node:path';
import AxeBuilder from '@axe-core/playwright';
import { roundedCents } from './exactAcceptanceMoney.mjs';
import {
  launch,
  login,
  newContext,
  request,
  checked,
  command,
  snapshot,
  form,
  save,
  wall,
  accounts,
  root,
  output as fixtureOutput,
  origin,
  route,
  screen,
} from './operationalHarness.mjs';
const output = path.join(
  root,
  process.argv.includes('--documents')
    ? 'artifacts/interface-documents-20261110/restaurant'
    : process.argv.includes('--interface-quality')
      ? 'artifacts/interface-consolidation-20261110/restaurant'
      : process.argv.includes('--staging-followup')
        ? 'artifacts/staging-local-followup-20261110/restaurant'
        : 'artifacts/operational-followup-20261109/dining-o4',
);
fs.mkdirSync(output, { recursive: true });
const browser = await launch(),
  results = [];
const text = (key) =>
  ({ ...d1Fr, ...serviceFr, ...interfaceQuality.fr })['d1.' + key];
let phase = 'owner-connection';
const mark = (label, values = {}) =>
  results.push({ label, status: 'PASS', ...values });
const catalogue = JSON.parse(
  fs.readFileSync(path.join(fixtureOutput, 'catalogue.json'), 'utf8'),
);
async function tab(page, name) {
  await page.getByRole('button', { name, exact: true }).click();
}
try {
  const owner = await login(browser, 'owner-a');
  const ownerState = await snapshot(owner);
  assert(ownerState.policy);
  const pages = {};
  const capabilities = {
    'd1-service': [
      'read',
      'service',
      'orders.read',
      'orders.approve',
      'orders.complete',
    ],
    'd1-kitchen': ['read', 'orders.read', 'orders.prepare'],
    'd1-collector': [
      'read',
      'finance.read',
      'collect',
      'invoices.create',
      'invoices.finalize',
      'documents.issue',
    ],
    'd1-cleaner': ['read', 'clean'],
  };
  for (const [username, caps] of Object.entries(capabilities)) {
    phase = 'membership-' + username;
    let state = await snapshot(owner);
    const profile = state.staff_profiles.find(
      (p) => p.employee_code === username.toUpperCase(),
    );
    let member = profile
      ? state.memberships.find((m) => m.id === profile.membership_id)
      : null;
    if (!member) {
      const invitation = checked(
        await request(owner, route + '/staff', {
          operation: 'invite',
          issuer: accounts[username].issuer,
          subject: accounts[username].subject,
          employee_code: username.toUpperCase(),
          display_name: username + ' — LOCAL DEV',
        }),
      );
      member = { id: invitation.identifier };
    }
    const page = await login(browser, username);
    pages[username] = page;
    state = await snapshot(owner);
    member = state.memberships.find((m) => m.id === member.id);
    if (member.status !== 'active') {
      checked(
        await request(
          page,
          `/api/web/dining/employment/8/${member.id}/accept`,
          {},
        ),
      );
      state = await snapshot(owner);
      member = state.memberships.find((m) => m.id === member.id);
      checked(
        await request(owner, route + '/staff', {
          operation: 'status',
          membership_id: member.id,
          expected_revision: member.revision,
          status: 'active',
          reason: 'Explicit isolated operational journey',
        }),
      );
    }
    for (const capability of caps)
      if (
        !state.grants.some(
          (g) =>
            g.membership_id === member.id &&
            g.capability === capability &&
            g.active,
        )
      )
        await command(owner, {
          operation: 'grant',
          membership_id: member.id,
          capability,
          actor_kind: 'human',
          active: true,
        });
    mark('real-account-personal-acceptance-and-explicit-grants', {
      username,
      membership: member.id,
      capabilities: caps,
    });
  }
  phase = 'owner-reference-and-table';
  const refs = {};
  for (const [kind, fr, en, ar] of [
    ['shape', 'Ronde — développement', 'Round — development', 'دائرية — تطوير'],
    [
      'category',
      'Standard — développement',
      'Standard — development',
      'عادية — تطوير',
    ],
    [
      'zone',
      'Salle — développement',
      'Dining room — development',
      'قاعة — تطوير',
    ],
    [
      'location',
      'Intérieur — développement',
      'Indoors — development',
      'داخل القاعة — تطوير',
    ],
  ]) {
    const code = kind === 'shape' ? 'round' : 'operational-o2-' + kind;
    const existing = (await snapshot(owner)).references.find(
      (r) => r.code === code,
    );
    refs[kind] =
      existing?.id ??
      (
        await command(owner, {
          operation: 'reference',
          data: {
            kind,
            code,
            labels: { fr, en, ar },
            active: true,
            pricing_ref: null,
          },
        })
      ).identifier;
  }
  const tableCode = 'DEV-' + Date.now();
  const table = (
    await command(owner, {
      operation: 'table',
      initial_state: 'available',
      data: {
        code: tableCode,
        name: 'Table de développement intégrée',
        min_capacity: 1,
        max_capacity: 4,
        shape_id: refs.shape,
        category_id: refs.category,
        zone_id: refs.zone,
        location_id: refs.location,
        description: 'Explicit isolated development table',
        floor_label: 'RDC — LOCAL DEV',
        room_label: 'Salle — LOCAL DEV',
        photos: [],
        pricing_ref: 'development-table',
        in_service: true,
        trait_ids: [],
      },
    })
  ).identifier;
  const today = wall(Date.now()).slice(0, 10);
  await command(owner, {
    operation: 'calendar',
    weekday: null,
    service_date: today,
    windows: [{ start: '00:00', end: '00:00', next_day: true }],
  });
  for (const product of catalogue.products) {
    const previous = (await snapshot(owner)).tariffs.find(
      (t) =>
        t.reference === 'public-product:' + product.id && t.currency === 'DZD',
    );
    if (!previous)
      await command(owner, {
        operation: 'tariff',
        data: {
          reference: 'public-product:' + product.id,
          component: 'menu',
          currency: 'DZD',
          unit: 'per_item',
          unit_price: product.exact_public_price,
          valid_from: new Date(Date.now() - 86400000).toISOString(),
          valid_until: null,
        },
      });
  }
  let state = await snapshot(owner);
  const link = state.public_links.find(
    (l) => l.kind === 'table' && l.table_id === table,
  );
  assert(link && link.active);
  mark('persisted-owner-table-calendar-and-exact-menu', {
    table,
    tableCode,
    products: catalogue.products.map((p) => p.id),
  });
  phase = 'customer-qr-menu';
  const customerContext = await newContext(browser),
    guest = await customerContext.newPage();
  const exported = await owner.request.get(
    origin + route + `/public-links/${link.id}/qr?locale=fr`,
  );
  assert.equal(exported.status(), 200);
  const svg = await exported.text();
  assert(svg.includes('<svg') && svg.includes('<path'));
  const qrPage = await customerContext.newPage();
  await qrPage.setContent(
    `<html><body style="background:white;padding:32px">${svg}</body></html>`,
  );
  const qrImage = await qrPage
    .locator('svg')
    .screenshot({ path: path.join(output, 'table-qr-export.png') });
  const nativeDecoder = await qrPage.evaluate(
    () => typeof BarcodeDetector === 'function',
  );
  if (nativeDecoder) {
    const decoded = await qrPage.evaluate(async (encoded) => {
      const bytes = Uint8Array.from(atob(encoded), (c) => c.charCodeAt(0));
      const image = await createImageBitmap(
        new Blob([bytes], { type: 'image/png' }),
      );
      const rows = await new BarcodeDetector({ formats: ['qr_code'] }).detect(
        image,
      );
      return rows[0]?.rawValue;
    }, qrImage.toString('base64'));
    assert(decoded);
    const decodedUrl = new URL(decoded);
    assert.equal(decodedUrl.origin, origin);
    assert.equal(decodedUrl.pathname, '/menu');
    assert.equal(decodedUrl.hash, '#' + link.public_id);
  }
  await qrPage.close();
  mark('actual-server-QR-export', {
    native_decode: nativeDecoder
      ? 'verified'
      : 'unavailable-in-installed-browser',
    physical_phone_scan: 'NOT TESTED',
  });
  await guest.goto(origin + '/menu?locale=fr#' + link.public_id);
  await guest.getByRole('heading', { name: new RegExp(tableCode) }).waitFor();
  await guest.getByLabel('Devise', { exact: true }).selectOption('DZD');
  state = await snapshot(owner);
  assert.equal(
    state.tables.find((t) => t.id === table).physical_state,
    'available',
  );
  mark('QR-read-does-not-confirm-presence-or-occupation');
  await guest.getByLabel(text('partySize'), { exact: true }).fill('4');
  await guest
    .getByRole('button', { name: text('signalPresence'), exact: true })
    .click();
  await guest
    .getByRole('heading', { name: text('visitStatus_pending'), exact: true })
    .waitFor();
  phase = 'observed-human-installation';
  const service = pages['d1-service'];
  await service.goto(origin + screen);
  await tab(service, text('section_visits'));
  let install = await form(service, 'install_presence');
  state = await snapshot(owner);
  const presence = state.presence_signals.find(
    (s) => s.table_id === table && s.status === 'pending',
  );
  assert(presence);
  await install.locator('[name="presence"]').selectOption(String(presence.id));
  await install.locator('[name="end"]').fill(wall(Date.now() + 2700000));
  await install.locator('[name="observed"]').check();
  await save(service, install);
  await guest.getByRole('button', { name: 'Actualiser', exact: true }).click();
  await guest
    .getByRole('heading', { name: text('visitStatus_active'), exact: true })
    .waitFor();
  state = await snapshot(owner);
  assert.equal(
    state.tables.find((t) => t.id === table).physical_state,
    'occupied',
  );
  mark('staff-observed-installation-before-order');
  phase = 'order-response-loss-and-retry';
  const product = catalogue.products[0];
  await guest
    .getByLabel(product.name + ' — ' + text('quantity'), { exact: true })
    .fill('2');
  if (process.argv.includes('--interface-quality')) {
    await guest.setViewportSize({ width: 390, height: 844 });
    await guest.screenshot({
      path: path.join(output, 'cart-mobile-before-request.png'),
      fullPage: true,
    });
  }
  let firstOrderId;
  await guest.route(
    '**/api/web/dining/public/orders',
    async (intercepted) => {
      const received = await intercepted.fetch();
      assert.equal(received.status(), 200);
      firstOrderId = (await received.json()).identifier;
      await intercepted.abort();
    },
    { times: 1 },
  );
  await guest
    .getByRole('button', { name: text('requestFood'), exact: true })
    .click();
  await guest.getByRole('alert').waitFor();
  state = await snapshot(service);
  assert(state.visit_orders.some((o) => o.order_id === firstOrderId));
  await guest.getByRole('button', { name: 'Actualiser', exact: true }).click();
  await guest
    .getByRole('button', { name: text('requestFood'), exact: true })
    .click();
  await guest
    .getByRole('heading', { name: new RegExp('#' + firstOrderId + ' — ') })
    .waitFor();
  state = await snapshot(service);
  assert.equal(
    state.visit_orders.filter((o) => o.order_id === firstOrderId).length,
    1,
  );
  mark('lost-real-response-retry-one-persisted-order', { order: firstOrderId });
  phase = 'separate-service-and-kitchen';
  const order = state.visit_orders.find((o) => o.order_id === firstOrderId);
  const visit = state.visits.find((v) => v.id === order.visit_id);
  checked(
    await request(service, route + '/visit-orders/transition', {
      order_id: firstOrderId,
      action: 'prepare',
      observed: true,
    }),
    403,
  );
  await service.reload();
  await tab(service, text('section_visits'));
  async function transition(page, action) {
    const f = await form(page, 'visit_order_transition');
    await f.locator('[name="visit_order"]').selectOption(String(firstOrderId));
    await f.locator('[name="visit_action"]').selectOption(action);
    await f.locator('[name="observed_order"]').check();
    await save(page, f);
  }
  await transition(service, 'approve');
  const kitchen = pages['d1-kitchen'];
  await kitchen.goto(origin + screen);
  await tab(kitchen, text('section_visits'));
  checked(
    await request(kitchen, route + '/visit-orders/transition', {
      order_id: firstOrderId,
      action: 'approve',
      observed: true,
    }),
    403,
  );
  await transition(kitchen, 'prepare');
  await transition(kitchen, 'ready');
  await service.reload();
  await tab(service, text('section_visits'));
  await transition(service, 'served');
  await transition(service, 'served');
  mark('service-approval-kitchen-preparation-ready-and-service', {
    repeated_service: 'same business state',
  });
  phase = 'actual-invoice-forms';
  const finance = pages['d1-collector'];
  await finance.goto(origin + screen);
  await tab(finance, text('section_finance'));
  const invoiceForm = await form(finance, 'invoice');
  await invoiceForm.locator('input[type="checkbox"]').first().check();
  await invoiceForm
    .locator('[name="occupation"]')
    .selectOption(String(visit.occupation_id));
  await invoiceForm.locator(`[name="orders"][value="${firstOrderId}"]`).check();
  await invoiceForm
    .locator('[name="currency_source"]')
    .fill('Explicit LOCAL DEV exact DZD public tariff');
  await invoiceForm
    .locator('[name="rounding_source"]')
    .fill('Final HALF_UP, 2 decimal places, existing contract');
  await invoiceForm
    .locator('[name="reconciliation"]')
    .fill('Exact real public-order snapshot, local development only');
  const drafted = await save(finance, invoiceForm);
  const invoiceId = drafted.identifier;
  const finalize = await form(finance, 'finalize_invoice');
  await finalize.locator('[name="invoice"]').selectOption(String(invoiceId));
  await save(finance, finalize);
  let issuedDocument;
  let frozenBeforePayment;
  const ownInvoiceView = async () =>
    guest.evaluate(async (publicId) => {
      const response = await fetch('/api/web/dining/public/invoice?locale=fr', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Visit-Token': sessionStorage.getItem('moulai-visit:' + publicId),
        },
        body: JSON.stringify({ public_id: publicId }),
      });
      return { status: response.status, data: await response.json() };
    }, link.public_id);
  if (process.argv.includes('--documents')) {
    phase = 'explicit-human-invoice-document-issuance';
    const unissued = await ownInvoiceView();
    assert.equal(unissued.status, 200);
    assert.equal(unissued.data.document.status, 'unissued');
    assert(!('qr_svg' in unissued.data.document));
    frozenBeforePayment = unissued.data.lines;
    checked(
      await request(service, route + '/public-links', {
        operation: 'issue',
        kind: 'food_invoice',
        resource_id: invoiceId,
        public_physical_state: false,
        reason: 'LOCAL TEST ONLY',
      }),
      403,
    );
    await tab(finance, text('section_visits'));
    const documentForm = await form(finance, 'public_link');
    await documentForm
      .locator('[name="document_kind"]')
      .selectOption('food_invoice');
    await documentForm
      .locator('[name="document_resource"]')
      .selectOption(String(invoiceId));
    issuedDocument = await save(finance, documentForm);
    const issued = await ownInvoiceView();
    assert.equal(issued.data.document.status, 'issued');
    assert.equal(issued.data.document.reference, issuedDocument.reference);
    assert.equal(issued.data.document.version, issuedDocument.version);
    assert.equal(
      new URL(issued.data.document.url).hash,
      '#' + issuedDocument.public_id,
    );
    assert.notEqual(issuedDocument.public_id, link.public_id);
    const noVisitSecret = await guest.evaluate(
      (url) =>
        !url.includes(
          sessionStorage.getItem('moulai-visit:' + location.hash.slice(1)),
        ),
      issued.data.document.url,
    );
    assert(noVisitSecret);
    const exported = await finance.request.get(
      origin +
        route +
        '/public-links/' +
        issuedDocument.identifier +
        '/qr?locale=fr',
    );
    assert.equal(exported.status(), 200);
    assert.equal(await exported.text(), issued.data.document.qr_svg);
    const verification = checked(
      await request(guest, '/api/web/dining/public/verify', {
        public_id: issuedDocument.public_id,
      }),
    );
    assert.equal(verification.status, 'valid');
    assert.equal(verification.kind, 'food_invoice');
    assert.equal(verification.reference, issuedDocument.reference);
    const invalid = checked(
      await request(guest, '/api/web/dining/public/verify', {
        public_id: 'Z'.repeat(43),
      }),
    );
    assert.equal(invalid.status, 'invalid');
    checked(
      await request(
        guest,
        '/api/web/dining/public/invoice',
        { public_id: issuedDocument.public_id },
        { 'X-Visit-Token': 'A'.repeat(43) },
      ),
      409,
    );
    mark('exact-invoice-QR-reuses-human-issuance-and-encoder', {
      permissionRefused: 403,
      publicVerification: 'valid and matching invoice document',
      svgMatchesAuthorizedExport: true,
      independentQrDecoding: 'NOT PERFORMED',
      physicalPhoneScan: 'NOT PERFORMED',
    });
    await tab(finance, text('section_finance'));
  }
  checked(
    await request(service, route + `/invoices/${invoiceId}/balance`),
    403,
  );
  phase = 'verified-human-receipt-form';
  const receipt = await form(finance, 'settlement');
  await receipt.locator('[name="invoice"]').selectOption(String(invoiceId));
  await receipt.getByTestId('invoice-balance').waitFor();
  const before = checked(
    await request(finance, route + `/invoices/${invoiceId}/balance`),
  );
  assert.equal(Number(before.total), 1200);
  assert.equal(Number(before.balance), 1200);
  const receiptReference = 'LOCAL-NO-FUNDS-' + Date.now(),
    received = wall(Date.now() - 60000);
  for (const [name, value] of Object.entries({
    amount: '1200',
    reference: receiptReference,
    received,
  }))
    await receipt.locator(`[name="${name}"]`).fill(value);
  await receipt.locator('[name="currency"]').selectOption('DZD');
  await receipt.locator('[name="mode"]').selectOption('cash');
  await receipt.locator('[name="observed"]').check();
  const recorded = await save(finance, receipt);
  assert.equal(Number(recorded.balance), 0);
  const receivedInstant = checked(
    await request(
      finance,
      route +
        `/instant?day=${received.slice(0, 10)}&wall_time=${encodeURIComponent(received.slice(11))}`,
    ),
  );
  const payload = {
    amount: '1200',
    currency: 'DZD',
    mode: 'cash',
    reference: receiptReference,
    received_at: receivedInstant.instant,
    observed: true,
  };
  checked(
    await request(
      service,
      route + `/invoices/${invoiceId}/settlement`,
      payload,
    ),
    403,
  );
  checked(
    await request(
      service,
      '/api/web/dining/public/invoice',
      { public_id: link.public_id },
      { 'X-Visit-Token': 'A'.repeat(43) },
    ),
    409,
  );
  mark('staff-cookie-cannot-substitute-for-customer-proof-or-collection-grant');
  const repeats = await Promise.all([
    request(finance, route + `/invoices/${invoiceId}/settlement`, payload),
    request(finance, route + `/invoices/${invoiceId}/settlement`, payload),
  ]);
  for (const replay of repeats) {
    checked(replay);
    assert.equal(replay.body.settlement_id, recorded.settlement_id);
  }
  await guest.getByRole('button', { name: 'Actualiser', exact: true }).click();
  await guest.getByTestId('own-invoice').waitFor();
  assert.match(
    await guest.getByTestId('own-invoice').innerText(),
    /(?:^|\s)0(?:[.]0+)?\s+DZD/,
  );
  await guest.reload();
  await guest.getByTestId('own-invoice').waitFor();
  if (process.argv.includes('--documents')) {
    const afterPayment = await ownInvoiceView();
    assert.deepEqual(afterPayment.data.lines, frozenBeforePayment);
    assert.equal(
      afterPayment.data.document.reference,
      issuedDocument.reference,
    );
    assert.equal(afterPayment.data.balance, '0.00000000');
    mark(
      'payment-changes-balance-without-rewriting-invoice-or-issued-reference',
    );
  }
  if (process.argv.includes('--interface-quality')) {
    const projection = await guest.evaluate(async (publicId) => {
      const response = await fetch('/api/web/dining/public/invoice', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-Visit-Token': sessionStorage.getItem('moulai-visit:' + publicId),
        },
        body: JSON.stringify({ public_id: publicId }),
      });
      return { status: response.status, data: await response.json() };
    }, link.public_id);
    assert.equal(projection.status, 200);
    assert.equal(projection.data.invoice_id, invoiceId);
    assert.equal(projection.data.balance, '0.00000000');
    assert(projection.data.finalized_at && projection.data.revision);
    assert.equal(projection.data.lines.length, 1);
    assert.equal(projection.data.lines[0].description, product.name);
    assert.equal(Number(projection.data.lines[0].quantity), 2);
    assert.equal(roundedCents(projection.data.lines[0].amount), 120000n);
    for (const line of projection.data.lines)
      assert.deepEqual(Object.keys(line).sort(), [
        'amount',
        'description',
        'quantity',
        'unit_price',
      ]);
    assert(
      !('provenance' in projection.data) &&
        !('finalized_by' in projection.data),
    );
    await guest
      .getByTestId('own-invoice')
      .locator('table tbody tr')
      .last()
      .waitFor();
    mark('own-frozen-invoice-projection-without-staff-provenance', {
      lines: projection.data.lines.length,
      revision: projection.data.revision,
      timestampFromServer: true,
    });
  }
  mark('final-invoice-and-single-verified-local-ledger-receipt', {
    invoiceId,
    settlementId: recorded.settlement_id,
    total: '1200 DZD',
    paid: '1200 DZD',
    balance: '0 DZD',
    funds: 'explicit synthetic development declaration; no real funds',
  });
  phase = 'departure-and-cleaning';
  const cleaner = pages['d1-cleaner'];
  await cleaner.goto(origin + screen);
  const physical = await form(cleaner, 'physical');
  await physical
    .locator('[name="occupation"]')
    .selectOption(String(visit.occupation_id));
  for (const action of ['departure', 'start_cleaning', 'finish_cleaning'])
    await save(cleaner, physical);
  state = await snapshot(owner);
  assert.equal(
    state.tables.find((t) => t.id === table).physical_state,
    'available',
  );
  await guest.reload();
  await guest.getByTestId('own-invoice').waitFor();
  mark(
    'departure-cleaning-and-own-invoice-readable-without-reopening-ordering',
  );
  phase = 'comparative-captures';
  const captures = [];
  for (const locale of ['fr', 'en', 'ar']) {
    await guest.evaluate(
      (locale) => localStorage.setItem('moulai.locale', locale),
      locale,
    );
    await guest.goto(origin + '/menu?locale=' + locale + '#' + link.public_id);
    await guest.getByTestId('own-invoice').waitFor();
    for (const theme of ['light', 'dark'])
      for (const [size, dimensions] of Object.entries({
        desktop: { width: 1440, height: 1000 },
        mobile: { width: 390, height: 844 },
      })) {
        await guest.setViewportSize(dimensions);
        await guest.evaluate(
          (theme) => window.moulaiTheme.choose(theme),
          theme,
        );
        const file = `customer-invoice-${locale}-${theme}-${size}.png`;
        assert.equal(
          await guest.evaluate(
            () => document.documentElement.scrollWidth > innerWidth + 1,
          ),
          false,
        );
        await guest.screenshot({
          path: path.join(output, file),
          fullPage: true,
          animations: 'disabled',
        });
        if (process.argv.includes('--interface-quality') && size === 'mobile') {
          const accessibility = await new AxeBuilder({ page: guest })
            .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
            .analyze();
          const receipt = {
            violations: accessibility.violations.map((row) => ({
              id: row.id,
              targets: row.nodes.map((node) => node.target),
            })),
            incomplete: accessibility.incomplete.map((row) => row.id),
          };
          fs.writeFileSync(
            path.join(output, `accessibility-${locale}-${theme}.json`),
            JSON.stringify(receipt, null, 2),
          );
          assert.equal(accessibility.violations.length, 0);
        }
        captures.push(file);
      }
    if (process.argv.includes('--interface-quality')) {
      await guest.emulateMedia({ media: 'print' });
      await guest
        .locator('[data-print-invoice] img')
        .first()
        .evaluate((image) => image.decode());
      await guest.screenshot({
        path: path.join(output, `print-${locale}.png`),
        fullPage: true,
      });
      if (process.argv.includes('--documents')) {
        const printableSnapshot = await guest.evaluate(
          async ({ publicId, locale }) => {
            const response = await fetch(
              '/api/web/dining/public/invoice?locale=' + locale,
              {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  'X-Visit-Token': sessionStorage.getItem(
                    'moulai-visit:' + publicId,
                  ),
                },
                body: JSON.stringify({ public_id: publicId }),
              },
            );
            return { status: response.status, invoice: await response.json() };
          },
          { publicId: link.public_id, locale },
        );
        assert.equal(printableSnapshot.status, 200);
        fs.writeFileSync(
          path.join(output, `print-snapshot-${locale}.json`),
          JSON.stringify(
            {
              source:
                'actual authorized local visit read; no visit credential retained',
              ...printableSnapshot,
            },
            null,
            2,
          ),
        );
        await guest.pdf({
          path: path.join(output, `invoice-${locale}.pdf`),
          format: 'A4',
          preferCSSPageSize: true,
          printBackground: true,
          tagged: true,
        });
      }
      await guest.emulateMedia({ media: 'screen' });
    }
  }
  if (process.argv.includes('--documents')) {
    phase = 'invalidated-emission-and-checked-print';
    await guest.evaluate(() => {
      window.__localPrintCalls = 0;
      window.print = () => {
        window.__localPrintCalls++;
      };
    });
    checked(
      await request(finance, route + '/public-links', {
        operation: 'disable',
        kind: 'food_invoice',
        resource_id: invoiceId,
        public_physical_state: false,
        reason: 'LOCAL invalidation proof, no financial change',
      }),
    );
    const invalidated = checked(
      await request(guest, '/api/web/dining/public/verify', {
        public_id: issuedDocument.public_id,
      }),
    );
    assert.equal(invalidated.status, 'invalidated');
    const readAgain = await ownInvoiceView();
    assert.equal(readAgain.data.document.status, 'invalidated');
    assert(
      !('url' in readAgain.data.document) &&
        !('qr_svg' in readAgain.data.document),
    );
    await guest.getByTestId('own-invoice').getByRole('button').click();
    await guest.waitForFunction(() => window.__localPrintCalls === 1);
    assert.equal(
      await guest
        .getByTestId('own-invoice')
        .locator('img[alt*="QR"], img[alt*="رمز"]')
        .count(),
      0,
    );
    await guest.screenshot({
      path: path.join(output, 'invoice-invalidated.png'),
      fullPage: true,
    });
    let reads = 0;
    await guest.route('**/api/web/dining/public/invoice*', (r) => {
      reads++;
      return r.fulfill({
        status: 503,
        contentType: 'application/json',
        body: '{}',
      });
    });
    await guest.getByTestId('own-invoice').getByRole('button').click();
    await guest.getByRole('alert').waitFor();
    assert.equal(await guest.evaluate(() => window.__localPrintCalls), 1);
    assert.equal(reads, 1);
    assert.equal(
      await guest.getByTestId('own-invoice').locator('table tbody tr').count(),
      1,
    );
    mark('disabled-QR-live-rejection-and-read-before-print-no-blind-retry', {
      financialWrites: 0,
      invoicePreservedOnReadFailure: true,
    });
  }
  const previous = path.join(output, 'dining-journey.json');
  if (fs.existsSync(previous))
    fs.copyFileSync(
      previous,
      path.join(output, 'dining-journey-previous-' + Date.now() + '.json'),
    );
  fs.writeFileSync(
    path.join(output, 'dining-journey.json'),
    JSON.stringify(
      {
        status: 'PASS',
        results,
        captures,
        table,
        order: firstOrderId,
        occupation: visit.occupation_id,
        invoice: invoiceId,
        settlement: recorded.settlement_id,
        identity: 'actual isolated Keycloak accounts',
        database: 'actual isolated PostgreSQL',
        external_funds: false,
      },
      null,
      2,
    ),
  );
  console.log(
    JSON.stringify({
      status: 'PASS',
      checks: results.length,
      captures: captures.length,
    }),
  );
} catch (error) {
  const file = path.join(
    output,
    'dining-journey-failure-' + Date.now() + '.json',
  );
  let message = redactLocalMessage(error.message ?? '');
  for (const account of Object.values(accounts))
    message = message.replaceAll(account.password, '[REDACTED]');
  fs.writeFileSync(
    file,
    JSON.stringify(
      {
        status: 'FAIL',
        phase,
        type: error.name,
        httpStatus: error.safeStatus,
        domainCode: error.safeCode,
        message,
        results,
      },
      null,
      2,
    ),
  );
  console.log(
    JSON.stringify({
      status: 'FAIL',
      phase,
      type: error.name,
      httpStatus: error.safeStatus,
      domainCode: error.safeCode,
    }),
  );
  process.exitCode = 1;
} finally {
  await browser.close();
}

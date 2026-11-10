// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Explicit visual fixture only: never a proof of authentication, receipt or invoice persistence.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { launch, newContext, origin, root } from './operationalHarness.mjs';

const output = path.join(
  root,
  'artifacts/interface-consolidation-20261110/invoice-visual-fixture',
);
fs.mkdirSync(output, { recursive: true });
const labels = {
  fr: 'VISUAL FIXTURE',
  en: 'VISUAL FIXTURE',
  ar: 'نموذج بصري للاختبار',
};
const reference = 'V'.repeat(43);
const invoice = {
  status: 'finalized',
  invoice_id: 90001,
  currency: 'DZD',
  total: '1200.00000000',
  advance: '0.00000000',
  paid: '1200.00000000',
  balance: '0.00000000',
  settlement_id: 90001,
  revision: 2,
  finalized_at: '2026-11-10T12:00:00Z',
  lines: [
    {
      description: 'VISUAL FIXTURE — Plat / طبق تجريبي',
      quantity: '2',
      unit_price: '600.00000000',
      amount: '1200.00000000',
    },
  ],
};
const menu = {
  reference,
  restaurant: 'VISUAL FIXTURE — Restaurant',
  branch: 'VISUAL FIXTURE — Branch',
  currency: 'DZD',
  precision: 2,
  currencies: ['DZD'],
  menu_digest: 'a'.repeat(64),
  scan_confirms_presence: false,
  availability_certified: false,
  table: {
    code: 'VISUAL-01',
    floor: '1',
    room: null,
    zone: labels,
    location: labels,
    physical_state: 'available',
  },
  products: [],
};
const browser = await launch(),
  results = [];
try {
  const context = await newContext(browser),
    page = await context.newPage();
  await page.route('**/api/web/dining/public/**', (route) => {
    const endpoint = new URL(route.request().url()).pathname;
    return route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify(
        endpoint.endsWith('/menu')
          ? menu
          : endpoint.endsWith('/invoice')
            ? invoice
            : { status: 'ended', orders: [] },
      ),
    });
  });
  for (const locale of ['fr', 'en', 'ar']) {
    await page.goto(origin + '/menu?locale=' + locale + '#' + reference);
    await page.getByTestId('own-invoice').locator('table tbody tr').waitFor();
    for (const theme of ['light', 'dark']) {
      await page.evaluate((theme) => window.moulaiTheme.choose(theme), theme);
      await page.setViewportSize({ width: 390, height: 844 });
      assert.equal(
        await page.evaluate(
          () => document.documentElement.scrollWidth > innerWidth + 1,
        ),
        false,
      );
      await page.screenshot({
        path: path.join(output, `screen-${locale}-${theme}-mobile.png`),
        fullPage: true,
      });
    }
    await page.emulateMedia({ media: 'print' });
    await page
      .locator('[data-print-invoice] img')
      .evaluate((image) => image.decode());
    await page.screenshot({
      path: path.join(output, `print-${locale}-mobile.png`),
      fullPage: true,
    });
    await page.setViewportSize({ width: 794, height: 1123 });
    await page.screenshot({
      path: path.join(output, `print-${locale}-a4-proportion.png`),
      fullPage: true,
    });
    results.push({
      locale,
      source: 'EXPLICIT VISUAL FIXTURE, NO REAL API OR AUTHORIZATION PROOF',
      horizontalPageOverflow: false,
    });
    await page.emulateMedia({ media: 'screen' });
  }
  fs.writeFileSync(
    path.join(output, 'results.json'),
    JSON.stringify(
      { status: 'PASS', syntheticOnly: true, backendExercised: false, results },
      null,
      2,
    ),
  );
  console.log(
    JSON.stringify({
      status: 'PASS',
      source: 'explicit visual fixture',
      cases: results.length,
    }),
  );
} finally {
  await browser.close();
}

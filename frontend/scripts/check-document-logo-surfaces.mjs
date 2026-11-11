// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// SaaS: real read-only local session. Food: explicitly labelled historical visual replay; no new visit, invoice or funds action.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { expect } from '@playwright/test';
import {
  launch,
  login,
  newContext,
  root,
  origin,
  request,
  checked,
} from './operationalHarness.mjs';

const output = path.join(
  root,
  'artifacts/document-logo-surfaces-20261111/final',
);
fs.mkdirSync(output, { recursive: true });
const prior = JSON.parse(
  fs.readFileSync(
    path.join(root, 'artifacts/saas-documents-20261111/browser/journey.json'),
    'utf8',
  ),
);
const historical = JSON.parse(
  fs.readFileSync(
    path.join(
      root,
      'artifacts/interface-documents-20261110/restaurant/print-snapshot-fr.json',
    ),
    'utf8',
  ),
).invoice;
const browser = await launch(),
  captures = [],
  exports = [];
const expected = {
  light: '/brand/moulai-logo-light01.png',
  dark: '/brand/moulai-logo-dark-approved-20261111.png',
};
try {
  const owner = await login(browser, 'billing-scenario');
  const endpoint = `/api/web/organizations/${prior.organization}/restaurants/${prior.restaurant}/saas-payments/${prior.paymentId}/documents`;
  const retained = checked(await request(owner, endpoint));
  assert.equal(retained[0].state, 'invalidated');
  const guest = await (await newContext(browser)).newPage();
  const reference = 'V'.repeat(43),
    labels = {
      fr: 'RELECTURE VISUELLE HISTORIQUE',
      en: 'HISTORICAL VISUAL REPLAY',
      ar: 'إعادة عرض بصري لبيانات اختبار سابقة',
    };
  const menu = {
    reference,
    restaurant: 'HISTORICAL VISUAL REPLAY — NO LIVE INVOICE CHECK',
    branch: 'VISUAL FIXTURE',
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
  await guest.route('**/api/web/dining/public/**', (route) =>
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify(
        new URL(route.request().url()).pathname.endsWith('/menu')
          ? menu
          : new URL(route.request().url()).pathname.endsWith('/invoice')
            ? historical
            : { status: 'ended', orders: [] },
      ),
    }),
  );
  await guest.goto(origin + '/access');
  for (const [kind, page] of [
    ['saas', owner],
    ['food', guest],
  ]) {
    for (const locale of ['fr', 'en', 'ar']) {
      await page.evaluate(
        (locale) => localStorage.setItem('moulai.locale', locale),
        locale,
      );
      await page.goto(
        origin +
          (kind === 'saas'
            ? `/workspace/saas-documents/${prior.organization}/${prior.restaurant}/${prior.paymentId}`
            : '/menu?locale=' + locale + '#' + reference),
      );
      const sheet = page.locator(
        kind === 'saas' ? 'main [data-saas-printable]' : '[data-print-invoice]',
      );
      await sheet.waitFor();
      const logo = sheet.locator('[data-approved-brand-logo] img');
      const navigationEntry = await page.evaluate(
        () => performance.getEntriesByType('navigation').length,
      );
      for (const theme of ['light', 'dark', 'light', 'dark']) {
        await page.evaluate((theme) => window.moulaiTheme.choose(theme), theme);
        await logo.evaluate(async (image) => {
          await image.decode();
        });
        assert.equal(
          await logo.evaluate((image) => new URL(image.currentSrc).pathname),
          expected[theme],
        );
        assert.equal(
          await page.evaluate(
            () => performance.getEntriesByType('navigation').length,
          ),
          navigationEntry,
        );
      }
      for (const theme of ['light', 'dark']) {
        await page.evaluate((theme) => window.moulaiTheme.choose(theme), theme);
        await logo.evaluate(async (image) => {
          await image.decode();
        });
        for (const [device, size] of Object.entries({
          desktop: { width: 1440, height: 1000 },
          mobile: { width: 390, height: 844 },
        })) {
          await page.setViewportSize(size);
          await page.evaluate(() => document.fonts.ready);
          assert.equal(
            await page.evaluate(
              () => document.documentElement.scrollWidth > innerWidth + 1,
            ),
            false,
          );
          const file = `${kind}-${locale}-${theme}-${device}.png`;
          await page.screenshot({
            path: path.join(output, file),
            fullPage: true,
          });
          const qr = sheet.locator('img').last();
          const qrBackground = await qr.evaluate((image) => {
            const parent = getComputedStyle(
                image.parentElement,
              ).backgroundColor,
              own = getComputedStyle(image).backgroundColor;
            return (
              own === 'rgb(255, 255, 255)' || parent === 'rgb(255, 255, 255)'
            );
          });
          assert.equal(qrBackground, true);
          captures.push({
            file,
            kind,
            locale,
            theme,
            device,
            logo: expected[theme],
            qrWhite: true,
            source:
              kind === 'saas'
                ? 'actual authorized local read'
                : 'explicit historical visual replay',
          });
        }
        const directory = path.join(output, kind + '-' + theme);
        fs.mkdirSync(directory, { recursive: true });
        await page.setViewportSize({ width: 1440, height: 1000 });
        await page.emulateMedia({ media: 'print' });
        const printRoot = page.locator(
          kind === 'saas' ? '[data-saas-print-root]' : '[data-print-invoice]',
        );
        await expect(
          printRoot.locator('[data-approved-brand-logo] img'),
        ).toHaveJSProperty('currentSrc', origin + expected.light);
        await printRoot
          .locator('img')
          .evaluateAll((images) =>
            Promise.all(images.map((image) => image.decode())),
          );
        assert.equal(
          await printRoot
            .locator('[data-approved-brand-logo] img')
            .evaluate((image) => new URL(image.currentSrc).pathname),
          expected.light,
        );
        await page.evaluate(async () => {
          await document.fonts.ready;
          scrollTo(0, 0);
          await new Promise((resolve) =>
            requestAnimationFrame(() => requestAnimationFrame(resolve)),
          );
        });
        const white = await printRoot.evaluate(
          (element) => getComputedStyle(element).backgroundColor,
        );
        assert.equal(white, 'rgb(255, 255, 255)');
        assert.equal(
          await page.evaluate(
            () => getComputedStyle(document.documentElement).colorScheme,
          ),
          'light',
        );
        await page.pdf({
          path: path.join(directory, `invoice-${locale}.pdf`),
          format: 'A4',
          preferCSSPageSize: true,
          printBackground: true,
          tagged: true,
        });
        exports.push({
          kind,
          locale,
          startedFromTheme: theme,
          file: `${kind}-${theme}/invoice-${locale}.pdf`,
          printLogo: expected.light,
          background: white,
          printColorScheme: 'light',
        });
        await page.emulateMedia({ media: 'screen' });
        assert.equal(
          await page.evaluate(
            () => getComputedStyle(document.documentElement).colorScheme,
          ),
          theme,
        );
        await logo.evaluate(async (image) => {
          await image.decode();
        });
        assert.equal(
          await logo.evaluate((image) => new URL(image.currentSrc).pathname),
          expected[theme],
        );
      }
    }
  }
  assert.deepEqual(checked(await request(owner, endpoint)), retained);
  fs.writeFileSync(
    path.join(output, 'browser-summary.json'),
    JSON.stringify(
      {
        status: 'PASS',
        captures,
        exports,
        retainedDocumentUnchanged: true,
        businessWrites: 0,
        themeSwitchWithoutReload: true,
        physicalPrinter: 'NOT TESTED',
        foodSource:
          'historical visual replay, not a new authorization or current validity proof',
      },
      null,
      2,
    ),
  );
  console.log(
    JSON.stringify({
      status: 'PASS',
      captures: captures.length,
      PDFs: exports.length,
      businessWrites: 0,
    }),
  );
} finally {
  await browser.close();
}

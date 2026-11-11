// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Read-only follow-up after the real journey: regenerate visual/PDF evidence without repeating emission or invalidation.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import AxeBuilder from '@axe-core/playwright';
import {
  launch,
  login,
  root,
  origin,
  request,
  checked,
} from './operationalHarness.mjs';
const prior = JSON.parse(
  fs.readFileSync(
    path.join(root, 'artifacts/saas-documents-20261111/browser/journey.json'),
    'utf8',
  ),
);
assert.equal(prior.status, 'PASS');
const output = path.join(root, 'artifacts/saas-documents-20261111/final');
fs.mkdirSync(output, { recursive: true });
const browser = await launch(),
  captures = [];
try {
  const page = await login(browser, 'billing-scenario');
  const api = `/api/web/organizations/${prior.organization}/restaurants/${prior.restaurant}/saas-payments/${prior.paymentId}/documents`;
  const before = checked(await request(page, api));
  assert.equal(before[0].id, prior.documentId);
  assert.equal(before[0].state, 'invalidated');
  for (const locale of ['fr', 'en', 'ar']) {
    await page.evaluate(
      (locale) => localStorage.setItem('moulai.locale', locale),
      locale,
    );
    await page.goto(
      origin +
        `/workspace/saas-documents/${prior.organization}/${prior.restaurant}/${prior.paymentId}`,
    );
    await page.locator('main [data-saas-printable]').waitFor();
    await page
      .locator('main [data-saas-printable] img')
      .evaluateAll((images) =>
        Promise.all(images.map((image) => image.decode())),
      );
    await page.evaluate(() => document.fonts.ready);
    await page.locator('main a').first().focus();
    await page.keyboard.press('Tab');
    assert.equal(
      await page
        .locator('main button')
        .first()
        .evaluate(
          (button) =>
            button === document.activeElement &&
            button.matches(':focus-visible'),
        ),
      true,
    );
    for (const theme of ['light', 'dark'])
      for (const [device, viewport] of Object.entries({
        desktop: { width: 1440, height: 900 },
        mobile: { width: 390, height: 844 },
      })) {
        await page.setViewportSize(viewport);
        await page.evaluate((theme) => window.moulaiTheme.choose(theme), theme);
        assert.equal(
          await page.evaluate(
            () => document.documentElement.scrollWidth > innerWidth,
          ),
          false,
        );
        const file = `owner-${locale}-${theme}-${device}.png`;
        await page.screenshot({
          path: path.join(output, file),
          fullPage: true,
        });
        const axe = await new AxeBuilder({ page }).analyze();
        assert.deepEqual(
          axe.violations.map((value) => value.id),
          [],
        );
        captures.push({
          file,
          locale,
          theme,
          device,
          axeViolations: 0,
          incomplete: axe.incomplete.map((value) => value.id),
        });
      }
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.emulateMedia({ media: 'print' });
    await page
      .locator('[data-saas-print-root] img')
      .evaluateAll((images) =>
        Promise.all(images.map((image) => image.decode())),
      );
    await page.evaluate(async () => {
      await document.fonts.ready;
      window.scrollTo(0, 0);
      await new Promise((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(resolve)),
      );
    });
    const print = await page.evaluate(() => ({
      appHidden:
        getComputedStyle(document.getElementById('root')).display === 'none',
      printVisible:
        getComputedStyle(document.querySelector('[data-saas-print-root]'))
          .display === 'block',
      background: getComputedStyle(document.body).backgroundImage,
      headers: document
        .querySelector('[data-saas-print-root]')
        .querySelectorAll('header,nav,aside').length,
    }));
    assert.equal(print.appHidden, true);
    assert.equal(print.printVisible, true);
    assert.equal(print.background, 'none');
    assert.equal(print.headers, 0);
    await page.screenshot({
      path: path.join(output, `print-dom-${locale}.png`),
      fullPage: true,
    });
    await page.pdf({
      path: path.join(output, `invoice-${locale}.pdf`),
      format: 'A4',
      preferCSSPageSize: true,
      printBackground: true,
      tagged: true,
    });
    await page.emulateMedia({ media: 'screen' });
  }
  const after = checked(await request(page, api));
  assert.deepEqual(after, before);
  fs.writeFileSync(
    path.join(output, 'summary.json'),
    JSON.stringify(
      {
        status: 'PASS',
        captures,
        applicationHiddenForPrint: true,
        sourceDocumentUnchanged: true,
        keyboardReachedPrintButton: true,
        documentState: 'invalidated',
        readOnlyBusinessOperations: true,
        independentQrDecoding: 'NOT PERFORMED',
        physicalPhoneScan: 'NOT TESTED',
        physicalPrinter: 'NOT TESTED',
      },
      null,
      2,
    ),
  );
  console.log(
    JSON.stringify({
      status: 'PASS',
      captures: captures.length,
      PDFs: 3,
      businessWrites: 0,
    }),
  );
} finally {
  await browser.close();
}

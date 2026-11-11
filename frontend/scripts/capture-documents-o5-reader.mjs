// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Read-only anonymous local verification; authenticated details are used only to obtain the already issued synthetic reference.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import AxeBuilder from '@axe-core/playwright';
import {
  launch,
  login,
  newContext,
  origin,
  root,
  checked,
  request,
} from './operationalHarness.mjs';
const output = path.join(root, 'artifacts/documents-o5-polish-20261111/reader');
fs.mkdirSync(output, { recursive: true });
const journey = JSON.parse(
  fs.readFileSync(
    path.join(root, 'artifacts/saas-documents-20261111/browser/journey.json'),
    'utf8',
  ),
);
assert.equal(journey.status, 'PASS');
const browser = await launch(),
  captures = [];
try {
  const owner = await login(browser, 'billing-scenario');
  const documents = checked(
    await request(
      owner,
      `/api/web/organizations/${journey.organization}/restaurants/${journey.restaurant}/saas-payments/${journey.paymentId}/documents`,
    ),
  );
  assert.equal(documents[0].state, 'invalidated');
  await owner.context().close();
  const context = await newContext(browser),
    page = await context.newPage();
  for (const locale of ['fr', 'en', 'ar']) {
    await page.goto(
      origin +
        `/verify-saas-document?locale=${locale}#${documents[0].reference}`,
    );
    await page.locator('main h2').waitFor();
    assert.equal(await page.locator('html').getAttribute('lang'), locale);
    const result = checked(
      await request(page, '/api/web/saas-documents/verify', {
        reference: documents[0].reference,
      }),
    );
    assert.deepEqual(Object.keys(result).sort(), [
      'issued_at',
      'issuer',
      'reference',
      'state',
    ]);
    assert.equal(result.state, 'invalidated');
    assert.equal(checked(await request(page, '/api/web/session')), null);
    for (const theme of ['light', 'dark'])
      for (const [device, viewport] of Object.entries({
        desktop: { width: 1440, height: 900 },
        mobile: { width: 390, height: 844 },
      })) {
        await page.setViewportSize(viewport);
        await page.evaluate((theme) => window.moulaiTheme.choose(theme), theme);
        await page.evaluate(() => document.fonts.ready);
        assert.equal(
          await page.evaluate(
            () => document.documentElement.scrollWidth > innerWidth,
          ),
          false,
        );
        assert.equal(
          await page.locator('html').getAttribute('dir'),
          locale === 'ar' ? 'rtl' : 'ltr',
        );
        const file = `verify-${locale}-${theme}-${device}.png`;
        await page.screenshot({
          path: path.join(output, file),
          fullPage: true,
        });
        const axe = await new AxeBuilder({ page }).analyze();
        assert.deepEqual(
          axe.violations.map((item) => item.id),
          [],
        );
        captures.push({
          file,
          locale,
          theme,
          device,
          axeViolations: 0,
          incomplete: axe.incomplete.map((item) => item.id),
        });
      }
  }
  fs.writeFileSync(
    path.join(output, 'summary.json'),
    JSON.stringify(
      {
        status: 'PASS',
        captures,
        authenticatedReader: false,
        publicFieldsOnly: true,
        state: 'invalidated',
        businessWrites: 0,
        physicalPhoneScan: 'NOT TESTED',
      },
      null,
      2,
    ),
  );
  console.log(
    JSON.stringify({
      status: 'PASS',
      captures: captures.length,
      businessWrites: 0,
    }),
  );
} finally {
  await browser.close();
}

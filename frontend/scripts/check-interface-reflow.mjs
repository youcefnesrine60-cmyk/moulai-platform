// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Geometry at 640 CSS px with 2x pixel density, not a physical-device or assistive-reader certification.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { launch, newContext, origin, root } from './operationalHarness.mjs';
import { redactLocalMessage } from '../src/shared/access/logSafety.ts';

const output = path.join(
  root,
  'artifacts/interface-consolidation-20261110/reflow',
);
fs.mkdirSync(output, { recursive: true });
const browser = await launch(),
  results = [];
try {
  const context = await newContext(browser, { width: 640, height: 480 }, 2),
    page = await context.newPage();
  for (const locale of ['fr', 'en', 'ar']) {
    await page.goto(origin + '/access');
    await page.evaluate(
      (locale) => localStorage.setItem('moulai.locale', locale),
      locale,
    );
    await page.reload();
    for (const theme of ['light', 'dark']) {
      await page.evaluate((theme) => window.moulaiTheme.choose(theme), theme);
      await page.evaluate(() => document.fonts.ready);
      const facts = await page.evaluate(() => ({
        width: innerWidth,
        pixelDensity: devicePixelRatio,
        overflow: document.documentElement.scrollWidth > innerWidth + 1,
        loginVisible: Boolean(document.querySelector('main button')),
        direction: document.documentElement.dir,
      }));
      assert.equal(facts.width, 640);
      assert.equal(facts.pixelDensity, 2);
      assert.equal(facts.overflow, false);
      await page.screenshot({
        path: path.join(output, `${locale}-${theme}-2x.png`),
        fullPage: true,
      });
      results.push({ locale, theme, facts });
    }
  }
  fs.writeFileSync(
    path.join(output, 'results.json'),
    JSON.stringify(
      {
        status: 'PASS',
        scope:
          '640 CSS px at density 2, six visual states; true browser UI zoom and phone remain untested',
        results,
      },
      null,
      2,
    ),
  );
  console.log(JSON.stringify({ status: 'PASS', cases: results.length }));
} catch (error) {
  fs.writeFileSync(
    path.join(output, 'failure.json'),
    JSON.stringify(
      { status: 'FAIL', message: redactLocalMessage(error.message) },
      null,
      2,
    ),
  );
  process.exitCode = 1;
} finally {
  await browser.close();
}

// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Read-only local browser checks; no provider, voice recording or business mutation.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import AxeBuilder from '@axe-core/playwright';
import {
  launch,
  newContext,
  login,
  origin,
  root,
} from './operationalHarness.mjs';
import { redactLocalMessage } from '../src/shared/access/logSafety.ts';

const output = path.join(
  root,
  'artifacts/interface-consolidation-20261110/quality',
);
fs.mkdirSync(output, { recursive: true });
const results = [];
const browser = await launch();
let phase = 'accessibility';
try {
  const anonymous = await newContext(browser),
    access = await anonymous.newPage();
  const owner = await login(browser, 'owner-a');
  for (const [name, page, route] of [
    ['access', access, '/access'],
    ['offer', owner, '/workspace/organizations/8/restaurants/6/offer'],
    [
      'tables',
      owner,
      '/workspace/organizations/8/restaurants/6/tables?branch=4',
    ],
  ]) {
    for (const locale of ['fr', 'en', 'ar']) {
      if (name !== 'access') {
        await page.goto(origin + '/api/web/auth/login');
        await page.waitForURL('**/workspace');
      }
      await page.goto(origin + '/access');
      await page.evaluate(
        (locale) => localStorage.setItem('moulai.locale', locale),
        locale,
      );
      await page.goto(origin + route);
      if (name === 'offer')
        await page.locator('select[required]').first().waitFor();
      if (name === 'tables')
        await page.getByTestId('operational-board').waitFor();
      for (const theme of ['light', 'dark']) {
        phase = `${name}-${locale}-${theme}`;
        await page.setViewportSize(
          locale === 'ar'
            ? { width: 390, height: 844 }
            : { width: 1440, height: 1000 },
        );
        await page.evaluate((theme) => window.moulaiTheme.choose(theme), theme);
        await page.evaluate(() => document.fonts.ready);
        const axe = await new AxeBuilder({ page })
          .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
          .analyze();
        const facts = await page.evaluate(() => ({
          direction: document.documentElement.dir,
          font: getComputedStyle(document.body).fontFamily,
          sora: document.fonts.check('16px "Sora Variable"', 'MoulAI'),
          tajawal: document.fonts.check('16px Tajawal', 'مرحبا'),
          overflow: document.documentElement.scrollWidth > innerWidth + 1,
          visibleKeys:
            document.body.innerText.match(
              /\b(?:quality|o3|d1|access|offer)\.[a-z_]+\b/g,
            ) ?? [],
          timing: performance.getEntriesByType('navigation').map((entry) => ({
            responseEnd: entry.responseEnd,
            domContentLoaded: entry.domContentLoadedEventEnd,
          })),
          paint: performance.getEntriesByType('paint').map((entry) => ({
            name: entry.name,
            milliseconds: entry.startTime,
          })),
          transferredBytes: performance
            .getEntriesByType('resource')
            .reduce((total, entry) => total + entry.transferSize, 0),
        }));
        results.push({
          phase,
          facts,
          violations: axe.violations.map((item) => ({
            id: item.id,
            impact: item.impact,
            help: item.help,
            nodes: item.nodes.map((node) => ({
              target: node.target,
              failure: node.failureSummary,
            })),
          })),
        });
        assert.equal(facts.overflow, false);
        assert.equal(facts.visibleKeys.length, 0);
        assert(
          locale === 'ar' ? facts.tajawal : facts.sora,
          'The font used by this language must be loaded; unused subsets are lazy-loaded.',
        );
        // Preserve all diagnostics before asserting; no automatic exemption of contrast findings.
        fs.writeFileSync(
          path.join(output, 'results.json'),
          JSON.stringify({ status: 'RUNNING', results }, null, 2),
        );
        assert.equal(
          axe.violations.length,
          0,
          phase + ': accessibility findings require review',
        );
      }
    }
  }
  phase = 'access-disclosure-keyboard-and-reflow';
  await access.goto(origin + '/access');
  await access.setViewportSize({ width: 320, height: 720 });
  await access.evaluate(() => document.fonts.ready);
  const summary = access.locator('main details > summary').first();
  await summary.focus();
  await access.keyboard.press('Enter');
  assert(await summary.locator('..').evaluate((details) => details.open));
  assert.equal(
    await access.evaluate(
      () => document.documentElement.scrollWidth > innerWidth + 1,
    ),
    false,
  );
  await access.screenshot({
    path: path.join(output, 'access-reflow-320.png'),
    fullPage: true,
  });
  // Local draft text must survive opening/closing help, without any submit.
  await owner.goto(origin + '/workspace/enrollment');
  const input = owner.locator('input[name="company_name"]');
  await input.fill('LOCAL-FAKE — Unsent visual draft');
  await owner.locator('[data-assistance-dock] button').first().click();
  await owner.keyboard.press('Escape');
  assert.equal(await input.inputValue(), 'LOCAL-FAKE — Unsent visual draft');
  await owner.locator('header a[href="/workspace"]').first().click();
  await owner.getByRole('dialog').waitFor();
  await owner.screenshot({ path: path.join(output, 'unsaved-dialog.png') });
  await owner.keyboard.press('Escape');
  assert.equal(await input.inputValue(), 'LOCAL-FAKE — Unsent visual draft');
  await input.fill('');
  // Explicitly discard the edit flag before closing; no business write is performed.
  await owner.locator('header a[href="/workspace"]').first().click();
  await owner.getByRole('dialog').getByRole('button').last().click();
  fs.writeFileSync(
    path.join(output, 'results.json'),
    JSON.stringify(
      {
        status: 'PASS',
        results,
        keyboardDisclosure: true,
        helpKeepsInput: true,
        discardExplicit: true,
        automaticSubmit: false,
        measurement:
          'local Vite, warm process; no remote or phone performance claim',
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
      { status: 'FAIL', phase, message: redactLocalMessage(error.message) },
      null,
      2,
    ),
  );
  console.log(
    JSON.stringify({
      status: 'FAIL',
      phase,
      message: redactLocalMessage(error.message),
    }),
  );
  process.exitCode = 1;
} finally {
  await browser.close();
}

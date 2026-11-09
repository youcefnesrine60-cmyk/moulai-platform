// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Comparable read-only views of the same persisted local data; no synthetic API responses.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { launch, login, origin, output } from './operationalHarness.mjs';
const browser = await launch(),
  captures = [];
let phase = 'login';
try {
  for (const [name, username, url, ready] of [
    [
      'owner-offer',
      'owner-a',
      '/workspace/organizations/8/restaurants/6/offer',
      'select[required]',
    ],
    [
      'pricing',
      'platform-admin',
      '/platform/pricing',
      'input[name="reminderDays"]',
    ],
  ]) {
    const page = await login(browser, username);
    for (const locale of ['fr', 'en', 'ar']) {
      await page.evaluate(
        (locale) => localStorage.setItem('moulai.locale', locale),
        locale,
      );
      await page.goto(origin + url);
      await page.waitForFunction(
        (locale) => document.documentElement.lang === locale,
        locale,
      );
      await page.locator(ready).waitFor();
      assert.equal(
        await page.evaluate(() => document.documentElement.dir),
        locale === 'ar' ? 'rtl' : 'ltr',
      );
      await page.evaluate(() => document.fonts.ready);
      for (const theme of ['light', 'dark'])
        for (const [viewport, dimensions] of Object.entries({
          desktop: { width: 1440, height: 1000 },
          mobile: { width: 390, height: 844 },
        })) {
          phase = [name, locale, theme, viewport].join('-');
          await page.setViewportSize(dimensions);
          await page.evaluate(
            (theme) => window.moulaiTheme.choose(theme),
            theme,
          );
          await page.evaluate(
            () =>
              new Promise((resolve) =>
                requestAnimationFrame(() => requestAnimationFrame(resolve)),
              ),
          );
          assert.equal(
            await page.evaluate(
              () => document.documentElement.scrollWidth > innerWidth + 1,
            ),
            false,
          );
          const keys =
            (await page.locator('body').innerText()).match(
              /\b(?:integration|pricing|reminders|offer|ops|d1)\.[a-zA-Z_]+/g,
            ) ?? [];
          assert.deepEqual(keys, []);
          const file = phase + '.png';
          await page.screenshot({
            path: path.join(output, file),
            fullPage: true,
            animations: 'disabled',
          });
          captures.push({
            file,
            locale,
            theme,
            viewport,
            overflow: false,
            rawKeys: [],
          });
        }
    }
    await page.context().close();
  }
  fs.writeFileSync(
    path.join(output, 'interface-captures.json'),
    JSON.stringify({ status: 'PASS', captures }, null, 2),
  );
  console.log(JSON.stringify({ status: 'PASS', captures: captures.length }));
} catch (error) {
  fs.writeFileSync(
    path.join(output, 'interface-captures-failure-' + Date.now() + '.json'),
    JSON.stringify(
      { status: 'FAIL', phase, type: error.name, captures },
      null,
      2,
    ),
  );
  console.log(JSON.stringify({ status: 'FAIL', phase, type: error.name }));
  process.exitCode = 1;
} finally {
  await browser.close();
}

// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// MoulAI™ — comparable views of actual local data, with no API stubs or secret screenshots.
import { chromium } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
const root = path.resolve(import.meta.dirname, '../..'),
  id = '3fb5f85a6cc94868acaf7d95b3777a16';
const directory = path.join(root, 'artifacts/operational-local', id),
  output = path.join(root, 'artifacts/operational-integration-20261107');
assert.equal(
  fs.readFileSync(path.join(directory, 'instance-marker'), 'ascii'),
  id,
);
const accounts = JSON.parse(
  fs.readFileSync(
    path.join(directory, 'private/acceptance-accounts.json'),
    'utf8',
  ),
);
const tablesOnly = process.argv.includes('--tables-only');
const pricingOnly = process.argv.includes('--pricing-only');
assert(!(tablesOnly && pricingOnly), 'Choose one partial capture scope');
const captures =
  tablesOnly || pricingOnly
    ? JSON.parse(
        fs.readFileSync(path.join(output, 'captures.json'), 'utf8'),
      ).captures.filter(
        (capture) =>
          !capture.file.startsWith(tablesOnly ? 'tables-' : 'pricing-'),
      )
    : [];
let phase = 'start';
const browser = await chromium.launch({ headless: true });
async function context() {
  const c = await browser.newContext({
    ignoreHTTPSErrors: true,
    locale: 'fr-FR',
  });
  await c.route('**/*', (r) =>
    ['https://127.0.0.1:5180', 'https://127.0.0.1:8444'].includes(
      new URL(r.request().url()).origin,
    )
      ? r.continue()
      : r.abort(),
  );
  return c;
}
async function login(c, username) {
  const page = await c.newPage();
  await page.goto('https://127.0.0.1:5180/access');
  await page
    .getByRole('button', { name: 'Continuer avec Keycloak', exact: true })
    .click();
  await page.locator('#username').fill(username);
  await page.locator('#password').fill(accounts[username].password);
  await page.locator('#kc-login').click();
  await page.waitForURL(/https:\/\/127\.0\.0\.1:5180\/(workspace|platform)/);
  return page;
}
async function capture(page, name, url) {
  for (const locale of ['fr', 'en', 'ar']) {
    await page.evaluate(
      (locale) => localStorage.setItem('moulai.locale', locale),
      locale,
    );
    await page.goto('https://127.0.0.1:5180' + url);
    await page.waitForFunction(
      (locale) => document.documentElement.lang === locale,
      locale,
    );
    if (name === 'workspace')
      await page
        .locator('a[href="/workspace/organizations/8/restaurants"]')
        .waitFor();
    if (name === 'access')
      await page
        .locator('button[aria-describedby="connection-status"]')
        .waitFor();
    if (name === 'tables')
      await page
        .locator('#dining-workspace')
        .getByRole('button')
        .filter({ hasText: /Configuration|الإعداد|Settings/ })
        .first()
        .waitFor();
    if (name === 'pricing')
      await page.locator('input[name="baseAmount"]').waitFor();
    await page.evaluate(() => document.fonts.ready);
    for (const theme of ['light', 'dark']) {
      await page.evaluate((theme) => window.moulaiTheme.choose(theme), theme);
      for (const [viewport, size] of Object.entries({
        desktop: { width: 1440, height: 1000 },
        mobile: { width: 390, height: 844 },
      })) {
        phase = [name, locale, theme, viewport].join('-');
        await page.setViewportSize(size);
        await page.evaluate(
          () =>
            new Promise((resolve) =>
              requestAnimationFrame(() => requestAnimationFrame(resolve)),
            ),
        );
        const overflow = await page.evaluate(
          () => document.documentElement.scrollWidth > window.innerWidth + 1,
        );
        const rawKeys = await page
          .locator('body')
          .innerText()
          .then(
            (text) =>
              text.match(/\b(?:integration|pricing|d1|ops)\.[a-zA-Z_]+/g) ?? [],
          );
        assert.equal(overflow, false, phase + ' horizontal overflow');
        assert.equal(rawKeys.length, 0, phase + ' untranslated keys');
        if (name === 'tables') {
          const bar = page.getByTestId('effective-permissions');
          await bar.scrollIntoViewIfNeeded();
          assert((await bar.innerText()).trim().length > 0);
          await page.evaluate(() => window.scrollTo(0, 0));
          await page.evaluate(
            () =>
              new Promise((resolve) =>
                requestAnimationFrame(() => requestAnimationFrame(resolve)),
              ),
          );
        }
        const filename = phase + '.png';
        await page.screenshot({
          path: path.join(output, filename),
          fullPage: true,
          animations: 'disabled',
        });
        captures.push({
          file: filename,
          locale,
          theme,
          viewport,
          overflow,
          rawKeys,
        });
      }
    }
  }
}
try {
  if (!tablesOnly && !pricingOnly) {
    const anonymous = await context();
    const access = await anonymous.newPage();
    await access.goto('https://127.0.0.1:5180/access');
    await capture(access, 'access', '/access');
    await anonymous.close();
  }
  if (!pricingOnly) {
    const owner = await context();
    const workspace = await login(owner, 'owner-a');
    if (!tablesOnly) await capture(workspace, 'workspace', '/workspace');
    await capture(
      workspace,
      'tables',
      '/workspace/organizations/8/restaurants/6/tables?branch=4',
    );
    await owner.close();
  }
  if (!tablesOnly) {
    const admin = await context();
    const pricing = await login(admin, 'platform-admin');
    await capture(pricing, 'pricing', '/platform/pricing');
    await admin.close();
  }
  fs.writeFileSync(
    path.join(output, 'captures.json'),
    JSON.stringify({ status: 'PASS', captures }, null, 2),
  );
  console.log(JSON.stringify({ status: 'PASS', captures: captures.length }));
} catch (error) {
  fs.writeFileSync(
    path.join(output, 'captures.json'),
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

// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { redactEvidenceJson } from '../src/shared/access/logSafety.ts';
// MoulAI™ — real browser acceptance on the owned loopback instance only.
// No trace, storage-state export or password-bearing failure log is retained.
import { chromium } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';

const root = path.resolve(import.meta.dirname, '../..');
const id = '3fb5f85a6cc94868acaf7d95b3777a16';
const instance = path.join(root, 'artifacts/operational-local', id);
assert.equal(
  fs.readFileSync(path.join(instance, 'instance-marker'), 'ascii'),
  id,
);
const accounts = JSON.parse(
  fs.readFileSync(
    path.join(instance, 'private/acceptance-accounts.json'),
    'utf8',
  ),
);
const output = path.join(root, 'artifacts/operational-integration-20261107');
const results = [];
let phase = 'browser-start';
let currentPage;
const traffic = [];
const uiErrors = [];
const browser = await chromium.launch({ headless: true });
try {
  for (const username of [
    'owner-a',
    'owner-b',
    'unlinked',
    'platform-admin',
    'platform-reader',
  ]) {
    phase = username + ':context';
    const context = await browser.newContext({
      ignoreHTTPSErrors: true,
      locale: 'fr-FR',
    });
    const blocked = [];
    await context.route('**/*', async (route) => {
      const url = new URL(route.request().url());
      if (
        ['https://127.0.0.1:5180', 'https://127.0.0.1:8444'].includes(
          url.origin,
        )
      )
        await route.continue();
      else {
        blocked.push(url.origin);
        await route.abort();
      }
    });
    const page = await context.newPage();
    currentPage = page;
    page.on('response', (response) => {
      const url = new URL(response.url());
      if (
        url.pathname.startsWith('/api/web') ||
        url.pathname.includes('login-actions')
      )
        traffic.push({ path: url.pathname, status: response.status() });
    });
    page.on('pageerror', (error) => uiErrors.push(error.message));
    page.on('console', (message) => {
      if (
        message.type() === 'error' &&
        !message.text().includes('Failed to load resource')
      )
        uiErrors.push(message.text().slice(0, 2000));
    });
    phase = username + ':access';
    await page.goto('https://127.0.0.1:5180/access');
    await page
      .getByRole('button', { name: 'Continuer avec Keycloak', exact: true })
      .click();
    phase = username + ':login';
    await page.locator('#username').fill(username);
    await page.locator('#password').fill(accounts[username].password);
    await page.locator('#kc-login').click();
    await page.waitForURL(/https:\/\/127\.0\.0\.1:5180\/(workspace|platform)/, {
      timeout: 12000,
    });
    phase = username + ':session';
    const projections = await page.evaluate(async () => {
      const session = await fetch('/api/web/session').then((r) => r.json());
      const companies = await fetch('/api/web/organizations').then(
        async (r) => ({ status: r.status, body: await r.json() }),
      );
      const foreign = await fetch('/api/web/organizations/9/restaurants').then(
        (r) => r.status,
      );
      const platform = await fetch('/api/web/platform/access').then(
        (r) => r.status,
      );
      return { session, companies, foreign, platform };
    });
    assert.equal(projections.session.source, 'authenticated-local');
    assert.equal(projections.session.subject, accounts[username].subject);
    if (username === 'owner-a') {
      assert.deepEqual(
        projections.companies.body.map((c) => c.id),
        [8],
      );
      assert.equal(projections.foreign, 403);
      assert.equal(projections.platform, 403);
      phase = username + ':dining';
      await page.goto(
        'https://127.0.0.1:5180/workspace/organizations/8/restaurants/6/tables',
      );
      await page
        .getByRole('heading', { name: /Tables et réservations/ })
        .first()
        .waitFor();
      await page.locator('select[name="branch"]').selectOption('4');
      await page
        .getByText('Habilitations contrôlées en base', { exact: false })
        .first()
        .waitFor();
      await page.screenshot({
        path: path.join(output, 'lot1-owner-fr-desktop.png'),
        fullPage: true,
      });
      await page.reload();
      await page
        .getByRole('heading', { name: /Tables et réservations/ })
        .first()
        .waitFor();
      const dining = await page.evaluate(() =>
        fetch('/api/web/dining-session').then((r) => r.json()),
      );
      assert.equal(dining.identity_provider, 'keycloak-local');
      projections.dining = dining;
    }
    if (username === 'owner-b')
      assert.deepEqual(
        projections.companies.body.map((c) => c.id),
        [9],
      );
    if (username === 'unlinked')
      assert.deepEqual(projections.companies.body, []);
    if (username === 'platform-admin')
      assert(
        projections.session.platformPermissions.includes(
          'subscriptions.pricing.manage',
        ),
      );
    if (username === 'platform-reader')
      assert(
        !projections.session.platformPermissions.includes(
          'subscriptions.pricing.manage',
        ),
      );
    const cookies = (await context.cookies()).filter((c) =>
      c.name.startsWith('__Secure-moulai'),
    );
    assert.equal(cookies.length, 1);
    phase = username + ':logout';
    const logout = await page.evaluate(async () => {
      const r = await fetch('/api/web/auth/logout', { method: 'POST' });
      return {
        status: r.status,
        protectedStatus: await fetch('/api/web/organizations').then(
          (r) => r.status,
        ),
      };
    });
    assert.equal(logout.status, 204);
    assert.equal(logout.protectedStatus, 401);
    projections.logout = logout;
    assert.equal(
      (await context.cookies()).filter((c) =>
        c.name.startsWith('__Secure-moulai'),
      ).length,
      0,
    );
    assert(
      cookies.every(
        (c) =>
          c.httpOnly &&
          c.secure &&
          c.sameSite === 'Lax' &&
          c.path === '/api/web',
      ),
    );
    assert.equal(blocked.length, 0);
    results.push({
      username,
      status: 'PASS',
      ...projections,
      cookieFlags: cookies.map(
        ({ name, secure, httpOnly, sameSite, path }) => ({
          name,
          secure,
          httpOnly,
          sameSite,
          path,
        }),
      ),
      blockedOrigins: blocked,
    });
    fs.writeFileSync(
      path.join(output, 'lot1-browser.json'),
      JSON.stringify({ results }, null, 2),
    );
    await context.close();
  }
  console.log(JSON.stringify({ status: 'PASS', accounts: results.length }));
} catch (error) {
  // Playwright exception strings can contain filled credentials or callback URLs.
  const diagnostic = currentPage
    ? {
        path: new URL(currentPage.url()).pathname,
        traffic,
        cookies: (await currentPage.context().cookies()).map(
          ({ name, path, secure, httpOnly, expires }) => ({
            name,
            path,
            secure,
            httpOnly,
            expires,
          }),
        ),
        session: await currentPage.evaluate(() =>
          fetch('/api/web/organizations').then((r) => r.json()),
        ),
        text: (await currentPage.locator('body').innerText()).slice(0, 3500),
      }
    : {};
  let safe = JSON.stringify(
    { results, failure: { phase, type: error.name, uiErrors, ...diagnostic } },
    null,
    2,
  );
  for (const account of Object.values(accounts))
    safe = safe.replaceAll(account.password, '[REDACTED]');
  safe = safe.replace(/eyJ[A-Za-z0-9_.-]{30,}/g, '[TOKEN REDACTED]');
  fs.writeFileSync(
    path.join(output, 'lot1-browser.json'),
    redactEvidenceJson(safe),
  );
  console.log(JSON.stringify({ status: 'FAIL', phase, type: error.name }));
  process.exitCode = 1;
} finally {
  await browser.close();
}

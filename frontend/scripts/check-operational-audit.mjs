// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// MoulAI™ — read-only audit proof and keyboard/documentation continuity on the real local host.
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
const campaignId = JSON.parse(
  fs.readFileSync(path.join(output, 'lot2-pricing-browser.json'), 'utf8'),
).finalCampaign.id;
const results = [];
let phase = 'start';
const browser = await chromium.launch({ headless: true });
async function read(page, path) {
  return page.evaluate(async (path) => {
    const r = await fetch('/api/web/platform/pricing/' + path);
    return { status: r.status, body: await r.json() };
  }, path);
}
async function login(username) {
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
  const p = await c.newPage();
  await p.goto('https://127.0.0.1:5180/access');
  await p.getByRole('button', { name: 'Se connecter', exact: true }).click();
  await p.locator('#username').fill(username);
  await p.locator('#password').fill(accounts[username].password);
  await p.locator('#kc-login').click();
  await p.waitForURL(/https:\/\/127\.0\.0\.1:5180\/(workspace|platform)/);
  return p;
}
try {
  for (const username of ['owner-a', 'platform-reader']) {
    phase = username + ':denied-audit';
    const page = await login(username);
    for (const target of ['base/history', `campaigns/${campaignId}/history`]) {
      const r = await read(page, target);
      assert.equal(r.status, 403);
      results.push({ username, target, status: r.status });
    }
    await page.context().close();
  }
  phase = 'admin:retained-history';
  const page = await login('platform-admin');
  for (const invalid of ['0', '-1']) {
    const refused = await read(page, `campaigns/${invalid}/history`);
    assert.equal(refused.status, 422);
    results.push({
      label: 'positive-audit-identifier-required',
      identifier: invalid,
      status: refused.status,
    });
  }
  const history = await read(page, `campaigns/${campaignId}/history`);
  assert.equal(history.status, 200);
  assert.deepEqual(history.body.map((r) => r.action).reverse(), [
    'pricing.create',
    'pricing.update',
    'pricing.publish',
    'pricing.deactivate',
  ]);
  assert(
    history.body.every(
      (r) =>
        r.author_admin_id === 1 &&
        r.author_name &&
        Number.isFinite(Date.parse(r.recorded_at)) &&
        r.details.after &&
        r.details.reason,
    ),
  );
  const base = await read(page, 'base/history');
  assert.equal(base.status, 200);
  assert(base.body.length >= 4);
  assert.equal(base.body[0].details.after.amount, '3000.00');
  assert.equal(history.body[0].details.after.active, false);
  results.push(
    { label: 'committed-campaign-audit', entries: history.body.length },
    { label: 'retained-base-audit', entries: base.body.length },
  );
  phase = 'keyboard-help-retains-input';
  await page.goto('https://127.0.0.1:5180/platform/pricing');
  const field = page.locator('[name="baseAmount"]');
  await field.fill('3000.50');
  const help = page
    .locator('header')
    .getByRole('button', { name: '? Aide', exact: true });
  await help.focus();
  await page.keyboard.press('Enter');
  await page.getByRole('dialog').waitFor();
  await page.keyboard.press('Escape');
  await page.getByRole('dialog').waitFor({ state: 'hidden' });
  assert.equal(await field.inputValue(), '3000.50');
  results.push({
    label: 'keyboard-help-open-close-preserves-draft',
    status: 'PASS',
  });
  fs.writeFileSync(
    path.join(output, 'lot2-audit.json'),
    JSON.stringify(
      {
        status: 'PASS',
        results,
        campaignHistory: history.body,
        baseHistory: base.body,
      },
      null,
      2,
    ),
  );
  console.log(JSON.stringify({ status: 'PASS', checks: results.length }));
} catch (error) {
  fs.writeFileSync(
    path.join(output, 'lot2-audit.json'),
    JSON.stringify(
      { status: 'FAIL', phase, type: error.name, results },
      null,
      2,
    ),
  );
  console.log(JSON.stringify({ status: 'FAIL', phase, type: error.name }));
  process.exitCode = 1;
} finally {
  await browser.close();
}

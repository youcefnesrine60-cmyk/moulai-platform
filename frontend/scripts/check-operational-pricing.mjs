// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { redactEvidenceJson } from '../src/shared/access/logSafety.ts';
// MoulAI™ — authenticated direct API and real UI acceptance; local development only.
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
const results = [];
let phase = 'start';
const browser = await chromium.launch({ headless: true });
const call = async (page, path, body) =>
  page.evaluate(
    async ({ path, body }) => {
      const response = await fetch('/api/web/platform/pricing/' + path, {
        method: body ? 'POST' : 'GET',
        headers: body ? { 'Content-Type': 'application/json' } : {},
        body: body ? JSON.stringify(body) : undefined,
      });
      return { status: response.status, body: await response.json() };
    },
    { path, body },
  );
const check = (label, response, status = 200) => {
  results.push({
    label,
    status: response.status,
    ...(response.status === status ? {} : { refusal: response.body }),
  });
  assert.equal(response.status, status, label);
  return response.body;
};
async function login(username) {
  const context = await browser.newContext({
    ignoreHTTPSErrors: true,
    locale: 'fr-FR',
  });
  await context.route('**/*', (r) =>
    ['https://127.0.0.1:5180', 'https://127.0.0.1:8444'].includes(
      new URL(r.request().url()).origin,
    )
      ? r.continue()
      : r.abort(),
  );
  const page = await context.newPage();
  await page.goto('https://127.0.0.1:5180/access');
  await page.getByRole('button', { name: 'Se connecter', exact: true }).click();
  await page.locator('#username').fill(username);
  await page.locator('#password').fill(accounts[username].password);
  await page.locator('#kc-login').click();
  await page.waitForURL(/https:\/\/127\.0\.0\.1:5180\/(workspace|platform)/);
  return page;
}
try {
  const values = {
    name: 'LOCAL ACCEPTANCE ONLY ' + Date.now(),
    discount_percent: '2.125',
    starts_at: new Date(Date.now() + 86400000).toISOString(),
    expires_at: new Date(Date.now() + 604800000).toISOString(),
    priority: 1,
    restaurant_id: null,
    owner_id: null,
    plan_id: null,
  };
  for (const username of [
    'owner-a',
    'owner-b',
    'employee',
    'platform-reader',
  ]) {
    phase = username + ':direct-permission';
    const page = await login(username);
    check(username + ':base-read-denied', await call(page, 'base'), 403);
    check(
      username + ':base-write-denied',
      await call(page, 'base', {
        amount: '3000.00',
        expected_sha256: 'a'.repeat(64),
        effective: 'on_commit',
        reason: 'Permission refusal test',
      }),
      403,
    );
    check(
      username + ':campaign-read-denied',
      await call(page, 'campaigns'),
      403,
    );
    for (const operation of ['create', 'update', 'publish', 'deactivate'])
      check(
        username + ':' + operation + '-denied',
        await call(page, 'campaigns', {
          operation,
          reason: 'Permission refusal test',
          ...(operation === 'create'
            ? {}
            : { identifier: 1, expected_sha256: 'a'.repeat(64) }),
          ...(['create', 'update'].includes(operation) ? { values } : {}),
        }),
        403,
      );
    await page.context().close();
  }
  phase = 'admin:base-ui';
  const admin = await login('platform-admin');
  const original = check('actual-base-parameter', await call(admin, 'base'));
  assert.equal(original.amount, '3000.00');
  await admin.goto('https://127.0.0.1:5180/platform/pricing');
  const baseForm = admin.getByRole('form', {
    name: 'Base SaaS B — paramètre existant',
    exact: true,
  });
  await baseForm.locator('[name="baseAmount"]').fill('3000.01');
  await baseForm
    .locator('[name="baseReason"]')
    .fill('LOCAL ACCEPTANCE ONLY — reversible isolated check');
  await baseForm
    .getByRole('button', { name: 'Appliquer maintenant', exact: true })
    .click();
  await admin
    .getByRole('status')
    .filter({ hasText: 'Opération enregistrée en base locale.' })
    .waitFor();
  const changed = check('base-ui-persisted', await call(admin, 'base'));
  assert.equal(changed.amount, '3000.01');
  assert.notEqual(changed.revision, original.revision);
  check(
    'stale-base-change-refused',
    await call(admin, 'base', {
      amount: '3000.02',
      expected_sha256: original.sha256,
      effective: 'on_commit',
      reason: 'Stale version check',
    }),
    409,
  );
  await baseForm.locator('[name="baseAmount"]').fill('3000.00');
  await baseForm
    .locator('[name="baseReason"]')
    .fill('Restore approved 3000 DZD after isolated acceptance');
  await baseForm
    .getByRole('button', { name: 'Appliquer maintenant', exact: true })
    .click();
  await admin
    .getByRole('status')
    .filter({ hasText: 'Opération enregistrée en base locale.' })
    .waitFor();
  assert.equal(
    check('approved-base-restored', await call(admin, 'base')).amount,
    '3000.00',
  );
  phase = 'admin:campaign-lifecycle';
  let record = check(
    'create-future-draft',
    await call(admin, 'campaigns', {
      operation: 'create',
      reason: 'Isolated acceptance only',
      values,
    }),
  );
  assert.equal(record.state, 'draft');
  assert.equal(record.active, false);
  const stale = record.sha256;
  record = check(
    'update-draft',
    await call(admin, 'campaigns', {
      operation: 'update',
      identifier: record.id,
      expected_sha256: record.sha256,
      reason: 'Explicit draft adjustment',
      values: { ...values, priority: 2 },
    }),
  );
  check(
    'stale-campaign-edit-refused',
    await call(admin, 'campaigns', {
      operation: 'update',
      identifier: record.id,
      expected_sha256: stale,
      reason: 'Stale request',
      values,
    }),
    409,
  );
  const publish = {
    operation: 'publish',
    identifier: record.id,
    expected_sha256: record.sha256,
    reason: 'Future local acceptance campaign',
  };
  const concurrent = await Promise.all([
    call(admin, 'campaigns', publish),
    call(admin, 'campaigns', publish),
  ]);
  assert.deepEqual(concurrent.map((r) => r.status).sort(), [200, 409]);
  results.push({
    label: 'concurrent-publication-single-commit',
    statuses: concurrent.map((r) => r.status),
  });
  record = concurrent.find((r) => r.status === 200).body;
  check(
    'published-campaign-immutable',
    await call(admin, 'campaigns', {
      operation: 'update',
      identifier: record.id,
      expected_sha256: record.sha256,
      reason: 'Forbidden rewrite',
      values,
    }),
    409,
  );
  record = check(
    'deactivate-campaign',
    await call(admin, 'campaigns', {
      operation: 'deactivate',
      identifier: record.id,
      expected_sha256: record.sha256,
      reason: 'End isolated acceptance — no commercial activation',
    }),
  );
  assert.equal(record.active, false);
  assert.equal(record.state, 'deactivated');
  check(
    'duplicate-deactivation-refused',
    await call(admin, 'campaigns', {
      operation: 'deactivate',
      identifier: record.id,
      expected_sha256: record.sha256,
      reason: 'Duplicate refusal',
    }),
    409,
  );
  await admin.reload();
  await admin
    .getByRole('heading', { name: 'Offres SaaS — campagnes', exact: true })
    .waitFor();
  await admin.screenshot({
    path: path.join(output, 'lot2-pricing-fr-desktop.png'),
    fullPage: true,
  });
  fs.writeFileSync(
    path.join(output, 'lot2-pricing-browser.json'),
    JSON.stringify(
      {
        status: 'PASS',
        results,
        finalCampaign: record,
        base: await call(admin, 'base'),
      },
      null,
      2,
    ),
  );
  console.log(JSON.stringify({ status: 'PASS', checks: results.length }));
} catch (error) {
  let safe = JSON.stringify(
    {
      status: 'FAIL',
      phase,
      type: error.name,
      message: error.message,
      results,
    },
    null,
    2,
  );
  for (const account of Object.values(accounts))
    safe = safe.replaceAll(account.password, '[REDACTED]');
  safe = safe.replace(/eyJ[A-Za-z0-9_.-]{30,}/g, '[TOKEN REDACTED]');
  fs.writeFileSync(
    path.join(output, 'lot2-pricing-browser.json'),
    redactEvidenceJson(safe),
  );
  console.log(JSON.stringify({ status: 'FAIL', phase, type: error.name }));
  process.exitCode = 1;
} finally {
  await browser.close();
}

// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Exercise actual campaign forms against the owned local database; never supply commercial feature prices.
import { chromium } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';

const root = path.resolve(import.meta.dirname, '../..');
const id = '3fb5f85a6cc94868acaf7d95b3777a16';
const directory = path.join(root, 'artifacts/operational-local', id);
const output = path.join(root, 'artifacts/operational-integration-20261107');
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
let phase = 'login';
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  ignoreHTTPSErrors: true,
  locale: 'fr-FR',
  timezoneId: 'America/New_York',
});
await context.route('**/*', (route) =>
  ['https://127.0.0.1:5180', 'https://127.0.0.1:8444'].includes(
    new URL(route.request().url()).origin,
  )
    ? route.continue()
    : route.abort(),
);
const page = await context.newPage();
async function call(body) {
  return page.evaluate(async (body) => {
    const response = await fetch('/api/web/platform/pricing/campaigns', {
      method: body ? 'POST' : 'GET',
      headers: body ? { 'Content-Type': 'application/json' } : {},
      body: body ? JSON.stringify(body) : undefined,
    });
    return { status: response.status, body: await response.json() };
  }, body);
}
async function submitForm(button) {
  const response = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/web/platform/pricing/campaigns') &&
      response.request().method() === 'POST',
  );
  await page.getByRole('button', { name: button, exact: true }).click();
  const received = await response;
  assert.equal(received.status(), 200);
  return received.json();
}
try {
  await page.goto('https://127.0.0.1:5180/access');
  await page.getByRole('button', { name: 'Se connecter', exact: true }).click();
  await page.locator('#username').fill('platform-admin');
  await page.locator('#password').fill(accounts['platform-admin'].password);
  await page.locator('#kc-login').click();
  await page.waitForURL(/https:\/\/127\.0\.0\.1:5180\/platform/);
  await page.goto('https://127.0.0.1:5180/platform/pricing');
  phase = 'create-through-ui';
  const name = 'LOCAL UI ACCEPTANCE ONLY ' + Date.now();
  const start = new Date(Date.now() + 3 * 86400000).toISOString().slice(0, -1);
  const end = new Date(Date.now() + 4 * 86400000).toISOString().slice(0, -1);
  for (const [field, value] of Object.entries({
    name,
    discount_percent: '1.23456789',
    starts_at: start,
    expires_at: end,
    priority: '2',
    reason: 'Local UI acceptance only; not a commercial offer',
  }))
    await page.locator(`input[name="${field}"]`).fill(value);
  let record = await submitForm('Créer le brouillon');
  assert.equal(record.discount_percent, '1.23456789');
  assert.equal(Date.parse(record.starts_at), Date.parse(start + 'Z'));
  assert.equal(Date.parse(record.expires_at), Date.parse(end + 'Z'));
  assert.equal(record.active, false);
  results.push({
    label: 'UI-draft-exact-decimal-and-UTC-in-non-UTC-device',
    status: 'PASS',
  });
  await page.reload();
  let card = page
    .locator('article')
    .filter({ has: page.getByRole('heading', { name, exact: true }) });
  await card
    .getByRole('button', { name: 'Modifier le brouillon', exact: true })
    .click();
  assert.equal(
    Date.parse(
      (await page.locator('input[name="starts_at"]').inputValue()) + 'Z',
    ),
    Date.parse(record.starts_at),
  );
  const editedName = name + ' EDITED';
  await page.locator('input[name="name"]').fill(editedName);
  await page
    .locator('input[name="reason"]')
    .fill('UI name correction; exact dates retained');
  phase = 'edit-through-ui';
  const edited = await submitForm('Enregistrer le brouillon');
  assert.equal(edited.starts_at, record.starts_at);
  assert.equal(edited.expires_at, record.expires_at);
  record = edited;
  results.push({
    label: 'UI-edit-and-reload-preserve-persisted-instants',
    status: 'PASS',
  });
  await page.reload();
  card = page.locator('article').filter({
    has: page.getByRole('heading', { name: editedName, exact: true }),
  });
  phase = 'publish-through-ui';
  await page
    .locator('input[name="reason"]')
    .fill('Local future publication acceptance');
  let pending = page.waitForResponse(
    (r) =>
      r.url().endsWith('/api/web/platform/pricing/campaigns') &&
      r.request().method() === 'POST',
  );
  await card
    .getByRole('button', { name: 'Publier la campagne', exact: true })
    .click();
  let received = await pending;
  assert.equal(received.status(), 200);
  record = await received.json();
  assert.equal(record.state, 'published');
  results.push({
    label: 'UI-publication-server-target-revalidation',
    status: 'PASS',
  });
  phase = 'immutable-and-deactivate';
  const immutable = await call({
    operation: 'update',
    identifier: record.id,
    expected_sha256: record.sha256,
    reason: 'Refused published rewrite',
    values: {
      name: editedName,
      discount_percent: '1.23456789',
      starts_at: record.starts_at,
      expires_at: record.expires_at,
      priority: 2,
      restaurant_id: null,
      owner_id: null,
      plan_id: null,
    },
  });
  assert.equal(immutable.status, 409);
  results.push({ label: 'published-rewrite-refused', status: 409 });
  await page.reload();
  card = page.locator('article').filter({
    has: page.getByRole('heading', { name: editedName, exact: true }),
  });
  await page
    .locator('input[name="reason"]')
    .fill('End isolated acceptance; no commercial activation');
  pending = page.waitForResponse(
    (r) =>
      r.url().endsWith('/api/web/platform/pricing/campaigns') &&
      r.request().method() === 'POST',
  );
  await card.getByRole('button', { name: /Désactiver/, exact: false }).click();
  received = await pending;
  assert.equal(received.status(), 200);
  record = await received.json();
  assert.equal(record.state, 'deactivated');
  assert.equal(record.active, false);
  results.push({ label: 'UI-deactivation-persisted', status: 'PASS' });
  const duplicate = await call({
    operation: 'deactivate',
    identifier: record.id,
    expected_sha256: record.sha256,
    reason: 'Repeated intent refusal',
  });
  assert.equal(duplicate.status, 409);
  results.push({ label: 'duplicate-deactivation-refused', status: 409 });
  const final = await call();
  assert.equal(final.status, 200);
  assert.equal(final.body.find((row) => row.id === record.id).active, false);
  fs.writeFileSync(
    path.join(output, 'lot2-campaign-ui.json'),
    JSON.stringify(
      {
        status: 'PASS',
        results,
        finalCampaign: record,
        deviceTimezone: 'America/New_York',
        inputs: 'explicit UTC',
      },
      null,
      2,
    ),
  );
  console.log(JSON.stringify({ status: 'PASS', checks: results.length }));
} catch (error) {
  fs.writeFileSync(
    path.join(output, 'lot2-campaign-ui.json'),
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

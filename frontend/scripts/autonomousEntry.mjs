// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Real native Keycloak registration and real five-minute expiry; no clock or HTTP response mock.
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {
  root,
  origin,
  newContext,
  request,
  checked,
} from './operationalHarness.mjs';

export async function prepareOwner(
  browser,
  {
    output = path.join(
      root,
      'artifacts/operational-followup-20261109/autonomous',
    ),
    exerciseExpiry = true,
  } = {},
) {
  fs.mkdirSync(output, { recursive: true });
  const name = 'self-' + crypto.randomUUID().replaceAll('-', '').slice(0, 12);
  const password = crypto.randomBytes(24).toString('base64url');
  const privateFile = path.join(
    root,
    `artifacts/operational-local/3fb5f85a6cc94868acaf7d95b3777a16/private/self-registration-marker-${name}.json`,
  );
  assert(
    !fs.existsSync(privateFile),
    'Do not repeat this account-creation acceptance automatically.',
  );
  fs.writeFileSync(
    privateFile,
    JSON.stringify({ username: name, containsCredentials: false }),
  );
  const checks = [];
  const persist = (status) =>
    fs.writeFileSync(
      path.join(output, 'entry-and-draft.json'),
      JSON.stringify(
        {
          status,
          checks,
          realProvider: 'Keycloak-local',
          externalCalls: 0,
          AI_calls: 0,
          passwordCustody:
            'Keycloak only; generated test password remains in this process RAM, never persisted',
        },
        null,
        2,
      ),
    );
  async function registrationPage() {
    const page = await (await newContext(browser)).newPage();
    await page.goto(origin + '/access');
    await page
      .getByRole('link', {
        name: 'Créer mon compte',
        exact: true,
      })
      .click();
    await page.locator('#username').waitFor();
    assert(new URL(page.url()).origin === 'https://127.0.0.1:8444');
    return page;
  }
  async function fillAccount(page, username) {
    await page.locator('#username').fill(username);
    await page.locator('#firstName').fill('Fictitious');
    await page.locator('#lastName').fill('Local Owner');
    await page.locator('#email').fill(username + '@moulai.local.invalid');
    await page.locator('#password').fill(password);
    await page.locator('#password-confirm').fill(password);
  }
  const interrupted = await registrationPage();
  await interrupted.locator('#username').fill(name + '-interrupted');
  await interrupted.goto(origin + '/access');
  assert.equal(checked(await request(interrupted, '/api/web/session')), null);
  await interrupted.context().close();
  checks.push({ step: 'interrupted-registration-no-session', status: 'PASS' });
  persist('RUNNING');
  const owner = await registrationPage();
  await fillAccount(owner, name);
  await owner.locator('input[type="submit"]').click();
  await owner.waitForURL('**/workspace', { timeout: 60000 });
  const session = checked(await request(owner, '/api/web/session'));
  fs.writeFileSync(
    path.join(output, 'registration-session-facts.json'),
    JSON.stringify({
      source: session?.source,
      area: session?.area,
      expiresAt: session?.expiresAt,
      now: Date.now() / 1000,
      platformPermissions: session?.platformPermissions,
    }),
  );
  assert.equal(session.source, 'authenticated-local');
  assert.equal(session.area, 'tenant');
  assert.deepEqual(session.platformPermissions, []);
  assert(session.expiresAt > Date.now() / 1000);
  checks.push({
    step: 'native-self-registration-auth-code-pkce',
    status: 'PASS',
    subject: session.subject,
    expiresAt: session.expiresAt,
    emailOwnershipVerified: false,
  });
  const duplicate = await registrationPage();
  await fillAccount(duplicate, name);
  await duplicate.locator('input[type="submit"]').click();
  await duplicate
    .locator(
      '#input-error-username, #input-error-email, .pf-v5-c-alert__description, .kc-feedback-text',
    )
    .first()
    .waitFor({ timeout: 30000 });
  assert(new URL(duplicate.url()).origin === 'https://127.0.0.1:8444');
  await duplicate.context().close();
  checks.push({ step: 'duplicate-provider-account-refused', status: 'PASS' });
  persist('RUNNING');
  if (!exerciseExpiry) return owner;
  await owner
    .getByRole('link', {
      name: 'Créer mon entreprise et mon premier établissement',
      exact: true,
    })
    .click();
  await owner
    .locator('input[name="company_name"]')
    .fill('LOCAL-FAKE — Dossier conservé après expiration');
  const saved = owner.waitForResponse(
    (r) =>
      r.request().method() === 'PUT' &&
      new URL(r.url()).pathname === '/api/web/enrollment-draft',
  );
  await owner
    .getByRole('button', {
      name: 'Conserver ce brouillon 30 minutes',
      exact: true,
    })
    .click();
  const savedResponse = await saved;
  assert.equal(savedResponse.status(), 200, 'enrollment-draft HTTP status');
  const forbidden = await owner.evaluate(async () => {
    const r = await fetch('/api/web/enrollment-draft', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        company_name: 'Local',
        password: 'UNACCEPTABLE_TEST_FIELD',
      }),
    });
    return r.status;
  });
  assert.equal(forbidden, 422);
  assert.equal(checked(await request(owner, '/api/web/enrollment')), null);
  checks.push({
    step: 'encrypted-explicit-draft-no-dossier-or-secret-field',
    status: 'PASS',
  });
  persist('RUNNING');
  const untilWarning = Math.max(
    0,
    session.expiresAt * 1000 - Date.now() - 59000,
  );
  await owner.waitForTimeout(untilWarning);
  await owner.locator('.session-warning').waitFor({ timeout: 6000 });
  await owner.screenshot({
    path: path.join(output, 'real-expiry-warning.png'),
    fullPage: true,
  });
  checks.push({ step: 'real-expiry-warning-before-60s', status: 'PASS' });
  persist('RUNNING');
  await owner.waitForURL('**/access', { timeout: 75000 });
  assert.equal(checked(await request(owner, '/api/web/session')), null);
  await owner.goto(origin + '/api/web/auth/login');
  await owner.waitForURL('**/workspace', { timeout: 60000 });
  const renewed = checked(await request(owner, '/api/web/session'));
  assert.equal(renewed.subject, session.subject);
  assert.equal(renewed.issuer, session.issuer);
  await owner
    .getByRole('link', {
      name: 'Créer mon entreprise et mon premier établissement',
      exact: true,
    })
    .click();
  await owner.locator('input[name="company_name"]').waitFor();
  assert.equal(
    await owner.locator('input[name="company_name"]').inputValue(),
    '',
  );
  await owner
    .getByRole('button', { name: 'Reprendre mon brouillon', exact: true })
    .click();
  await owner.waitForFunction(() =>
    document
      .querySelector('input[name="company_name"]')
      ?.value.includes('Dossier conservé'),
  );
  assert.equal(checked(await request(owner, '/api/web/enrollment')), null);
  await owner.screenshot({
    path: path.join(output, 'draft-restored-after-real-reauthentication.png'),
    fullPage: true,
  });
  checks.push({
    step: 'same-identity-reauth-explicit-restore-no-command-replay',
    status: 'PASS',
    elapsedRealExpiry: true,
  });
  persist('PASS');
  await owner.goto(origin + '/workspace');
  return owner;
}

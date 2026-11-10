// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { redactEvidenceJson } from '../src/shared/access/logSafety.ts';
// MoulAI™ — real local invitation, self-acceptance, activation and immediate revocation.
// All writes target the owned disposable development database through authenticated HTTP.
import { chromium } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
const root = path.resolve(import.meta.dirname, '../..');
const id = '3fb5f85a6cc94868acaf7d95b3777a16';
const directory = path.join(root, 'artifacts/operational-local', id);
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
const output = path.join(root, 'artifacts/operational-integration-20261107');
const route = '/api/web/organizations/8/restaurants/6/branches/4/dining';
const results = [];
let phase = 'start';
const browser = await chromium.launch({ headless: true });
const call = async (page, url, body) =>
  page.evaluate(
    async ({ url, body }) => {
      const r = await fetch(url, {
        method: body ? 'POST' : 'GET',
        headers: body ? { 'Content-Type': 'application/json' } : {},
        body: body ? JSON.stringify(body) : undefined,
      });
      return { status: r.status, body: await r.json() };
    },
    { url, body },
  );
async function login(username) {
  const context = await browser.newContext({
    ignoreHTTPSErrors: true,
    locale: 'fr-FR',
  });
  await context.route('**/*', async (r) =>
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
  await page.waitForURL(/https:\/\/127\.0\.0\.1:5180\/workspace/);
  return page;
}
try {
  phase = 'owner-login';
  const owner = await login('owner-a');
  const check = async (label, response, status = 200) => {
    results.push({
      label,
      status: response.status,
      ...(response.status !== status ? { refusal: response.body } : {}),
    });
    assert.equal(response.status, status, label);
    return response.body;
  };
  const initial = await check(
    'initial-workspace',
    await call(owner, route + '/workspace'),
  );
  if (!initial.policy) {
    const ownerMember = initial.memberships.find((m) => m.role === 'owner');
    await check(
      'explicit-development-policy',
      await call(owner, route + '/commands', {
        operation: 'policy',
        data: {
          timezone: 'Africa/Algiers',
          response_seconds: 300,
          hold_seconds: 600,
          lateness_seconds: 600,
          preparation_seconds: 900,
          cleaning_seconds: 600,
          confirmation_seconds: 600,
          confirmation_scope: 'tables',
          alert_offsets_seconds: [300, 0],
          service_recipients: [ownerMember.id],
          escalation_recipients: [],
          currencies: { DZD: 2 },
          payment_instructions: {
            cash: 'Development only — no real collection',
          },
          terms: 'Synthetic isolated acceptance policy, not commercial terms',
        },
      }),
    );
  }
  phase = 'reference-ui';
  await owner.goto(
    'https://127.0.0.1:5180/workspace/organizations/8/restaurants/6/tables?branch=4',
  );
  await owner
    .getByRole('button', { name: 'Configuration', exact: true })
    .click();
  const form = owner.locator('form[data-operation="reference"]');
  await form.locator('..').locator(':scope > summary').click();
  const code = 'integrated-' + Date.now();
  await form.locator('[name="kind"]').selectOption('view');
  for (const [name, value] of Object.entries({
    code,
    fr: 'Vue intégrée locale',
    en: 'Integrated local view',
    ar: 'إطلالة محلية متكاملة',
  }))
    await form.locator(`[name="${name}"]`).fill(value);
  await form
    .getByRole('button', { name: 'Valider et enregistrer', exact: true })
    .click();
  await owner
    .getByRole('status')
    .filter({ hasText: /enregistr|persist/i })
    .first()
    .waitFor();
  await owner.reload();
  let snap = await check(
    'workspace-after-reload',
    await call(owner, route + '/workspace'),
  );
  assert(snap.references.some((r) => r.code === code));
  results.push({
    label: 'reference-created-via-ui-retained-after-reload',
    code,
  });
  phase = 'invite';
  const invited = await check(
    'owner-invites-existing-account',
    await call(owner, route + '/staff', {
      operation: 'invite',
      issuer: accounts.employee.issuer,
      subject: accounts.employee.subject,
      employee_code: 'LOCAL-EMPLOYEE',
      display_name: 'Local employee',
    }),
  );
  const memberId = invited.identifier;
  const state = async () => {
    const s = await check(
      'membership-read',
      await call(owner, route + '/workspace'),
    );
    return s.memberships.find((m) => m.id === memberId);
  };
  const status = async (value) =>
    check(
      'owner-status-' + value,
      await call(owner, route + '/staff', {
        operation: 'status',
        membership_id: memberId,
        expected_revision: (await state()).revision,
        status: value,
        reason: 'Local controlled integration acceptance',
      }),
    );
  if (process.argv.includes('--prepare-new-invitation')) {
    await status('revoked');
    console.log(
      JSON.stringify({ status: 'revoked-via-authorized-route', memberId }),
    );
    process.exitCode = 0;
  } else {
    await check(
      'activation-before-personal-acceptance-denied',
      await call(owner, route + '/staff', {
        operation: 'status',
        membership_id: memberId,
        expected_revision: (await state()).revision,
        status: 'active',
        reason: 'Acceptance precondition test',
      }),
      409,
    );
    phase = 'employee-self-acceptance';
    const employee = await login('employee');
    await employee.goto('https://127.0.0.1:5180/workspace/invitations');
    await employee.locator('details > summary').first().click();
    await employee
      .getByRole('button', { name: /Accepter/ })
      .first()
      .click();
    await employee
      .getByRole('status')
      .filter({ hasText: /accept/i })
      .first()
      .waitFor();
    await check(
      'pending-still-cannot-enter-restaurant',
      await call(employee, route + '/workspace'),
      403,
    );
    phase = 'activate-and-grant';
    await status('active');
    await check(
      'no-implicit-dining-capability-after-activation',
      await call(employee, route + '/workspace'),
      403,
    );
    await check(
      'explicit-dining-read-grant',
      await call(owner, route + '/commands', {
        operation: 'grant',
        membership_id: memberId,
        capability: 'read',
        actor_kind: 'human',
        active: true,
      }),
    );
    await check(
      'employee-reads-granted-restaurant',
      await call(employee, route + '/workspace'),
    );
    await check(
      'employee-cannot-read-foreign-establishment',
      await call(
        employee,
        '/api/web/organizations/9/restaurants/7/branches/5/dining/workspace',
      ),
      403,
    );
    await check(
      'employee-cannot-configure',
      await call(employee, route + '/commands', {
        operation: 'reference',
        identifier: null,
        acknowledge_conflicts: false,
        data: {
          kind: 'view',
          code: 'denied',
          labels: { fr: 'Interdit', en: 'Denied', ar: 'مرفوض' },
          active: true,
          pricing_ref: null,
        },
      }),
      403,
    );
    phase = 'suspension';
    await status('suspended');
    await check(
      'suspension-denies-existing-browser-session',
      await call(employee, route + '/workspace'),
      403,
    );
    phase = 'reactivation';
    await status('active');
    await check(
      'reactivation-does-not-restore-old-capability',
      await call(employee, route + '/workspace'),
      403,
    );
    await check(
      'new-explicit-read-grant',
      await call(owner, route + '/commands', {
        operation: 'grant',
        membership_id: memberId,
        capability: 'read',
        actor_kind: 'human',
        active: true,
      }),
    );
    await check(
      'read-restored-only-after-new-grant',
      await call(employee, route + '/workspace'),
    );
    phase = 'revocation';
    await status('revoked');
    await check(
      'revocation-denies-existing-browser-session',
      await call(employee, route + '/workspace'),
      403,
    );
    const final = await state();
    assert.equal(final.status, 'revoked');
    fs.writeFileSync(
      path.join(output, 'lot1-membership.json'),
      JSON.stringify({ status: 'PASS', memberId, results, final }, null, 2),
    );
    console.log(JSON.stringify({ status: 'PASS', checks: results.length }));
  }
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
    path.join(output, 'lot1-membership.json'),
    redactEvidenceJson(safe),
  );
  console.log(JSON.stringify({ status: 'FAIL', phase, type: error.name }));
  process.exitCode = 1;
} finally {
  await browser.close();
}

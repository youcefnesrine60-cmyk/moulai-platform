// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Real owner UI replacement of an explicitly prepared synthetic legacy-metadata offer.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import {
  root,
  origin,
  launch,
  login,
  request,
  checked,
} from './operationalHarness.mjs';

const output = path.join(root, 'artifacts/operational-followup-20261109');
const fixture = JSON.parse(
  fs.readFileSync(path.join(output, 'obsolete-offer-fixture.json'), 'utf8'),
);
const route = '/api/web/organizations/11/restaurants/9/saas-payments';
const browser = await launch(),
  checks = [];
let phase = 'owner-login';
function observe(phase) {
  execFileSync(
    path.join(root, '.venv/Scripts/python.exe'),
    [
      '-I',
      '-B',
      path.join(root, 'scripts/verify_operational_requote.py'),
      '--phase',
      phase,
    ],
    { cwd: root, stdio: ['ignore', 'pipe', 'pipe'] },
  );
}
try {
  const page = await login(browser, 'billing-scenario');
  await page.goto(origin + '/workspace/organizations/11/restaurants/9/offer');
  const panel = page
    .getByRole('heading', {
      name: 'Abonnement SaaS et justificatifs',
      exact: true,
    })
    .locator('..');
  const previewButton = panel.getByRole('button', {
    name: 'Examiner le remplacement de cette offre',
    exact: true,
  });
  await previewButton.waitFor();
  phase = 'preview';
  const pending = page.waitForResponse(
    (r) =>
      r.request().method() === 'POST' &&
      new URL(r.url()).pathname.endsWith(
        `/saas-payments/${fixture.payment_id}/replacement`,
      ),
  );
  await previewButton.click();
  const response = await pending;
  assert.equal(response.status(), 200);
  const preview = await response.json();
  assert(preview.review.reasons.includes('payment_adjustment_rates'));
  assert.equal(preview.review.parameters.B, '3000.00000000');
  assert.equal(Number(preview.review.pricing.final_amount_due), 2940);
  observe('preview');
  checks.push({
    step: 'authenticated-ui-preview-no-persisted-change',
    status: 'PASS',
    reasons: preview.review.reasons,
  });
  await page.evaluate(() => window.moulaiTheme.choose('light'));
  await panel.screenshot({
    path: path.join(output, 'requote-preview-fr-light-desktop.png'),
  });
  phase = 'confirmation';
  const confirmation = page.waitForResponse(
    (r) =>
      r.request().method() === 'POST' &&
      new URL(r.url()).pathname.endsWith(
        `/saas-payments/${fixture.payment_id}/replacement`,
      ),
  );
  await panel
    .getByRole('button', {
      name: 'Confirmer ces nouveaux montants et remplacer l’offre non payée',
      exact: true,
    })
    .click();
  const confirmed = await confirmation;
  assert.equal(confirmed.status(), 200);
  const result = await confirmed.json();
  assert.notEqual(result.payment.id, fixture.payment_id);
  assert.equal(result.payment.status, 'pending');
  assert.equal(Number(result.payment.amount), 2940);
  const repeated = checked(
    await request(page, `${route}/${fixture.payment_id}/replacement`, {
      currency: 'DZD',
      approval: preview.approval,
    }),
  );
  assert.equal(repeated.reused, true);
  assert.equal(repeated.payment.id, result.payment.id);
  checks.push({
    step: 'explicit-confirmation-and-idempotent-retry',
    status: 'PASS',
    oldPayment: fixture.payment_id,
    newPayment: result.payment.id,
    activation: false,
  });
  await page.reload();
  await panel
    .getByRole('button', {
      name: 'Examiner le remplacement de cette offre',
      exact: true,
    })
    .waitFor();
  const payments = checked(await request(page, route));
  assert.equal(
    payments.find((p) => p.id === fixture.payment_id).status,
    'cancelled',
  );
  assert.equal(payments.filter((p) => p.status === 'pending').length, 1);
  assert.equal(payments.find((p) => p.id === 1).status, 'paid');
  await page.evaluate(() => window.moulaiTheme.choose('dark'));
  await panel.screenshot({
    path: path.join(output, 'requote-confirmed-fr-dark-desktop.png'),
  });
  phase = 'foreign-permission';
  const foreign = await login(browser, 'owner-b');
  assert.equal(
    (
      await request(foreign, `${route}/${fixture.payment_id}/replacement`, {
        currency: 'DZD',
        approval: preview.approval,
      })
    ).status,
    403,
  );
  observe('complete');
  checks.push({
    step: 'foreign-direct-api-refused-and-independent-observer',
    status: 'PASS',
    httpStatus: 403,
  });
  fs.writeFileSync(
    path.join(output, 'requote-ui.json'),
    JSON.stringify(
      {
        status: 'PASS',
        checks,
        syntheticLegacyMetadataFixture: true,
        newOffer: result.payment.id,
        AI_calls: 0,
        bankTransactions: 0,
      },
      null,
      2,
    ),
  );
  console.log(
    JSON.stringify({
      status: 'PASS',
      checks: checks.length,
      newPayment: result.payment.id,
    }),
  );
} catch (error) {
  fs.writeFileSync(
    path.join(output, 'requote-ui-failure.json'),
    JSON.stringify(
      {
        status: 'FAIL',
        phase,
        type: error.name,
        location: error.stack
          ?.split('\n')
          .filter((s) => s.includes('check-operational-requote.mjs')),
      },
      null,
      2,
    ),
  );
  console.log(JSON.stringify({ status: 'FAIL', phase, type: error.name }));
  process.exitCode = 1;
} finally {
  await browser.close();
}

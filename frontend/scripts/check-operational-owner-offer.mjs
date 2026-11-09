// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Actual tenant billing reads never confer platform pricing-edit rights.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {
  launch,
  login,
  request,
  checked,
  output,
  origin,
} from './operationalHarness.mjs';
const browser = await launch(),
  results = [];
let phase = 'owner-read';
try {
  const owner = await login(browser, 'owner-a');
  const own = '/api/web/organizations/8/restaurants/6/offer';
  const offer = checked(await request(owner, own));
  assert.equal(Number(offer.base_reference), 3000);
  assert.equal(offer.binding_quote, false);
  assert.deepEqual(offer.plans, []);
  assert.deepEqual(offer.blockers, ['subscription_plans_missing']);
  results.push({
    label: 'owned-current-B-with-explicit-missing-plan-block',
    status: 'PASS',
  });
  checked(await request(owner, '/api/web/platform/pricing/base'), 403);
  results.push({
    label: 'owner-no-administrative-edit-permission',
    status: 403,
  });
  checked(
    await request(owner, '/api/web/organizations/8/restaurants/7/offer'),
    403,
  );
  results.push({
    label: 'foreign-restaurant-with-modified-identifier-refused',
    status: 403,
  });
  const input = {
    plan_id: 1,
    billing_cycle: 'monthly',
    payment_method: 'electronic',
    currency: 'DZD',
    additional_feature_ids: [],
  };
  checked(
    await request(owner, own + '/simulation', { ...input, amount: '1' }),
    422,
  );
  const blocked = await request(owner, own + '/simulation', input);
  checked(blocked, 409);
  results.push({
    label: 'no-zero-history-or-invented-plan-simulation',
    status: 409,
    code: blocked.body.detail.code,
  });
  await owner.goto(origin + '/workspace/organizations/8/restaurants/6/offer');
  await owner
    .getByRole('heading', { name: 'Mon offre SaaS', exact: true })
    .waitFor();
  assert.equal(
    await owner
      .getByRole('button', { name: 'Simuler sans souscrire', exact: true })
      .isDisabled(),
    true,
  );
  await owner.screenshot({
    path: path.join(output, 'owner-offer-fr-light.png'),
    fullPage: true,
  });
  results.push({
    label: 'actual-owned-interface-shows-unavailable-plan-without-fixture',
    status: 'PASS',
  });
  for (const username of [
    'owner-b',
    'd1-service',
    'd1-collector',
    'platform-admin',
  ]) {
    phase = 'direct-billing-permission-' + username;
    const page = await login(browser, username);
    checked(await request(page, own), 403);
    checked(await request(page, own + '/simulation', input), 403);
    results.push({
      label: 'read-and-simulation-denied',
      username,
      status: 403,
    });
  }
  fs.writeFileSync(
    path.join(output, 'owner-offer.json'),
    JSON.stringify({ status: 'PASS', results, offer }, null, 2),
  );
  console.log(JSON.stringify({ status: 'PASS', checks: results.length }));
} catch (error) {
  fs.writeFileSync(
    path.join(output, 'owner-offer.json'),
    JSON.stringify(
      {
        status: 'FAIL',
        phase,
        type: error.name,
        httpStatus: error.safeStatus,
        domainCode: error.safeCode,
        results,
      },
      null,
      2,
    ),
  );
  console.log(
    JSON.stringify({
      status: 'FAIL',
      phase,
      type: error.name,
      httpStatus: error.safeStatus,
      domainCode: error.safeCode,
    }),
  );
  process.exitCode = 1;
} finally {
  await browser.close();
}

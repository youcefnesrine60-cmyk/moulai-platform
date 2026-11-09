// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Verify the real local editor and its audit; never dispatch reminders or change recipients.
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
const endpoint = '/api/web/platform/pricing/reminders';
let phase = 'initial-policy';
try {
  const admin = await login(browser, 'platform-admin');
  const initial = checked(await request(admin, endpoint));
  assert.deepEqual(initial.days, [14, 7, 1, 0]);
  assert.equal(initial.delivery_active, false);
  assert.equal(initial.responsible_configured, false);
  const baseBefore = checked(
    await request(admin, '/api/web/platform/pricing/base'),
  );
  assert.equal(Number(baseBefore.amount), 3000);
  const historyBefore = checked(await request(admin, endpoint + '/history'));
  await admin.goto(origin + '/platform/pricing');
  phase = 'actual-form';
  await admin.locator('input[name="reminderDays"]').fill('21,14,7,1,0');
  await admin
    .locator('input[name="reminderReason"]')
    .fill(
      'LOCAL ONLY — editor acceptance; restore approved offsets immediately',
    );
  const submitted = admin.waitForResponse(
    (r) => r.url().endsWith(endpoint) && r.request().method() === 'POST',
  );
  await admin
    .locator('input[name="reminderDays"]')
    .locator('..')
    .locator('..')
    .getByRole('button')
    .click();
  assert.equal((await submitted).status(), 200);
  const changed = checked(await request(admin, endpoint));
  assert.deepEqual(changed.days, [21, 14, 7, 1, 0]);
  assert.notEqual(changed.sha256, initial.sha256);
  results.push({
    label: 'actual-form-commits-policy-with-new-version',
    status: 'PASS',
  });
  phase = 'stale-refusal';
  checked(
    await request(admin, endpoint, {
      days: [14, 7, 1, 0],
      reason: 'Stale edit must fail',
      expected_sha256: initial.sha256,
    }),
    409,
  );
  results.push({ label: 'stale-policy-refused', status: 409 });
  phase = 'restore-approved-offsets';
  checked(
    await request(admin, endpoint, {
      days: [14, 7, 1, 0],
      reason: 'Restore approved 14/7/1/0 after local acceptance',
      expected_sha256: changed.sha256,
    }),
  );
  const final = checked(await request(admin, endpoint));
  assert.deepEqual(final.days, initial.days);
  assert.equal(final.delivery_active, false);
  assert.equal(final.responsible_configured, false);
  const baseAfter = checked(
    await request(admin, '/api/web/platform/pricing/base'),
  );
  assert.equal(baseAfter.amount, baseBefore.amount);
  const history = checked(await request(admin, endpoint + '/history'));
  assert.equal(history.length, historyBefore.length + 2);
  for (const row of history.slice(0, 2)) {
    assert.equal(row.action, 'pricing.reminders.change');
    assert(row.author_name);
    assert(row.recorded_at);
    assert(row.details.before && row.details.after);
  }
  results.push({
    label: 'approved-offsets-restored-B-unchanged-two-retained-audits',
    status: 'PASS',
  });
  for (const username of ['owner-a', 'platform-reader', 'd1-collector']) {
    phase = 'permission-' + username;
    const page = await login(browser, username);
    checked(await request(page, endpoint), 403);
    checked(
      await request(page, endpoint, {
        days: [14, 7, 1, 0],
        reason: 'Must be denied',
        expected_sha256: final.sha256,
      }),
      403,
    );
    checked(await request(page, endpoint + '/history'), 403);
    results.push({
      label: 'direct-read-write-history-denied',
      username,
      status: 403,
    });
  }
  fs.writeFileSync(
    path.join(output, 'reminder-editor.json'),
    JSON.stringify(
      { status: 'PASS', results, final, history: history.slice(0, 2) },
      null,
      2,
    ),
  );
  console.log(JSON.stringify({ status: 'PASS', checks: results.length }));
} catch (error) {
  fs.writeFileSync(
    path.join(output, 'reminder-editor-failure-' + Date.now() + '.json'),
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

// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Observe actual five-minute expiry without changing clocks, token lifetimes or server sessions.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {
  launch,
  login,
  request,
  checked,
  origin,
  output,
} from './operationalHarness.mjs';
const browser = await launch();
let phase = 'sign-in';
try {
  const page = await login(browser, 'platform-admin');
  await page.goto(origin + '/platform/pricing');
  const before = checked(await request(page, '/api/web/platform/pricing/base'));
  let mutations = 0;
  page.on('request', (r) => {
    if (
      r.method() === 'POST' &&
      r.url().endsWith('/api/web/platform/pricing/base')
    )
      mutations++;
  });
  await page.locator('[name="baseAmount"]').fill('3000.93');
  await page
    .locator('[name="baseReason"]')
    .fill('UNSAVED EXPIRY PROOF — never submitted');
  const started = Date.now();
  const cookie = (
    await page.context().cookies(origin + '/api/web/session')
  ).find((c) => c.name === '__Secure-moulai-session');
  assert(
    cookie &&
      cookie.expires > started / 1000 &&
      cookie.expires <= started / 1000 + 301,
  );
  phase = 'waiting-for-real-expiration';
  await page.waitForURL(origin + '/access', { timeout: 370000 });
  const elapsed = (Date.now() - started) / 1000;
  assert.equal(await page.locator('[name="baseAmount"]').count(), 0);
  assert.equal(
    await request(page, '/api/web/organizations').then((r) => r.status),
    401,
  );
  assert.equal(mutations, 0);
  await page.screenshot({
    path: path.join(output, 'session-expired-access-fr.png'),
    fullPage: true,
  });
  phase = 'new-authentication-without-draft-replay';
  const reopened = await login(browser, 'platform-admin');
  await reopened.goto(origin + '/platform/pricing');
  assert.equal(await reopened.locator('[name="baseAmount"]').inputValue(), '');
  const after = checked(
    await request(reopened, '/api/web/platform/pricing/base'),
  );
  assert.deepEqual(after, before);
  const result = {
    status: 'PASS',
    real_clock: true,
    configured_lifetime_seconds: 300,
    observed_elapsed_seconds: elapsed,
    returned_to_access: true,
    protected_api_status_after_expiry: 401,
    automatic_refresh: false,
    automatic_mutations: mutations,
    unsubmitted_draft:
      'discarded on protected view unmount; not restored or replayed after login',
    base_and_revision_unchanged: true,
  };
  fs.writeFileSync(
    path.join(output, 'session-expiry.json'),
    JSON.stringify(result, null, 2),
  );
  console.log(
    JSON.stringify({
      status: 'PASS',
      elapsed_seconds: elapsed,
      unsaved_draft: 'not persisted or replayed',
    }),
  );
} catch (error) {
  fs.writeFileSync(
    path.join(output, 'session-expiry.json'),
    JSON.stringify({ status: 'FAIL', phase, type: error.name }, null, 2),
  );
  console.log(JSON.stringify({ status: 'FAIL', phase, type: error.name }));
  process.exitCode = 1;
} finally {
  await browser.close();
}

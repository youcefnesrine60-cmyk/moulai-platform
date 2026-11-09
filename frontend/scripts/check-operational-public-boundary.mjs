// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// MoulAI™ — verify public wiring and refusal without inventing a table, menu or paid account.
import { chromium } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
const root = path.resolve(import.meta.dirname, '../..'),
  output = path.join(root, 'artifacts/operational-integration-20261107');
const results = [];
let phase = 'start';
const browser = await chromium.launch({ headless: true });
try {
  const c = await browser.newContext({
    ignoreHTTPSErrors: true,
    locale: 'fr-FR',
  });
  await c.route('**/*', (r) =>
    new URL(r.request().url()).origin === 'https://127.0.0.1:5180'
      ? r.continue()
      : r.abort(),
  );
  const page = await c.newPage();
  phase = 'unregistered-table-menu';
  await page.goto('https://127.0.0.1:5180/menu#' + 'A'.repeat(43));
  await page.getByRole('alert').waitFor();
  assert.equal(await page.getByTestId('render-recovery').count(), 0);
  results.push({
    label: 'public-menu-route-mounted-with-unavailable-link',
    status: 'PASS',
  });
  phase = 'invalid-document';
  await page.goto('https://127.0.0.1:5180/verify-document#' + 'A'.repeat(43));
  await page.getByRole('heading', { name: /invalide/i }).waitFor();
  results.push({
    label: 'public-document-verification-routed',
    status: 'PASS',
  });
  phase = 'no-review-session';
  const session = await page.evaluate(async () => {
    const response = await fetch('/api/web/session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ actor: 'owner' }),
    });
    return {
      reviewIdentityStatus: response.status,
      actualSession: await fetch('/api/web/session').then((r) => r.json()),
    };
  });
  assert.equal(session.reviewIdentityStatus, 405);
  assert.equal(session.actualSession, null);
  results.push({
    label: 'fictional-profile-cannot-create-session',
    ...session,
  });
  fs.writeFileSync(
    path.join(output, 'public-boundary.json'),
    JSON.stringify(
      {
        status: 'PASS',
        positiveOrderFlow:
          'NOT TESTED — no catalogue or table data manufactured',
        results,
      },
      null,
      2,
    ),
  );
  console.log(JSON.stringify({ status: 'PASS', checks: results.length }));
} catch (error) {
  fs.writeFileSync(
    path.join(output, 'public-boundary.json'),
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

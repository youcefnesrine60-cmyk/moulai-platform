// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// MoulAI™ — hold a real browser session in RAM across a controlled service restart.
// The host is restarted by the owning operator; no credentials or storage state are exported.
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
const expected = JSON.parse(
  fs.readFileSync(path.join(output, 'lot1-membership.json'), 'utf8'),
).results.find(
  (r) => r.label === 'reference-created-via-ui-retained-after-reload',
).code;
const initialPid = JSON.parse(
  fs.readFileSync(path.join(directory, 'review.json'), 'utf8'),
).pid;
let phase = 'login';
const browser = await chromium.launch({ headless: true });
try {
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
  await page.locator('#username').fill('owner-a');
  await page.locator('#password').fill(accounts['owner-a'].password);
  await page.locator('#kc-login').click();
  await page.waitForURL(/\/workspace/);
  const before = await page.evaluate(async () => ({
    session: await fetch('/api/web/session').then((r) => r.json()),
    workspace: await fetch(
      '/api/web/organizations/8/restaurants/6/branches/4/dining/workspace',
    ).then((r) => r.json()),
  }));
  const reference = before.workspace.references.find(
    (r) => r.code === expected,
  );
  assert(reference);
  fs.writeFileSync(
    path.join(output, 'restart-test-ready.json'),
    JSON.stringify({ instance: id, initialPid, referenceId: reference.id }),
  );
  phase = 'wait-owned-restart';
  let restored = false;
  for (let attempt = 0; attempt < 120; attempt++) {
    await new Promise((resolve) => setTimeout(resolve, 1000));
    const status = JSON.parse(
      fs.readFileSync(path.join(directory, 'review.json'), 'utf8'),
    );
    if (status.pid === initialPid) continue;
    try {
      const response = await context.request.get(
        'https://127.0.0.1:5180/api/web/session',
        { timeout: 2000 },
      );
      const session = await response.json();
      if (
        response.status() === 200 &&
        session?.subject === before.session.subject
      ) {
        restored = true;
        break;
      }
    } catch {
      /* A stopped local host is the expected intermediate state, not a business retry. */
    }
  }
  assert(
    restored,
    'same provider/browser session must survive restart without another login',
  );
  phase = 'persisted-read';
  await page.goto(
    'https://127.0.0.1:5180/workspace/organizations/8/restaurants/6/tables?branch=4',
  );
  await page
    .getByText('Habilitations contrôlées en base', { exact: false })
    .first()
    .waitFor();
  const after = await page.evaluate(async () => ({
    session: await fetch('/api/web/session').then((r) => r.json()),
    workspace: await fetch(
      '/api/web/organizations/8/restaurants/6/branches/4/dining/workspace',
    ).then((r) => r.json()),
  }));
  assert.equal(after.session.subject, before.session.subject);
  assert.equal(
    after.workspace.references.find((r) => r.code === expected)?.id,
    reference.id,
  );
  fs.writeFileSync(
    path.join(output, 'lot1-restart.json'),
    JSON.stringify(
      {
        status: 'PASS',
        sameAuthenticatedSubject: true,
        noNewLogin: true,
        referenceId: reference.id,
        referenceCode: expected,
        initialPid,
        finalPid: JSON.parse(
          fs.readFileSync(path.join(directory, 'review.json'), 'utf8'),
        ).pid,
      },
      null,
      2,
    ),
  );
  console.log(
    JSON.stringify({ status: 'PASS', noNewLogin: true, dataRetained: true }),
  );
} catch (error) {
  fs.writeFileSync(
    path.join(output, 'lot1-restart.json'),
    JSON.stringify({ status: 'FAIL', phase, type: error.name }, null, 2),
  );
  console.log(JSON.stringify({ status: 'FAIL', phase, type: error.name }));
  process.exitCode = 1;
} finally {
  await browser.close();
}

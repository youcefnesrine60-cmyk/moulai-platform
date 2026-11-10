// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Visible disposable Chromium window for an unedited Windows capture of the real tab favicon.
import { chromium } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import { root, origin, newContext } from './operationalHarness.mjs';

const output = path.join(
  root,
  'artifacts/operational-followup-20261109/favicon',
);
fs.mkdirSync(output, { recursive: true });
const stop = path.join(output, 'close-window');
assert(
  !fs.existsSync(stop),
  'This visible proof requires a new explicit window run.',
);
const browser = await chromium.launch({
  channel: 'chrome',
  headless: false,
  args: ['--window-size=1280,900'],
});
try {
  const page = await (await newContext(browser)).newPage();
  await page.goto(origin + '/access');
  await page
    .getByRole('button', { name: 'Se connecter', exact: true })
    .waitFor();
  const icons = await page.locator('link[rel="icon"]').evaluateAll((elements) =>
    elements.map((e) => ({
      href: e.getAttribute('href'),
      type: e.getAttribute('type'),
      sizes: e.getAttribute('sizes'),
    })),
  );
  assert.deepEqual(
    icons.map((i) => i.href),
    ['/brand/GateWay.png', '/brand/GateWay.ico'],
  );
  const resources = [];
  for (const name of ['GateWay.ico', 'GateWay.png']) {
    const response = await page.request.get(origin + '/brand/' + name);
    assert.equal(response.status(), 200);
    const actual = await response.body(),
      source = fs.readFileSync(path.join(root, 'assets/originals', name));
    assert(actual.equals(source));
    resources.push({
      name,
      status: 200,
      sha256: crypto.createHash('sha256').update(actual).digest('hex'),
      binaryIdentical: true,
    });
  }
  await page.reload({ waitUntil: 'networkidle' });
  const fresh = await (await newContext(browser)).newPage();
  await fresh.goto(origin + '/access');
  await fresh
    .getByRole('button', { name: 'Se connecter', exact: true })
    .waitFor();
  await fresh.bringToFront();
  fs.writeFileSync(
    path.join(output, 'resource-proof.json'),
    JSON.stringify(
      {
        status: 'PASS',
        icons,
        resources,
        hardReload: true,
        freshContext: true,
        tabScreenshot:
          'Pending Windows capture; not claimed by this HTTP check',
      },
      null,
      2,
    ),
  );
  console.log(
    JSON.stringify({ status: 'READY_FOR_TAB_CAPTURE', externalCalls: 0 }),
  );
  while (!fs.existsSync(stop))
    await new Promise((resolve) => setTimeout(resolve, 1000));
} finally {
  await browser.close();
}

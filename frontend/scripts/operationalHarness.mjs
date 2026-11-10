// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Real local Keycloak browser harness; no stored tokens, tracing or fictional authentication.
import { chromium } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
// Node APIRequestContext and Chromium both verify TLS; the former needs explicit OS trust.
assert.equal(
  process.env.NODE_USE_SYSTEM_CA,
  '1',
  'Start Node with NODE_USE_SYSTEM_CA=1; never bypass TLS errors.',
);
export const root = path.resolve(import.meta.dirname, '../..');
const id = '3fb5f85a6cc94868acaf7d95b3777a16';
const directory = path.join(root, 'artifacts/operational-local', id);
assert.equal(
  fs.readFileSync(path.join(directory, 'instance-marker'), 'ascii'),
  id,
);
export const accounts = JSON.parse(
  fs.readFileSync(
    path.join(directory, 'private/acceptance-accounts.json'),
    'utf8',
  ),
);
export const output = path.join(
  root,
  'artifacts/operational-milestone-20261108',
);
export const origin = 'https://127.0.0.1:5180';
export const route = '/api/web/organizations/8/restaurants/6/branches/4/dining';
export const screen =
  '/workspace/organizations/8/restaurants/6/tables?branch=4';
export async function launch() {
  return chromium.launch({ headless: true });
}
export async function newContext(browser, viewport, density = 1) {
  const context = await browser.newContext({
    ignoreHTTPSErrors: false,
    locale: 'fr-FR',
    ...(viewport ? { viewport, deviceScaleFactor: density } : {}),
  });
  await context.route('**/*', (r) =>
    [origin, 'https://127.0.0.1:8444'].includes(
      new URL(r.request().url()).origin,
    )
      ? r.continue()
      : r.abort(),
  );
  return context;
}
export async function login(browser, username) {
  const context = await newContext(browser),
    page = await context.newPage();
  await page.goto(origin + '/access');
  await page.getByRole('button', { name: 'Se connecter', exact: true }).click();
  await page.locator('#username').fill(username);
  await page.locator('#password').fill(accounts[username].password);
  await page.locator('#kc-login').click();
  await page.waitForURL(/https:\/\/127\.0\.0\.1:5180\/(workspace|platform)/);
  return page;
}
export async function request(page, path, body, headers = {}) {
  return page.evaluate(
    async ({ path, body, headers }) => {
      const r = await fetch(path, {
        method: body === undefined ? 'GET' : 'POST',
        headers:
          body === undefined
            ? headers
            : { 'Content-Type': 'application/json', ...headers },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      return { status: r.status, body: await r.json() };
    },
    { path, body, headers },
  );
}
export function checked(result, status = 200) {
  if (result.status !== status)
    throw Object.assign(new Error('Unexpected local status'), {
      safeStatus: result.status,
      safeCode:
        typeof result.body?.detail?.code === 'string'
          ? result.body.detail.code
          : undefined,
    });
  return result.body;
}
export async function command(page, body) {
  return checked(await request(page, route + '/commands', body));
}
export async function snapshot(page) {
  return checked(await request(page, route + '/workspace'));
}
export async function form(page, operation) {
  const f = page.locator(`form[data-operation="${operation}"]`);
  await f.waitFor({ state: 'attached' });
  const parent = f.locator('..');
  if ((await parent.getAttribute('open')) === null)
    await parent.locator(':scope > summary').click();
  return f;
}
export async function save(page, f) {
  const result = page.waitForResponse(
    (r) => r.request().method() === 'POST' && r.url().includes(route),
  );
  await f.locator('button[type="submit"]').click();
  const response = await result;
  assert.equal(response.status(), 200, await response.text());
  await f.locator('fieldset').first().waitFor({ state: 'visible' });
  await page.waitForFunction(
    () =>
      !Array.from(document.querySelectorAll('form fieldset')).some(
        (x) => x.disabled,
      ),
  );
  return response.json();
}
export function wall(milliseconds) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Africa/Algiers',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(new Date(milliseconds));
  const get = (k) => parts.find((p) => p.type === k).value;
  return `${get('year')}-${get('month')}-${get('day')}T${get('hour')}:${get('minute')}`;
}

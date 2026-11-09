// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// MoulAI™ — explicit HTTP simulation for client lifecycle failures; no business writes.
import { installManualThemeFixture } from './manualThemeFixture';
import { test, expect, type Page } from '@playwright/test';
import { diningPresentationFixture } from '../fixtures/diningPresentation';
import { d1Fr } from '../../src/shared/i18n/d1.fr';

async function setup(page: Page) {
  const fixture = diningPresentationFixture('fr');
  let actor = 'owner';
  let capabilities = fixture.workspace.capabilities;
  let workspaceStatus = 200;
  let commandStatus = 409;
  let loginStatus = 200;
  let loginCalls = 0;
  let commandCalls = 0;
  let gate: Promise<void> = Promise.resolve();
  await page.route('**/*', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    expect(url.origin).toBe('http://127.0.0.1:5574');
    if (!url.pathname.startsWith('/local-d1/')) return route.continue();
    if (url.pathname === '/local-d1/session') {
      if (request.method() === 'POST') {
        loginCalls++;
        await gate;
        if (loginStatus !== 200)
          return route.fulfill({
            status: loginStatus,
            json: { detail: 'denied' },
          });
        actor = request.postDataJSON().actor;
        capabilities =
          actor === 'cleaner'
            ? ['read', 'clean']
            : fixture.workspace.capabilities;
      }
      return route.fulfill({ json: { ...fixture.session, actor } });
    }
    if (url.pathname.endsWith('/commands')) {
      commandCalls++;
      await gate;
      return route.fulfill({
        status: commandStatus,
        json:
          commandStatus === 200
            ? { saved: true }
            : { detail: { code: 'dining_fixture_refused' } },
      });
    }
    if (url.pathname.endsWith('/workspace'))
      return route.fulfill({
        status: workspaceStatus,
        json:
          workspaceStatus === 200
            ? { ...fixture.workspace, capabilities }
            : { detail: 'unavailable' },
      });
    if (url.pathname.endsWith('/planning'))
      return route.fulfill({ json: fixture.planning });
    if (url.pathname.endsWith('/instant'))
      return route.fulfill({
        json: { instant: '2026-11-03T00:00:00Z', timezone: 'Africa/Algiers' },
      });
    throw new Error('Unexpected local request');
  });
  await page.addInitScript(() => {
    localStorage.setItem('moulai.locale', 'fr');
    localStorage.setItem('moulai.theme', 'dark');
  });
  await page.goto('/dining-local?branch=300');
  await expect(page.getByTestId('operational-board')).toBeVisible();
  return {
    caps: (value: string[]) => {
      capabilities = value;
    },
    status: (value: number) => {
      workspaceStatus = value;
    },
    loginStatus: (value: number) => {
      loginStatus = value;
    },
    commandStatus: (value: number) => {
      commandStatus = value;
    },
    gate: (value: Promise<void>) => {
      gate = value;
    },
    calls: () => ({ loginCalls, commandCalls }),
  };
}
test('selected profile is pending; switching clears data and admits only server capabilities once', async ({
  page,
}) => {
  const control = await setup(page);
  await page.getByTestId('session-settings').locator('summary').click();
  await page.locator('[name="actor"]').selectOption('cleaner');
  await expect(page.getByTestId('active-session')).toContainText(
    d1Fr['d1.actor_owner'],
  );
  await expect(page.getByTestId('pending-profile')).toBeVisible();
  let release!: () => void;
  control.gate(
    new Promise((resolve) => {
      release = resolve;
    }),
  );
  await page
    .getByRole('button', { name: d1Fr['d1.signIn'], exact: true })
    .click();
  await expect(page.getByTestId('operational-board')).toHaveCount(0);
  await expect(
    page.getByRole('button', { name: d1Fr['d1.signIn'], exact: true }),
  ).toBeDisabled();
  release();
  await expect(page.getByTestId('active-session')).toContainText(
    d1Fr['d1.actor_cleaner'],
  );
  await expect(page.getByTestId('operational-board')).toBeVisible();
  await expect(
    page.getByRole('button', { name: d1Fr['d1.section_finance'], exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole('button', {
      name: d1Fr['d1.section_requests'],
      exact: true,
    }),
  ).toHaveCount(0);
  expect(control.calls().loginCalls).toBe(1);
});
test('revocation hides finance; rejected access clears previous data rather than rendering an empty financial table', async ({
  page,
}) => {
  const control = await setup(page);
  await page
    .getByRole('button', { name: d1Fr['d1.section_finance'], exact: true })
    .click();
  control.caps(['read', 'clean']);
  await page
    .getByRole('button', { name: d1Fr['d1.reload'], exact: true })
    .click();
  await expect(
    page.getByRole('button', { name: d1Fr['d1.section_finance'], exact: true }),
  ).toHaveCount(0);
  await expect(page.getByTestId('operational-board')).toBeVisible();
  control.status(403);
  await page
    .getByRole('button', { name: d1Fr['d1.reload'], exact: true })
    .click();
  await expect(page.getByRole('alert')).toContainText(
    d1Fr['d1.permissionRefused'],
  );
  await expect(page.getByTestId('operational-board')).toHaveCount(0);
});
test('failed profile opening cannot display old authority', async ({
  page,
}) => {
  const control = await setup(page);
  await page.getByTestId('session-settings').locator('summary').click();
  await page.locator('[name="actor"]').selectOption('cleaner');
  control.loginStatus(503);
  await page
    .getByRole('button', { name: d1Fr['d1.signIn'], exact: true })
    .click();
  await expect(page.getByTestId('active-session')).toContainText(
    d1Fr['d1.noSession'],
  );
  await expect(page.getByTestId('operational-board')).toHaveCount(0);
  await expect(page.getByRole('alert')).toBeVisible();
});
test('recoverable form error retains input; a committed write with failed reload is never submitted twice automatically', async ({
  page,
}) => {
  const control = await setup(page);
  await page
    .getByRole('button', {
      name: d1Fr['d1.section_configuration'],
      exact: true,
    })
    .click();
  const form = page.locator('form[data-operation="reference"]');
  await form.locator('..').locator('summary').click();
  await form.locator('[name="kind"]').selectOption('view');
  for (const name of ['code', 'fr', 'en', 'ar'])
    await form.locator(`[name="${name}"]`).fill('Fictional input retained');
  await form
    .getByRole('button', { name: d1Fr['d1.save'], exact: true })
    .click();
  await expect(form.getByRole('alert')).toContainText(d1Fr['d1.formError']);
  await expect(form.locator('[name="code"]')).toHaveValue(
    'Fictional input retained',
  );
  await expect(
    page.getByText(d1Fr['d1.persistedReloaded'], { exact: true }),
  ).toHaveCount(0);
  control.commandStatus(200);
  control.status(503);
  await form
    .getByRole('button', { name: d1Fr['d1.save'], exact: true })
    .click();
  await expect(
    page.getByText(d1Fr['d1.committedStale'], { exact: true }),
  ).toBeVisible();
  expect(control.calls().commandCalls).toBe(2);
  await expect(
    page.getByText(d1Fr['d1.persistedReloaded'], { exact: true }),
  ).toHaveCount(0);
});
test('both authorized loopback entry points respond in the browser', async ({
  page,
}) => {
  const urls = [
    'http://127.0.0.1:5173/access',
    'http://127.0.0.1:5574/dining-local',
  ];
  await page.route('**/*', (route) => {
    const url = new URL(route.request().url());
    expect(url.hostname).toBe('127.0.0.1');
    expect(['5173', '5574']).toContain(url.port);
    return route.continue();
  });
  for (const url of urls) {
    const response = await page.goto(url);
    expect(response?.status()).toBe(200);
    await expect(page.locator('h1')).toBeVisible();
    await page.screenshot({
      path: `../artifacts/dining-workspace-20261104/access-${new URL(url).port}.png`,
      fullPage: true,
    });
  }
});

if (process.env.DINING_REAL_CAPTURE === '1')
  test('real persisted observations render all states in the verified Light and Dark themes', async ({
    page,
  }) => {
    const writes: string[] = [];
    await page.route('**/*', (route) => {
      const request = route.request();
      const url = new URL(request.url());
      expect(url.origin).toBe('http://127.0.0.1:5574');
      if (
        !['GET', 'HEAD'].includes(request.method()) &&
        url.pathname !== '/local-d1/session'
      ) {
        writes.push(url.pathname);
        return route.abort();
      }
      return route.continue();
    });
    await page.addInitScript(() => {
      localStorage.setItem('moulai.locale', 'fr');
      localStorage.setItem('moulai.theme', 'light');
    });
    await page.goto('/dining-local?branch=7000300');
    const settings = page.getByTestId('session-settings');
    await expect(settings).toBeVisible();
    if ((await settings.getAttribute('open')) === null)
      await settings.locator('summary').click();
    await page.locator('[name="actor"]').selectOption('owner');
    await page
      .getByRole('button', { name: d1Fr['d1.signIn'], exact: true })
      .click();
    await expect(page.getByTestId('active-session')).toContainText(
      'Bistro MoulAI',
    );
    await expect(page.getByTestId('physical-count-all')).toHaveAttribute(
      'data-count',
      '8',
    );
    for (const state of [
      'available',
      'occupied',
      'dirty',
      'maintenance',
      'out_of_service',
    ])
      await expect(
        page
          .locator(`[data-testid="physical-badge"][data-state="${state}"]`)
          .first(),
      ).toBeVisible();
    for (const theme of ['light', 'dark']) {
      if (theme === 'dark') {
        await page.getByRole('combobox', { name: 'Apparence' }).click();
        await page.getByRole('option', { name: 'Sombre', exact: true }).click();
      }
      await expect(page.locator('html')).toHaveAttribute('data-theme', theme);
      await page.screenshot({
        path: `../artifacts/dining-workspace-20261104/live-local-${theme}-1440.png`,
        fullPage: true,
      });
      if (theme === 'dark')
        await page.screenshot({
          path: '../artifacts/dining-workspace-20261104/live-dark-viewport.png',
        });
    }
    expect(writes).toEqual([]);
  });

// Visual fixtures request a manual choice; opening policy is checked independently.
test.beforeEach(async ({ page }) => installManualThemeFixture(page));

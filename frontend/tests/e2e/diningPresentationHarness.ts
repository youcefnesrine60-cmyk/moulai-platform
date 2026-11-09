// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { installManualThemeFixture } from './manualThemeFixture';
import { expect, type Page } from '@playwright/test';
import { diningPresentationFixture } from '../fixtures/diningPresentation';
import type { Planning } from '../../src/shared/dining/local/client';

/** Test-only simulated reads. Every business write and external request is refused. */
export async function openPresentationCase(
  page: Page,
  fixture: ReturnType<typeof diningPresentationFixture>,
  planningFor?: (day: string) => Promise<Planning>,
  appearance: {
    locale: 'fr' | 'en' | 'ar';
    theme: 'light' | 'dark' | 'opening';
  } = { locale: 'fr', theme: 'light' },
) {
  await installManualThemeFixture(page);
  const writes: string[] = [];
  await page.route('**/*', async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    expect(url.hostname).toBe('127.0.0.1');
    expect(url.port).toBe('5574');
    if (!url.pathname.startsWith('/local-d1/')) return route.continue();
    if (req.method() !== 'GET') {
      writes.push(url.pathname);
      await route.abort();
      throw new Error('Business writes forbidden in presentation test');
    }
    let body: unknown;
    if (url.pathname === '/local-d1/session') body = fixture.session;
    else if (url.pathname === '/local-d1/dining/employment/invitations')
      body = [];
    else if (url.pathname.endsWith('/workspace')) body = fixture.workspace;
    else if (url.pathname.endsWith('/instant'))
      body = {
        instant: new Date(
          url.searchParams.get('day') +
            'T' +
            url.searchParams.get('wall_time') +
            '+01:00',
        ).toISOString(),
        timezone: 'Africa/Algiers',
      };
    else if (url.pathname.endsWith('/planning')) {
      const date = new Date(
        Date.parse(url.searchParams.get('starts_at') ?? '') + 3600000,
      )
        .toISOString()
        .slice(0, 10);
      body = planningFor ? await planningFor(date) : fixture.planning;
    } else throw new Error('Unexpected presentation request');
    return route.fulfill({ json: body });
  });
  page.on('pageerror', (error) => {
    throw error;
  });
  await page.addInitScript(({ locale, theme }) => {
    localStorage.setItem('moulai.locale', locale);
    if (theme === 'opening') localStorage.removeItem('moulai.theme');
    else localStorage.setItem('moulai.theme', theme);
  }, appearance);
  await page.goto('/dining-local?branch=300');
  await expect(page.getByTestId('table-card-1')).toBeVisible();
  return writes;
}

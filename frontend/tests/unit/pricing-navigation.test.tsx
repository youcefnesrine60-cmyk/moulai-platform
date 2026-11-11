// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Mocked editor transport only: these checks do not change real tariffs or grant server authority.
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Link, Outlet, RouterProvider, createMemoryRouter } from 'react-router';
import { describe, expect, it, vi } from 'vitest';
import { PricingCampaignsPage } from '../../src/features/integration/PricingCampaignsPage';
import { UnsavedChangesProvider } from '../../src/shared/ui/UnsavedChanges';
import i18n from '../../src/shared/i18n';
import { webRequest } from '../../src/shared/access/operational';

vi.mock('../../src/app/access', () => ({
  useSession: () => ({ data: null }),
  identityKey: () => ['editor-unit-only'],
}));
vi.mock('../../src/shared/access/operational', () => ({ webRequest: vi.fn() }));

async function start() {
  await i18n.changeLanguage('fr');
  vi.mocked(webRequest).mockImplementation(async (path, _signal, method) => {
    if (method === 'POST')
      throw new Error('recoverable unit transport failure');
    if (path.endsWith('/campaigns')) return [];
    if (path.endsWith('/base-contexts'))
      return [{ country_code: 'DZ', currency: 'DZD' }];
    if (path.includes('/base?'))
      return {
        amount: '3000.00',
        country_code: 'DZ',
        currency: 'DZD',
        revision: 'UNIT-ONLY',
        sha256: 'a'.repeat(64),
      };
    if (path.endsWith('/reminders'))
      return {
        days: [14, 7, 1, 0],
        sha256: 'b'.repeat(64),
        responsible_configured: false,
        applies_to: 'new_schedules_only',
        delivery_active: false,
      };
    throw new Error('Unexpected unit read');
  });
  const router = createMemoryRouter([
    {
      element: (
        <QueryClientProvider
          client={
            new QueryClient({ defaultOptions: { queries: { retry: false } } })
          }
        >
          <UnsavedChangesProvider>
            <Link to="/next">Next view</Link>
            <Outlet />
          </UnsavedChangesProvider>
        </QueryClientProvider>
      ),
      children: [
        { path: '/', element: <PricingCampaignsPage /> },
        { path: '/next', element: <p>Next editor view</p> },
      ],
    },
  ]);
  render(<RouterProvider router={router} />);
  await screen.findByLabelText(i18n.t('pricing.newBase'));
  return userEvent.setup();
}

describe('legacy pricing editor navigation protection', () => {
  it('keeps base inputs after a recoverable error and prevents a blind navigation/replay', async () => {
    const user = await start();
    const base = screen.getByRole('form', { name: i18n.t('pricing.base') });
    await user.type(
      within(base).getByLabelText(i18n.t('pricing.newBase')),
      '3500',
    );
    await user.type(
      within(base).getByLabelText(i18n.t('pricing.reason')),
      'UNSAVED UNIT ONLY',
    );
    await user.click(within(base).getByRole('button'));
    await screen.findByRole('alert');
    expect(within(base).getByLabelText(i18n.t('pricing.newBase'))).toHaveValue(
      '3500',
    );
    await user.click(screen.getByRole('link', { name: 'Next view' }));
    await user.click(
      screen.getByRole('button', { name: i18n.t('quality.stay') }),
    );
    expect(within(base).getByLabelText(i18n.t('pricing.reason'))).toHaveValue(
      'UNSAVED UNIT ONLY',
    );
    expect(
      vi.mocked(webRequest).mock.calls.filter((call) => call[2] === 'POST'),
    ).toHaveLength(1);
    await user.click(screen.getByRole('link', { name: 'Next view' }));
    await user.click(
      screen.getByRole('button', { name: i18n.t('quality.leave') }),
    );
    expect(await screen.findByText('Next editor view')).toBeVisible();
    expect(
      vi.mocked(webRequest).mock.calls.filter((call) => call[2] === 'POST'),
    ).toHaveLength(1);
  });
  it('protects an unfinished campaign independently of base price inputs', async () => {
    const user = await start();
    await user.type(
      screen.getByLabelText(i18n.t('pricing.name')),
      'UNIT CAMPAIGN — NOT PERSISTED',
    );
    await user.click(screen.getByRole('link', { name: 'Next view' }));
    await user.click(
      screen.getByRole('button', { name: i18n.t('quality.stay') }),
    );
    expect(screen.getByLabelText(i18n.t('pricing.name'))).toHaveValue(
      'UNIT CAMPAIGN — NOT PERSISTED',
    );
    expect(
      vi.mocked(webRequest).mock.calls.filter((call) => call[2] === 'POST'),
    ).toHaveLength(0);
  });
});

// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Local UI fixtures only; server billing-country authority and pricing are covered independently.
import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Link, Outlet, createMemoryRouter, RouterProvider } from 'react-router';
import { describe, expect, it, vi } from 'vitest';
import { OwnerOfferPage } from '../../src/features/integration/OwnerOfferPage';
import { UnsavedChangesProvider } from '../../src/shared/ui/UnsavedChanges';
import { webRequest } from '../../src/shared/access/operational';
import i18n from '../../src/shared/i18n';

vi.mock('../../src/features/management/scope', () => ({
  useSelection: () => ({ organizationId: 1, restaurantId: 2 }),
}));
vi.mock('../../src/app/access', () => ({
  useSession: () => ({ data: null }),
  identityKey: () => ['offer-test'],
}));
vi.mock('../../src/features/integration/EnrollmentPage', () => ({
  BillingCountryPanel: () => null,
}));
vi.mock('../../src/features/integration/SaasPayments', () => ({
  SaasPayments: () => null,
}));
vi.mock('../../src/shared/access/operational', () => ({ webRequest: vi.fn() }));

async function mount() {
  await i18n.changeLanguage('fr');
  vi.mocked(webRequest).mockResolvedValue({
    base_reference: '3000',
    currency: 'DZD',
    country_code: 'DZ',
    currencies: ['DZD'],
    plans: [{ id: 41, code: 'basic', name: 'TEST PLAN' }],
    blockers: [],
    binding_quote: false,
    registration_connected: false,
  });
  const router = createMemoryRouter([
    {
      element: (
        <UnsavedChangesProvider>
          <Outlet />
        </UnsavedChangesProvider>
      ),
      children: [
        {
          path: '/',
          element: (
            <>
              <OwnerOfferPage />
              <Link to="/next">Next</Link>
            </>
          ),
        },
        { path: '/next', element: <p>Next view</p> },
        { path: '/access', element: <p>Expired session</p> },
      ],
    },
  ]);
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  await screen.findByRole('combobox', { name: i18n.t('offer.plan') });
  return { router, user: userEvent.setup() };
}

describe('owner simulation choices survive a cancelled navigation', () => {
  it('keeps plan and cycle without posting a simulation or checkout', async () => {
    const { user } = await mount();
    await user.selectOptions(
      screen.getByRole('combobox', { name: i18n.t('offer.plan') }),
      '41',
    );
    await user.selectOptions(
      screen.getByRole('combobox', { name: i18n.t('offer.cycle') }),
      'yearly',
    );
    await user.click(screen.getByRole('link', { name: 'Next' }));
    await user.click(
      screen.getByRole('button', { name: i18n.t('quality.stay') }),
    );
    expect(
      screen.getByRole('combobox', { name: i18n.t('offer.plan') }),
    ).toHaveValue('41');
    expect(
      screen.getByRole('combobox', { name: i18n.t('offer.cycle') }),
    ).toHaveValue('yearly');
    expect(
      vi.mocked(webRequest).mock.calls.every((call) => call[2] === undefined),
    ).toBe(true);
    await user.click(screen.getByRole('link', { name: 'Next' }));
    await user.click(
      screen.getByRole('button', { name: i18n.t('quality.leave') }),
    );
    expect(await screen.findByText('Next view')).toBeVisible();
  });
  it('never blocks session expiry because a simulation choice is unsaved', async () => {
    const { user, router } = await mount();
    await user.selectOptions(
      screen.getByRole('combobox', { name: i18n.t('offer.plan') }),
      '41',
    );
    await act(async () => {
      window.dispatchEvent(new Event('moulai-session-expired'));
      await router.navigate('/access');
    });
    expect(await screen.findByText('Expired session')).toBeVisible();
    expect(screen.queryByRole('dialog')).toBeNull();
  });
});

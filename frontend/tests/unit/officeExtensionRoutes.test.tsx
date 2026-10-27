import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Providers, createQueryClient } from '../../src/app/Providers';
import { routes } from '../../src/app/router';
import { createSyntheticAdapter } from '../../src/review/syntheticAdapter';
import type {
  AccessAdapter,
  ReviewProfile,
} from '../../src/shared/access/contracts';
import { AccessError } from '../../src/shared/access/contracts';
import i18n from '../../src/shared/i18n';

const scope = { organizationId: 9101, restaurantId: 9201 };
const base = '/workspace/organizations/9101/restaurants/9201';
async function mount(
  path: string,
  profile: ReviewProfile = 'owner',
  custom?: AccessAdapter,
) {
  const adapter = custom ?? createSyntheticAdapter(0);
  await adapter.openReview(profile);
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(
    <Providers adapter={adapter} client={createQueryClient()}>
      <RouterProvider router={router} />
    </Providers>,
  );
  return { adapter, router };
}
beforeEach(async () => {
  await i18n.changeLanguage('fr');
  window.moulaiTheme.choose('light');
});

describe('extended local office workflows', () => {
  it('renders accessible distributions alongside explicit unavailable financial metrics', async () => {
    await mount(`${base}/reports`, 'manager');
    const chart = await screen.findByRole('figure', {
      name: i18n.t('office.orderChart'),
    });
    expect(within(chart).getAllByRole('listitem')).toHaveLength(8);
    expect(
      await screen.findByRole('figure', {
        name: i18n.t('office.categoryChart'),
      }),
    ).toBeVisible();
    expect(screen.getAllByText(i18n.t('office.unavailable'))).toHaveLength(2);
  });
  it('previews yearly terms and BaridiMob instructions without creating a payment', async () => {
    const user = userEvent.setup();
    const { adapter, router } = await mount(`${base}/billing`);
    const before = await adapter.payments(scope, new AbortController().signal);
    const form = within(
      await screen.findByRole('form', { name: i18n.t('office.offerPreview') }),
    );
    await user.selectOptions(
      form.getByRole('combobox', { name: i18n.t('office.cycle') }),
      'yearly',
    );
    await user.selectOptions(
      form.getByRole('combobox', { name: i18n.t('office.method') }),
      'baridimob',
    );
    expect(screen.getByText('SYNTHETIC-RIP-NOT-PAYABLE')).toBeVisible();
    expect(screen.queryByText('SYNTHETIC-CCP-NOT-PAYABLE')).toBeNull();
    await user.click(
      form.getByRole('button', { name: i18n.t('office.simulateCheckout') }),
    );
    expect(form.getByRole('status')).toHaveTextContent(
      i18n.t('office.checkoutPreview'),
    );
    await act(async () => {
      await i18n.changeLanguage('ar');
      window.moulaiTheme.choose('dark');
    });
    expect(
      form.getByRole('combobox', { name: i18n.t('office.cycle') }),
    ).toHaveValue('yearly');
    expect(
      form.getByRole('combobox', { name: i18n.t('office.method') }),
    ).toHaveValue('baridimob');
    expect(
      screen.getByRole('button', { name: i18n.t('office.checkout') }),
    ).toBeDisabled();
    expect(await adapter.payments(scope, new AbortController().signal)).toEqual(
      before,
    );
    expect(router.state.location.pathname).toBe(`${base}/billing`);
    await user.selectOptions(
      form.getByRole('combobox', { name: i18n.t('office.cycle') }),
      'monthly',
    );
    expect(form.queryByRole('status')).toBeNull();
  });
  it('shows missing subscription/instructions without substituting payment details', async () => {
    const adapter = createSyntheticAdapter(0);
    vi.spyOn(adapter, 'billingWorkspace').mockResolvedValue({
      restaurantId: 9201,
      subscription: null,
      offers: [],
      instructions: [],
    });
    await mount(`${base}/billing`, 'owner', adapter);
    expect(
      await screen.findByText(i18n.t('office.noSubscription')),
    ).toBeVisible();
    expect(
      screen.getByText(i18n.t('office.instructionsUnavailable')),
    ).toBeVisible();
    expect(
      screen.getByRole('button', { name: i18n.t('office.simulateCheckout') }),
    ).toBeDisabled();
  });
  it('shows a bounded new-read error instead of invented subscription success', async () => {
    const adapter = createSyntheticAdapter(0);
    vi.spyOn(adapter, 'billingWorkspace').mockRejectedValue(
      new AccessError('temporary'),
    );
    await mount(`${base}/billing`, 'owner', adapter);
    expect(await screen.findByRole('alert')).toBeVisible();
    expect(screen.queryByText(i18n.t('office.checkoutPreview'))).toBeNull();
  });
  it('requires independent test evidence for admin approval and changes no source record', async () => {
    const user = userEvent.setup();
    const { adapter } = await mount('/platform/receipts', 'admin');
    await screen.findByRole('heading', { name: 'PAYMENT-REVIEW-9201' });
    const before = await adapter.platformRecords(
      'receipts',
      new AbortController().signal,
    );
    await user.click(
      screen.getByText(i18n.t('office.details'), { selector: 'summary' }),
    );
    const form = within(
      screen.getByRole('form', { name: i18n.t('office.verification') }),
    );
    await user.click(
      form.getByRole('button', { name: i18n.t('office.simulateReview') }),
    );
    expect(form.getByRole('alert')).toHaveTextContent(
      i18n.t('office.simulationError'),
    );
    await user.click(
      form.getByRole('checkbox', { name: i18n.t('office.fundsHypothesis') }),
    );
    await user.type(
      form.getByRole('textbox', { name: i18n.t('office.bankReference') }),
      'BILLING-REVIEW-9201',
    );
    await user.type(
      form.getByRole('textbox', { name: i18n.t('office.receivedAmount') }),
      '2500.00',
    );
    await user.selectOptions(
      form.getByRole('combobox', { name: i18n.t('office.currency') }),
      'DZD',
    );
    await user.type(
      form.getByRole('textbox', { name: i18n.t('office.note') }),
      'Synthetic verification only',
    );
    await user.click(
      form.getByRole('button', { name: i18n.t('office.simulateReview') }),
    );
    expect(form.getByRole('status')).toHaveTextContent(
      i18n.t('office.simulationApproved'),
    );
    expect(
      screen.getByRole('button', {
        name: i18n.t('office.approve'),
      }),
    ).toBeDisabled();
    expect(
      await adapter.platformRecords('receipts', new AbortController().signal),
    ).toEqual(before);
    await user.selectOptions(
      form.getByRole('combobox', { name: i18n.t('office.decision') }),
      'reject',
    );
    expect(form.queryByRole('status')).toBeNull();
    await user.click(
      form.getByRole('button', { name: i18n.t('office.simulateReview') }),
    );
    expect(form.getByRole('status')).toHaveTextContent(
      i18n.t('office.simulationRejected'),
    );
    await user.click(
      form.getByRole('button', { name: i18n.t('office.resetSimulation') }),
    );
    expect(form.queryByRole('status')).toBeNull();
    expect(form.getByRole('checkbox')).not.toBeChecked();
  });
  it('does not show simulations to a platform admin lacking payment-review permission', async () => {
    const adapter = createSyntheticAdapter(0);
    const original = adapter.getSession;
    const limited: AccessAdapter = {
      ...adapter,
      getSession: async (signal) => {
        const session = await original(signal);
        return session
          ? { ...session, platformPermissions: ['admins.manage'] }
          : null;
      },
    };
    await mount('/platform/receipts', 'admin', limited);
    expect(await screen.findByRole('alert')).toBeVisible();
    expect(
      screen.queryByRole('form', { name: i18n.t('office.verification') }),
    ).toBeNull();
  });
  it('discards an unsaved subscription preview when selecting another restaurant', async () => {
    const user = userEvent.setup();
    const { router } = await mount(`${base}/billing`);
    await screen.findByRole('form', { name: i18n.t('office.offerPreview') });
    await user.click(
      screen.getByRole('button', { name: i18n.t('office.simulateCheckout') }),
    );
    expect(screen.getByRole('status')).toHaveTextContent(
      i18n.t('office.checkoutPreview'),
    );
    await act(async () => {
      await router.navigate(
        '/workspace/organizations/9102/restaurants/9203/billing',
      );
    });
    await screen.findByRole('heading', { name: /Paiement.*920301/ });
    expect(screen.queryByText(i18n.t('office.checkoutPreview'))).toBeNull();
    expect(
      await screen.findByText(i18n.t('office.expired'), { exact: true }),
    ).toBeVisible();
  });
});

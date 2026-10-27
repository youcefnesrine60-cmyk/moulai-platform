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
import { orderStatuses } from '../../src/shared/business/contracts';
import i18n from '../../src/shared/i18n';
import { officeFr } from '../../src/shared/i18n/office.fr';
import { officeEn } from '../../src/shared/i18n/office.en';
import { officeAr } from '../../src/shared/i18n/office.ar';

const base = '/workspace/organizations/9101/restaurants/9201';
const scope = { organizationId: 9101, restaurantId: 9201 };
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

describe('report semantics and balanced indicators', () => {
  for (const locale of ['fr', 'en', 'ar'] as const)
    it(`shows exact counts and shares of each distribution in ${locale}`, async () => {
      await i18n.changeLanguage(locale);
      await mount(`${base}/reports`);
      const orders = await screen.findByRole('figure', {
        name: i18n.t('office.orderChart'),
      });
      expect(
        Array.from(
          orders.querySelectorAll<HTMLElement>('[data-proportion]'),
          (n) => Number(n.dataset.proportion),
        ),
      ).toEqual(Array(8).fill(12.5));
      expect(
        within(orders).getAllByText(
          (_, element) =>
            element?.tagName === 'BDI' &&
            element.textContent ===
              new Intl.NumberFormat(locale, {
                style: 'percent',
                maximumFractionDigits: 1,
              }).format(1 / 8),
        ),
      ).toHaveLength(8);
      for (const row of within(orders).getAllByRole('listitem'))
        expect(
          within(row).getByText(new Intl.NumberFormat(locale).format(1), {
            exact: true,
          }),
        ).toBeVisible();
      const categories = screen.getByRole('figure', {
        name: i18n.t('office.categoryChart'),
      });
      const widths = Array.from(
        categories.querySelectorAll<HTMLElement>('[data-proportion]'),
        (n) => Number(n.dataset.proportion),
      );
      expect(widths[0]).toBeCloseTo(200 / 3);
      expect(widths[1]).toBeCloseTo(100 / 3);
      const activity = screen.getByRole('region', {
        name: i18n.t('office.activityIndicators'),
      });
      const additional = screen.getByRole('region', {
        name: i18n.t('office.additionalIndicators'),
      });
      expect(
        within(activity).getAllByRole('heading', { level: 3 }),
      ).toHaveLength(3);
      expect(
        within(additional).getAllByRole('heading', { level: 3 }),
      ).toHaveLength(2);
      expect(
        within(additional).getAllByText(i18n.t('office.unavailable')),
      ).toHaveLength(2);
    });
  it('renders zero-total distributions with zero shares, not NaN or full bars', async () => {
    const adapter = createSyntheticAdapter(0);
    vi.spyOn(adapter, 'report').mockResolvedValue({
      restaurantId: 9201,
      totalOrders: 0,
      totalProducts: 0,
      totalCategories: 2,
      averageOrderValue: null,
      monthlyGrowth: null,
    });
    vi.spyOn(adapter, 'reportBreakdown').mockResolvedValue({
      restaurantId: 9201,
      orderCounts: orderStatuses.map((status) => ({ status, count: 0 })),
      categoryCounts: [
        { id: 1, name: 'Vide · فارغ', count: 0 },
        { id: 2, name: 'Empty', count: 0 },
      ],
    });
    await mount(`${base}/reports`, 'owner', adapter);
    await screen.findByRole('figure', { name: i18n.t('office.orderChart') });
    const fills = document.querySelectorAll<HTMLElement>('[data-proportion]');
    expect(fills).toHaveLength(10);
    for (const fill of fills) {
      expect(fill.dataset.proportion).toBe('0');
      expect(fill.style.inlineSize).toBe('0%');
    }
    expect(screen.getAllByText(i18n.t('office.unavailable'))).toHaveLength(2);
  });
  it('keeps a real zero distinct from an unavailable value', async () => {
    const adapter = createSyntheticAdapter(0);
    vi.spyOn(adapter, 'report').mockResolvedValue({
      restaurantId: 9201,
      totalOrders: 0,
      totalProducts: 0,
      totalCategories: 0,
      averageOrderValue: 0,
      monthlyGrowth: 0,
    });
    await mount(`${base}/reports`, 'owner', adapter);
    await screen.findByRole('heading', {
      name: i18n.t('office.average'),
      level: 3,
    });
    expect(
      document.querySelectorAll('[data-metric-state="unavailable"]'),
    ).toHaveLength(0);
    expect(
      document.querySelectorAll('[data-metric-state="value"]'),
    ).toHaveLength(5);
  });
  it('handles empty distributions without inventing category labels', async () => {
    const adapter = createSyntheticAdapter(0);
    vi.spyOn(adapter, 'reportBreakdown').mockResolvedValue({
      restaurantId: 9201,
      orderCounts: [],
      categoryCounts: [],
    });
    await mount(`${base}/reports`, 'owner', adapter);
    const chart = await screen.findByRole('figure', {
      name: i18n.t('office.categoryChart'),
    });
    expect(within(chart).getByText(i18n.t('office.empty'))).toBeVisible();
  });
});

describe('compact payment history with unchanged financial boundaries', () => {
  it('shows each summary field once and keeps detail/receipt controls collapsed', async () => {
    await mount(`${base}/billing`);
    await screen.findByRole('heading', { name: /Paiement.*920101/ });
    const rows = document.querySelectorAll<HTMLElement>('[data-payment-row]');
    expect(rows).toHaveLength(3);
    const first = rows[0]!;
    expect(first.querySelectorAll('dt')).toHaveLength(6);
    expect(within(first).getAllByText('BILLING-REVIEW-9201')).toHaveLength(1);
    expect(
      within(first).getAllByText(i18n.t('office.pending'), { exact: true }),
    ).toHaveLength(2);
    expect(first.querySelector('details')).not.toHaveAttribute('open');
    expect(first.querySelector('input')?.closest('details')).toBe(
      first.querySelector('details'),
    );
    const summary = first.querySelector('summary')!;
    await userEvent.click(summary);
    expect(
      within(first).getByRole('textbox', { name: i18n.t('office.reference') }),
    ).toBeVisible();
    expect(first.querySelectorAll('dt')).toHaveLength(6);
  });
  it('preserves filters and the pending state after a local receipt preview', async () => {
    const user = userEvent.setup();
    const { adapter } = await mount(`${base}/billing`);
    await screen.findByRole('heading', { name: /Paiement.*920101/ });
    const initial = await adapter.payments(scope, new AbortController().signal);
    await user.click(
      screen.getByText(i18n.t('office.localDraft'), { selector: 'summary' }),
    );
    await user.click(
      screen.getByRole('button', { name: i18n.t('office.preview') }),
    );
    expect(screen.getByRole('alert')).toHaveTextContent(
      i18n.t('office.invalid'),
    );
    await user.type(
      screen.getByRole('textbox', { name: i18n.t('office.reference') }),
      'SYNTHETIC-DRAFT-ONLY',
    );
    await user.upload(
      screen.getByLabelText(i18n.t('office.file')),
      new File(['synthetic'], 'review.pdf', { type: 'application/pdf' }),
    );
    await user.click(
      screen.getByRole('button', { name: i18n.t('office.preview') }),
    );
    expect(screen.getByRole('status')).toHaveTextContent(
      i18n.t('office.previewReady'),
    );
    expect(
      screen.getByRole('button', { name: i18n.t('office.send') }),
    ).toBeDisabled();
    expect(await adapter.payments(scope, new AbortController().signal)).toEqual(
      initial,
    );
    await user.selectOptions(
      screen.getByRole('combobox', { name: i18n.t('office.status') }),
      'refunded',
    );
    expect(
      screen.getByRole('heading', { name: i18n.t('office.empty') }),
    ).toBeVisible();
  });
  it('keeps a subscription simulation, draft and selected scope across appearance changes', async () => {
    const user = userEvent.setup();
    const { router } = await mount(`${base}/billing`);
    const form = within(
      await screen.findByRole('form', { name: i18n.t('office.offerPreview') }),
    );
    await user.selectOptions(
      form.getByRole('combobox', { name: i18n.t('office.method') }),
      'baridimob',
    );
    await user.selectOptions(
      form.getByRole('combobox', { name: i18n.t('office.cycle') }),
      'yearly',
    );
    await user.click(
      form.getByRole('button', { name: i18n.t('office.simulateCheckout') }),
    );
    await act(async () => {
      await i18n.changeLanguage('ar');
      window.moulaiTheme.choose('dark');
    });
    expect(
      form.getByRole('combobox', { name: i18n.t('office.cycle') }),
    ).toHaveValue('yearly');
    expect(form.getByRole('status')).toHaveTextContent(
      i18n.t('office.checkoutPreview'),
    );
    expect(screen.getByText('SYNTHETIC-RIP-NOT-PAYABLE')).toBeVisible();
    expect(router.state.location.pathname).toBe(`${base}/billing`);
  });
  for (const path of ['reports', 'billing'])
    it(`refuses Staff at ${path} without reading the protected projection`, async () => {
      const adapter = createSyntheticAdapter(0);
      const report = vi.spyOn(adapter, 'report');
      const payments = vi.spyOn(adapter, 'payments');
      await mount(
        `/workspace/organizations/9101/restaurants/9202/${path}`,
        'employee',
        adapter,
      );
      expect(await screen.findByRole('alert')).toBeVisible();
      expect(report).not.toHaveBeenCalled();
      expect(payments).not.toHaveBeenCalled();
    });
  it('retains complete FR/EN/AR copy', () => {
    for (const catalog of [officeEn, officeAr])
      expect(Object.keys(catalog).sort()).toEqual(Object.keys(officeFr).sort());
  });
});

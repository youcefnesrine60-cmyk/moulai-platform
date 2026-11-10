// MoulAI™ — mocked identity presentation, not proof of a remote sign-in.
import { describe, expect, it, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import i18n from '../../src/shared/i18n';
import { AccessPage } from '../../src/features/access/AccessPage';
import { interfaceQuality } from '../../src/shared/i18n/interfaceQuality';
import {
  PaymentProgress,
  SaasPayments,
} from '../../src/features/integration/SaasPayments';
import { exactAmountText } from '../../src/shared/ui/ExactAmount';
import { preferredSection } from '../../src/features/dining/local/navigation';
import { OwnerOfferPage } from '../../src/features/integration/OwnerOfferPage';

const target = vi.hoisted(() => ({ mode: 'authenticated-local' }));
vi.mock('../../src/app/access', () => ({
  useAdapter: () => ({ mode: target.mode }),
  useSession: () => ({ isPending: false, data: null }),
  identityKey: () => ['isolated-fixture'],
}));
vi.mock('../../src/features/management/scope', () => ({
  useSelection: () => ({ organizationId: 1, restaurantId: 2 }),
}));
function mount(child: React.ReactNode) {
  return render(
    <MemoryRouter>
      <QueryClientProvider
        client={
          new QueryClient({ defaultOptions: { queries: { retry: false } } })
        }
      >
        {child}
      </QueryClientProvider>
    </MemoryRouter>,
  );
}
describe('plain access actions and truthful session disclosure', () => {
  it('keeps translation coverage identical', () => {
    expect(Object.keys(interfaceQuality.fr)).toEqual(
      Object.keys(interfaceQuality.en),
    );
    expect(Object.keys(interfaceQuality.fr)).toEqual(
      Object.keys(interfaceQuality.ar),
    );
  });
  for (const locale of ['fr', 'en', 'ar']) {
    it(`${locale}: offers registration locally and keeps technical instructions folded`, async () => {
      target.mode = 'authenticated-local';
      await i18n.changeLanguage(locale);
      mount(<AccessPage />);
      expect(
        screen.getByRole('button', { name: i18n.t('access.signin') }),
      ).toBeEnabled();
      expect(
        screen.getByRole('link', { name: i18n.t('followup.register') }),
      ).toHaveAttribute('href', '/api/web/auth/register');
      const summary = screen.getByText(i18n.t('quality.sessionDetails'));
      expect(summary.closest('details')).not.toHaveAttribute('open');
      await userEvent.click(summary);
      expect(summary.closest('details')).toHaveAttribute('open');
      expect(summary.closest('details')).toHaveTextContent(
        i18n.t('quality.localDraft'),
      );
      expect(screen.getByText(i18n.t('quality.test'))).toBeVisible();
    });
    it(`${locale}: does not offer registration or verified local draft recovery in closed staging`, async () => {
      target.mode = 'authenticated-staging';
      await i18n.changeLanguage(locale);
      mount(<AccessPage />);
      expect(
        screen.queryByRole('link', { name: i18n.t('followup.register') }),
      ).toBeNull();
      expect(
        screen.getByText(i18n.t('quality.noPublicRegistration')),
      ).toBeVisible();
      expect(screen.queryByText(i18n.t('quality.localDraft'))).toBeNull();
      expect(
        screen.getByText(i18n.t('followup.sessionDraftStaging')),
      ).toBeInTheDocument();
    });
  }
});

describe('independent financial facts', () => {
  it('keeps a lost checkout response uncertain and refreshes by reading, without replaying payment creation', async () => {
    await i18n.changeLanguage('fr');
    const fetcher = vi
      .fn()
      .mockImplementation(async (_url: string, options?: RequestInit) => {
        if (options?.method === 'POST') throw new TypeError('Failed to fetch');
        return new Response('[]');
      });
    vi.stubGlobal('fetch', fetcher);
    mount(
      <SaasPayments
        organizationId={1}
        restaurantId={2}
        planId={3}
        cycle="monthly"
        currency="DZD"
      />,
    );
    const user = userEvent.setup();
    await screen.findByText(i18n.t('quality.noPayments'));
    await user.selectOptions(
      screen.getByRole('combobox', { name: i18n.t('o3.transferMethod') }),
      'ccp',
    );
    await user.click(
      screen.getByRole('button', { name: i18n.t('o3.checkout') }),
    );
    expect(await screen.findByText(i18n.t('quality.uncertain'))).toBeVisible();
    expect(
      screen.getByRole('button', { name: i18n.t('o3.checkout') }),
    ).toBeDisabled();
    await user.click(
      screen.getByRole('button', { name: i18n.t('quality.recheck') }),
    );
    expect(
      screen.getByRole('button', { name: i18n.t('o3.checkout') }),
    ).toBeEnabled();
    expect(
      fetcher.mock.calls.filter(([, options]) => options?.method === 'POST'),
    ).toHaveLength(1);
    vi.unstubAllGlobals();
  });
  it('discards the old simulation when the selected currency changes, without creating a payment', async () => {
    await i18n.changeLanguage('fr');
    const fetcher = vi
      .fn()
      .mockImplementation(async (url: string, options?: RequestInit) => {
        if (url.endsWith('/offer'))
          return new Response(
            JSON.stringify({
              base_reference: '3000',
              currency: 'DZD',
              country_code: 'DZ',
              currencies: ['DZD', 'EUR'],
              plans: [{ id: 3, code: 'basic', name: 'LOCAL-FAKE plan' }],
              blockers: [],
              binding_quote: false,
              registration_connected: true,
            }),
          );
        if (url.endsWith('/simulation'))
          return new Response(
            JSON.stringify({
              binding_quote: false,
              pricing: {
                base_price: '3000',
                restaurant_score: '0',
                loyalty_discount: '0',
                multi_restaurant_discount: '0',
                promotion_discount: '0',
                multi_branch_cost: '0',
                final_price: '3000',
                payment_adjustment: '-60',
                final_amount_due: '2940',
                parameters: { B: '3000', payment_adjustment_rate: '-0.02' },
              },
            }),
          );
        if (options?.method === 'POST') throw new Error('Unexpected mutation');
        return new Response('[]');
      });
    vi.stubGlobal('fetch', fetcher);
    mount(<OwnerOfferPage />);
    const user = userEvent.setup();
    await user.selectOptions(
      await screen.findByRole('combobox', { name: i18n.t('offer.plan') }),
      '3',
    );
    await user.click(
      screen.getByRole('button', { name: i18n.t('offer.simulate') }),
    );
    expect(
      await screen.findByRole('region', { name: i18n.t('quality.simulation') }),
    ).toBeVisible();
    await user.selectOptions(
      screen.getByRole('combobox', { name: i18n.t('o3.currency') }),
      'EUR',
    );
    expect(
      screen.queryByRole('region', { name: i18n.t('quality.simulation') }),
    ).toBeNull();
    expect(
      fetcher.mock.calls.filter(([, options]) => options?.method === 'POST'),
    ).toHaveLength(1);
    vi.unstubAllGlobals();
  });
  it.each(['fr', 'en', 'ar'])(
    '%s does not call a paid scheduled renewal active',
    async (locale) => {
      await i18n.changeLanguage(locale);
      mount(
        <PaymentProgress
          row={{
            id: 1,
            amount: '2940.00000000',
            currency: 'DZD',
            status: 'paid',
            receipt_status: 'approved',
            subscription_status: 'scheduled',
          }}
        />,
      );
      const stages = screen.getAllByRole('listitem');
      expect(stages).toHaveLength(3);
      expect(stages[1]).toHaveTextContent(i18n.t('quality.confirmed'));
      expect(stages[2]).toHaveTextContent(
        i18n.t('quality.subscription.scheduled'),
      );
      expect(stages[2]).not.toHaveTextContent(
        i18n.t('quality.subscription.active'),
      );
    },
  );
  it('keeps an absent subscription status unconfirmed', async () => {
    await i18n.changeLanguage('fr');
    mount(
      <PaymentProgress
        row={{
          id: 1,
          amount: '2940',
          currency: 'DZD',
          status: 'pending',
          receipt_status: 'pending',
        }}
      />,
    );
    expect(screen.getAllByRole('listitem')[2]).toHaveTextContent(
      i18n.t('quality.notConfirmed'),
    );
  });
  it('does not round a server decimal or lose large integer precision while formatting', () => {
    expect(exactAmountText('9007199254740993123.00500000', 'en')).toBe(
      '9,007,199,254,740,993,123.005',
    );
    expect(exactAmountText('2940.00000000', 'fr')).toMatch(/^2\D940$/);
    expect(exactAmountText('-1.00500000', 'en')).toBe('-1.005');
  });
  it('selects a work view from actual capabilities, without granting any right', () => {
    expect(preferredSection(['orders.prepare', 'orders.read'])).toBe('visits');
    expect(preferredSection(['finance.read', 'collect'])).toBe('finance');
    expect(preferredSection(['clean'])).toBe('planning');
    expect(preferredSection(['configure', 'finance.read'])).toBe('planning');
    expect(preferredSection([])).toBe('planning');
  });
  for (const [status, key] of [
    [403, 'state.noAccess.body'],
    [500, 'state.temporary.body'],
  ] as const) {
    it(`distinguishes HTTP ${status} from an empty payment list`, async () => {
      await i18n.changeLanguage('fr');
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue(new Response('{}', { status })),
      );
      mount(
        <SaasPayments
          organizationId={1}
          restaurantId={2}
          planId={3}
          cycle="monthly"
          currency="DZD"
        />,
      );
      expect(await screen.findByText(i18n.t(key))).toBeVisible();
      expect(screen.queryByText(i18n.t('quality.noPayments'))).toBeNull();
      expect(
        within(screen.getByRole('alert')).getByRole('button', {
          name: i18n.t('common.retry'),
        }),
      ).toBeEnabled();
      vi.unstubAllGlobals();
    });
  }
});

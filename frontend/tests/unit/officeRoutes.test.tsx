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

describe('office routes through real providers and scoped navigation', () => {
  for (const locale of ['fr', 'en', 'ar'] as const)
    for (const theme of ['light', 'dark'] as const)
      it(`renders reports in ${locale}/${theme} with unavailable financial values`, async () => {
        await i18n.changeLanguage(locale);
        window.moulaiTheme.choose(theme);
        await mount(`${base}/reports`);
        await screen.findByRole('heading', {
          name: i18n.t('nav.reports'),
          level: 1,
        });
        expect(
          await screen.findAllByText(i18n.t('office.unavailable')),
        ).toHaveLength(2);
        expect(document.documentElement.dir).toBe(
          locale === 'ar' ? 'rtl' : 'ltr',
        );
        expect(document.documentElement.dataset.theme).toBe(theme);
      });
  it('navigates from reports to billing and filters payments without changing scope', async () => {
    const user = userEvent.setup();
    const { router } = await mount(`${base}/reports`);
    await screen.findByRole('heading', {
      name: i18n.t('nav.reports'),
      level: 1,
    });
    await user.click(
      within(
        screen.getByRole('navigation', { name: i18n.t('restaurant.context') }),
      ).getByRole('link', { name: i18n.t('nav.billing') }),
    );
    await screen.findByRole('heading', { name: /Paiement.*920101/ });
    await user.selectOptions(
      screen.getByRole('combobox', { name: i18n.t('office.status') }),
      'refunded',
    );
    expect(
      screen.getByRole('heading', { name: i18n.t('office.empty') }),
    ).toBeVisible();
    expect(router.state.location.pathname).toBe(`${base}/billing`);
  });
  it('validates a receipt draft, keeps it across languages, never sends or changes payment state', async () => {
    const user = userEvent.setup();
    const { adapter } = await mount(`${base}/billing`);
    await screen.findByRole('heading', { name: /Paiement.*920101/ });
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
      screen.getByLabelText(i18n.t('office.reference'), { selector: 'input' }),
      'TEST-ONLY-123',
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
    await act(async () => {
      await i18n.changeLanguage('ar');
      window.moulaiTheme.choose('dark');
    });
    expect(screen.getByText('TEST-ONLY-123')).toBeVisible();
    expect(
      screen.getByRole('button', { name: i18n.t('office.send') }),
    ).toBeDisabled();
    expect(
      (
        await adapter.payments(
          { organizationId: 9101, restaurantId: 9201 },
          new AbortController().signal,
        )
      )[0]?.status,
    ).toBe('pending');
  });
  for (const [profile, path] of [
    ['manager', `${base}/billing`],
    ['employee', '/workspace/organizations/9101/restaurants/9202/reports'],
    ['owner', '/platform/receipts'],
    ['admin', `${base}/billing`],
  ] as const)
    it(`denies ${profile} at ${path}`, async () => {
      await mount(path, profile);
      expect(await screen.findByRole('alert')).toBeVisible();
      expect(
        screen.queryByRole('heading', { name: /Paiement.*920101/ }),
      ).toBeNull();
    });
  for (const section of ['requests', 'receipts', 'audit'] as const)
    it(`renders platform ${section} with read-only detail and no tenant selectors`, async () => {
      await mount(`/platform/${section}`, 'admin');
      await screen.findByRole('heading', {
        name: i18n.t(`nav.${section}`),
        level: 1,
      });
      await userEvent.click(
        screen.getByText(i18n.t('office.details'), { selector: 'summary' }),
      );
      if (section !== 'audit')
        expect(
          screen.getByRole('button', { name: i18n.t('office.approve') }),
        ).toBeDisabled();
      expect(
        screen.queryByRole('link', { name: i18n.t('nav.restaurants') }),
      ).toBeNull();
    });
  it('denies a platform section when the specific permission is missing', async () => {
    const adapter = createSyntheticAdapter(0);
    const original = adapter.getSession;
    const limited: AccessAdapter = {
      ...adapter,
      getSession: async (signal) => {
        const s = await original(signal);
        return s ? { ...s, platformPermissions: ['admins.manage'] } : null;
      },
    };
    const read = vi.spyOn(limited, 'platformRecords');
    await mount('/platform/receipts', 'admin', limited);
    expect(await screen.findByRole('alert')).toBeVisible();
    expect(read).not.toHaveBeenCalled();
  });
  it('shows empty report data without manufacturing zeroes', async () => {
    const adapter = createSyntheticAdapter(0);
    vi.spyOn(adapter, 'report').mockResolvedValue(null);
    await mount(`${base}/reports`, 'owner', adapter);
    expect(
      await screen.findByRole('heading', { name: i18n.t('office.empty') }),
    ).toBeVisible();
    expect(screen.queryByText(i18n.t('office.average'))).toBeNull();
  });
  it('shows a bounded read error and retries only on user request', async () => {
    const adapter = createSyntheticAdapter(0);
    const spy = vi
      .spyOn(adapter, 'payments')
      .mockRejectedValue(new AccessError('temporary'));
    await mount(`${base}/billing`, 'owner', adapter);
    expect(await screen.findByRole('alert')).toBeVisible();
    expect(spy).toHaveBeenCalledTimes(1);
    await userEvent.click(
      screen.getByRole('button', { name: i18n.t('common.retry') }),
    );
    expect(spy).toHaveBeenCalledTimes(2);
  });
});

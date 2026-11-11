// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Actual routed legacy editors, with a clearly synthetic adapter: no claim of persisted catalogue integration.
import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { describe, expect, it, vi } from 'vitest';
import { Providers, createQueryClient } from '../../src/app/Providers';
import { routes } from '../../src/app/router';
import { createSyntheticAdapter } from '../../src/review/syntheticAdapter';
import i18n from '../../src/shared/i18n';

const base = '/workspace/organizations/9101/restaurants/9201';
async function mount(path: string) {
  await i18n.changeLanguage('fr');
  const adapter = createSyntheticAdapter(0);
  await adapter.openReview('owner');
  const router = createMemoryRouter(routes, { initialEntries: [base + path] });
  const view = render(
    <Providers adapter={adapter} client={createQueryClient()}>
      <RouterProvider router={router} />
    </Providers>,
  );
  return { router, adapter, user: userEvent.setup(), view };
}

describe('legacy draft and filter continuity', () => {
  it('keeps all catalogue filters in the URL and restores them on a new mount', async () => {
    const initial =
      '?catalog-section=products&catalog-category=all&catalog-search=Pizza&catalog-availability=available&other=kept';
    const { router, user, view } = await mount('/catalogue' + initial);
    const search = await screen.findByRole('searchbox', {
      name: i18n.t('business.search'),
    });
    expect(search).toHaveValue('Pizza');
    await user.clear(search);
    await user.type(search, 'Café');
    expect(
      new URLSearchParams(router.state.location.search).get('catalog-search'),
    ).toBe('Café');
    expect(new URLSearchParams(router.state.location.search).get('other')).toBe(
      'kept',
    );
    const retained = router.state.location.search;
    view.unmount();
    await mount('/catalogue' + retained);
    expect(
      await screen.findByRole('searchbox', { name: i18n.t('business.search') }),
    ).toHaveValue('Café');
    expect(
      screen.getByRole('combobox', { name: i18n.t('business.available') }),
    ).toHaveValue('available');
  });
  it('retains catalogue text when refusing a close and discards only after explicit confirmation', async () => {
    const { user, adapter } = await mount('/catalogue');
    const save = vi.spyOn(adapter, 'saveReview');
    await user.click(
      await screen.findByRole('button', {
        name: i18n.t('business.addProduct'),
      }),
    );
    await user.type(
      screen.getByRole('textbox', { name: i18n.t('business.name') }),
      'Draft product',
    );
    await user.click(
      screen.getByRole('button', { name: i18n.t('business.cancel') }),
    );
    await user.click(
      screen.getByRole('button', { name: i18n.t('quality.stay') }),
    );
    expect(
      screen.getByRole('textbox', { name: i18n.t('business.name') }),
    ).toHaveValue('Draft product');
    await user.keyboard('{Escape}');
    await user.click(
      screen.getByRole('button', { name: i18n.t('quality.leave') }),
    );
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(save).not.toHaveBeenCalled();
  });
  it('protects an agent draft without activating or saving an agent', async () => {
    const { user, adapter } = await mount('/agents/920101');
    const save = vi.spyOn(adapter, 'saveAgentReview');
    const buttons = await screen.findAllByRole('button', {
      name: i18n.t('intelligence.configure'),
    });
    await user.click(buttons[0]!);
    const name = screen.getByRole('textbox', {
      name: i18n.t('intelligence.name'),
    });
    await user.clear(name);
    await user.type(name, 'Draft agent');
    await user.click(
      screen.getByRole('button', { name: i18n.t('intelligence.closeEditor') }),
    );
    await user.click(
      screen.getByRole('button', { name: i18n.t('quality.stay') }),
    );
    expect(
      screen.getByRole('textbox', { name: i18n.t('intelligence.name') }),
    ).toHaveValue('Draft agent');
    await user.keyboard('{Escape}');
    await user.click(
      screen.getByRole('button', { name: i18n.t('quality.leave') }),
    );
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(save).not.toHaveBeenCalled();
  });
  it('allows session expiration to remove a dirty legacy editor', async () => {
    const { user, router } = await mount('/catalogue');
    await user.click(
      await screen.findByRole('button', {
        name: i18n.t('business.addProduct'),
      }),
    );
    await user.type(
      screen.getByRole('textbox', { name: i18n.t('business.name') }),
      'Unsaved',
    );
    await act(async () => {
      window.dispatchEvent(new Event('moulai-session-expired'));
      await router.navigate('/access');
    });
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(
      await screen.findByRole('heading', { name: i18n.t('access.title') }),
    ).toBeVisible();
  });
});

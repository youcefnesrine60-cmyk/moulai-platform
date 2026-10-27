// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Providers, createQueryClient } from '../../src/app/Providers';
import { routes } from '../../src/app/router';
import { createSyntheticAdapter } from '../../src/review/syntheticAdapter';
import {
  AccessError,
  type AccessAdapter,
  type ReviewProfile,
} from '../../src/shared/access/contracts';
import i18n from '../../src/shared/i18n';
import type { AgentWorkspace } from '../../src/shared/intelligence/contracts';

const base = '/workspace/organizations/9101/restaurants/9201';

/** Mount real lazy routes and existing providers, with a private review session per test. */
async function mount(
  path: string,
  profile: ReviewProfile = 'owner',
  supplied?: AccessAdapter,
) {
  const adapter = supplied ?? createSyntheticAdapter(0);
  await adapter.openReview(profile);
  const client = createQueryClient();
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  const view = render(
    <Providers adapter={adapter} client={client}>
      <RouterProvider router={router} />
    </Providers>,
  );
  return { ...view, adapter, client, router };
}

beforeEach(async () => {
  await i18n.changeLanguage('fr');
  window.moulaiTheme.choose('light');
});

describe('scoped intelligence routes and local configuration', () => {
  it('navigates Agents → Channels → Conversations with actual scoped data', async () => {
    const user = userEvent.setup();
    await mount(`${base}/agents`);
    await screen.findByRole('heading', {
      name: i18n.t('nav.agents'),
      level: 1,
    });
    await user.type(
      screen.getByRole('searchbox', { name: i18n.t('intelligence.search') }),
      'Service',
    );
    expect(
      screen.queryByRole('heading', { name: 'Accueil · IA-REV-9201' }),
    ).toBeNull();
    const navigation = screen.getByRole('navigation', {
      name: i18n.t('restaurant.context'),
    });
    await user.click(
      within(navigation).getByRole('link', { name: i18n.t('nav.channels') }),
    );
    await screen.findByRole('heading', {
      name: i18n.t('nav.channels'),
      level: 1,
    });
    await user.selectOptions(
      screen.getByRole('combobox', {
        name: i18n.t('intelligence.channelType'),
      }),
      'telegram',
    );
    expect(
      screen.getByRole('heading', { name: 'Canal Telegram de revue 9201' }),
    ).toBeVisible();
    expect(
      screen.queryByRole('heading', { name: 'Canal web de revue 9201' }),
    ).toBeNull();
    await user.click(
      within(navigation).getByRole('link', {
        name: i18n.t('nav.conversations'),
      }),
    );
    await screen.findByRole('link', {
      name: /Consulter la conversation.*Visiteur de revue 1/,
    });
    await user.selectOptions(
      screen.getByRole('combobox', { name: i18n.t('intelligence.status') }),
      'closed',
    );
    await screen.findByRole('link', {
      name: /Consulter la conversation.*Visiteur de revue 2/,
    });
    expect(
      screen.queryByRole('link', {
        name: /Consulter la conversation.*Visiteur de revue 1/,
      }),
    ).toBeNull();
  });

  for (const profile of ['owner', 'manager'] as const)
    it(`${profile} validates, confirms and applies descriptive configuration locally`, async () => {
      const user = userEvent.setup();
      await mount(`${base}/agents/920101`, profile);
      await screen.findByRole('heading', {
        name: 'Accueil · IA-REV-9201',
        level: 1,
      });
      await user.click(
        screen.getByRole('button', { name: i18n.t('intelligence.configure') }),
      );
      const dialog = screen.getByRole('dialog');
      const name = within(dialog).getByRole('textbox', {
        name: i18n.t('intelligence.name'),
      });
      await user.clear(name);
      await user.type(name, '   ');
      await user.click(
        within(dialog).getByRole('button', {
          name: i18n.t('intelligence.preview'),
        }),
      );
      await waitFor(() => expect(name).toHaveAttribute('aria-invalid', 'true'));
      await user.clear(name);
      await user.type(name, 'Agent local validé');
      await user.click(
        within(dialog).getByRole('button', {
          name: i18n.t('intelligence.preview'),
        }),
      );
      expect(
        within(dialog).getByRole('heading', {
          name: i18n.t('intelligence.confirmTitle'),
        }),
      ).toBeVisible();
      await user.click(
        within(dialog).getByRole('button', {
          name: i18n.t('intelligence.applyReview'),
        }),
      );
      await screen.findByRole('heading', {
        name: 'Agent local validé',
        level: 1,
      });
      expect(screen.queryByRole('dialog')).toBeNull();
    });

  for (const suffix of [
    'agents/920301',
    'channels/920311',
    'conversations/920321',
    'agents/no-id',
    'conversations/0',
  ])
    it(`hides foreign or malformed resource ${suffix}`, async () => {
      await mount(`${base}/${suffix}`);
      await screen.findByRole('heading', {
        name: i18n.t('state.notFound.title'),
      });
      expect(screen.queryByText(/IA-REV-9203/)).toBeNull();
      expect(screen.queryByText(/synthetic-visitor-9203/)).toBeNull();
    });

  for (const section of ['agents', 'channels', 'conversations'])
    it(`Staff cannot read ${section} even on a granted restaurant`, async () => {
      const adapter = createSyntheticAdapter(0);
      const spy = vi.spyOn(adapter, 'agentWorkspace');
      await mount(
        `/workspace/organizations/9101/restaurants/9202/${section}`,
        'employee',
        adapter,
      );
      await screen.findByRole('heading', {
        name: i18n.t('state.noAccess.title'),
      });
      expect(spy).not.toHaveBeenCalled();
      expect(
        screen.queryByRole('link', { name: i18n.t('nav.agents') }),
      ).toBeNull();
    });

  for (const profile of ['unlinked', 'suspended'] as const)
    it(`keeps ${profile} state fail-closed`, async () => {
      await mount(`${base}/agents`, profile);
      await screen.findByRole('heading', {
        name: i18n.t(`state.${profile}.title`),
      });
    });

  it('platform area is not tenant membership and manager cannot switch to company B', async () => {
    await mount(`${base}/agents`, 'admin');
    await screen.findByRole('heading', {
      name: i18n.t('state.noAccess.title'),
    });
  });

  it('renders loading and cancels the pending read when the scope exits', async () => {
    const adapter = createSyntheticAdapter(0);
    let aborted = false;
    const spy = vi.spyOn(adapter, 'agentWorkspace').mockImplementation(
      (_scope, signal) =>
        new Promise<AgentWorkspace>((_resolve, reject) => {
          signal?.addEventListener(
            'abort',
            () => {
              aborted = true;
              reject(new DOMException('Cancelled', 'AbortError'));
            },
            { once: true },
          );
        }),
    );
    const { unmount } = await mount(`${base}/agents`, 'owner', adapter);
    await waitFor(() => expect(spy).toHaveBeenCalledOnce());
    expect(
      screen.getByRole('heading', { name: i18n.t('common.loading') }),
    ).toBeVisible();
    unmount();
    expect(aborted).toBe(true);
  });

  it('renders a recoverable module error', async () => {
    const adapter = createSyntheticAdapter(0);
    const original = adapter.agentWorkspace;
    const spy = vi
      .spyOn(adapter, 'agentWorkspace')
      .mockRejectedValueOnce(new AccessError('temporary'));
    const user = userEvent.setup();
    await mount(`${base}/agents`, 'owner', adapter);
    await screen.findByRole('heading', {
      name: i18n.t('state.temporary.title'),
    });
    spy.mockImplementation(original);
    await user.click(
      screen.getByRole('button', { name: i18n.t('common.retry') }),
    );
    await screen.findByRole('heading', { name: 'Accueil · IA-REV-9201' });
  });

  it('supports an empty agent workspace and empty conversation', async () => {
    const { router } = await mount(
      '/workspace/organizations/9101/restaurants/9202/agents',
    );
    await screen.findByRole('heading', { name: i18n.t('business.noResults') });
    await act(() => router.navigate(`${base}/conversations/920122`));
    await screen.findByText(i18n.t('intelligence.emptyMessages'));
  });

  it('renders message content as escaped text, preserves chronology and pages media safely', async () => {
    const user = userEvent.setup();
    const { container } = await mount(`${base}/conversations/920121`);
    await screen.findByText(/No HTML execution/);
    const timeline = screen.getByRole('list', {
      name: i18n.t('intelligence.messages'),
    });
    expect(within(timeline).getAllByRole('listitem')).toHaveLength(5);
    expect(container.querySelector('script, iframe, video, audio')).toBeNull();
    await user.click(
      screen.getByRole('button', { name: i18n.t('intelligence.next') }),
    );
    await screen.findByText(/Pièce jointe synthétique/);
    expect(
      screen.getByText(new RegExp(i18n.t('intelligence.mediaBoundary'))),
    ).toBeVisible();
    expect(container.querySelector('main img')).toBeNull();
    expect(screen.queryByRole('textbox')).toBeNull();
  });

  it('preserves a draft across languages/themes and drops module caches on scope exit', async () => {
    const user = userEvent.setup();
    const { router, client } = await mount(`${base}/agents/920101`);
    await screen.findByRole('heading', {
      name: 'Accueil · IA-REV-9201',
      level: 1,
    });
    await user.click(
      screen.getByRole('button', { name: i18n.t('intelligence.configure') }),
    );
    await user.clear(
      screen.getByRole('textbox', { name: i18n.t('intelligence.name') }),
    );
    await user.type(
      screen.getByRole('textbox', { name: i18n.t('intelligence.name') }),
      'Draft · مسودة',
    );
    for (const locale of ['en', 'ar', 'fr']) {
      await act(async () => {
        await i18n.changeLanguage(locale);
        window.moulaiTheme.choose('dark');
      });
      expect(
        screen.getByRole('textbox', { name: i18n.t('intelligence.name') }),
      ).toHaveValue('Draft · مسودة');
    }
    await user.click(
      screen.getByRole('button', { name: i18n.t('intelligence.closeEditor') }),
    );
    await waitFor(() =>
      expect(
        screen.getByRole('button', { name: i18n.t('intelligence.configure') }),
      ).toHaveFocus(),
    );
    expect(
      client
        .getQueryCache()
        .getAll()
        .some((query) => query.queryKey.includes('intelligence')),
    ).toBe(true);
    await act(() =>
      router.navigate('/workspace/organizations/9101/restaurants'),
    );
    await waitFor(() =>
      expect(
        client
          .getQueryCache()
          .getAll()
          .some((query) => query.queryKey.includes('intelligence')),
      ).toBe(false),
    );
  });
});

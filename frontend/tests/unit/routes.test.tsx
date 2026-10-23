// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { beforeEach, describe, expect, it } from 'vitest';
import { Providers, createQueryClient } from '../../src/app/Providers';
import { routes } from '../../src/app/router';
import { createSyntheticAdapter } from '../../src/review/syntheticAdapter';
import { disconnectedAdapter } from '../../src/shared/access/disconnected';
import type { ReviewProfile } from '../../src/shared/access/contracts';
import i18n from '../../src/shared/i18n';

/** Exercise actual routes, providers and cancellation with isolated in-memory data. */
async function mount(path: string, profile?: ReviewProfile) {
  const adapter = createSyntheticAdapter(0);
  if (profile) await adapter.openReview(profile);
  const client = createQueryClient();
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(
    <Providers adapter={adapter} client={client}>
      <RouterProvider router={router} />
    </Providers>,
  );
  return { router, client, adapter };
}

beforeEach(async () => {
  await i18n.changeLanguage('fr');
});

describe('browser access composition', () => {
  it('keeps production sign-in disconnected and hides synthetic review', async () => {
    render(
      <Providers adapter={disconnectedAdapter} client={createQueryClient()}>
        <RouterProvider
          router={createMemoryRouter(routes, { initialEntries: ['/access'] })}
        />
      </Providers>,
    );
    expect(
      await screen.findByRole('heading', {
        name: 'Bienvenue dans votre espace.',
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Continuer avec Keycloak' }),
    ).toBeDisabled();
    expect(
      screen.queryByRole('button', { name: 'Ouvrir la revue locale' }),
    ).not.toBeInTheDocument();
  });
  it('requires a session before displaying selected-company data', async () => {
    await mount('/workspace/organizations/9101/restaurants');
    expect(
      await screen.findByRole('heading', {
        name: 'Bienvenue dans votre espace.',
      }),
    ).toBeInTheDocument();
    expect(screen.queryByText('Maison Safran')).not.toBeInTheDocument();
  });
  it('navigates explicitly from an owner’s organizations to one restaurant', async () => {
    const user = userEvent.setup();
    await mount('/workspace', 'owner');
    await user.click(
      await screen.findByRole('link', {
        name: 'Ouvrir l’entreprise · Maison Safran',
      }),
    );
    await user.click(
      await screen.findByRole('link', {
        name: 'Ouvrir le restaurant · Alger · Centre',
      }),
    );
    expect(
      await screen.findByRole('heading', { name: 'Alger · Centre' }),
    ).toBeInTheDocument();
    expect(screen.queryByText('Oran · Front de mer')).not.toBeInTheDocument();
  });
  it('denies platform entry to an owner', async () => {
    await mount('/platform', 'owner');
    expect(
      await screen.findByRole('heading', {
        name: 'Cet espace ne vous est pas accessible.',
      }),
    ).toBeInTheDocument();
    expect(screen.queryByText('Revue des paiements')).not.toBeInTheDocument();
  });
  it('shows no restaurant for empty grants', async () => {
    await mount('/workspace/organizations/9101/restaurants', 'empty');
    expect(
      await screen.findByRole('heading', { name: 'Aucun restaurant accordé.' }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('link', { name: /Ouvrir le restaurant/ }),
    ).not.toBeInTheDocument();
  });
  it('does not disclose a foreign organization on a direct URL', async () => {
    await mount('/workspace/organizations/9102/restaurants', 'employee');
    expect(
      await screen.findByRole('heading', {
        name: 'Cet espace n’est pas disponible.',
      }),
    ).toBeInTheDocument();
    expect(screen.queryByText('Comptoir Atlas')).not.toBeInTheDocument();
  });
  it('hides staff billing and platform affordances rather than elevating the profile', async () => {
    await mount('/workspace/organizations/9101/restaurants/9202', 'employee');
    expect(
      await screen.findByRole('heading', { name: 'Alger · Les Jardins' }),
    ).toBeInTheDocument();
    expect(
      screen.queryByText('Abonnement & paiements'),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText('Administration & journaux'),
    ).not.toBeInTheDocument();
  });
  it('switches semantic direction and actual text to Arabic', async () => {
    await mount('/workspace', 'owner');
    await screen.findByRole('heading', {
      name: 'Chaque entreprise, son espace.',
    });
    await userEvent.click(screen.getByRole('button', { name: 'العربية' }));
    expect(
      await screen.findByRole('heading', { name: 'لكل مؤسسة مساحتها.' }),
    ).toBeInTheDocument();
    expect(document.documentElement).toHaveAttribute('dir', 'rtl');
    expect(document.documentElement).toHaveAttribute('lang', 'ar');
  });
  it('drops old tenant cache and data on sign-out', async () => {
    const { client, router } = await mount('/workspace', 'owner');
    await screen.findByRole('heading', {
      name: 'Chaque entreprise, son espace.',
    });
    await userEvent.click(
      screen.getByRole('button', { name: 'Quitter la revue' }),
    );
    await screen.findByRole('heading', {
      name: 'Bienvenue dans votre espace.',
    });
    expect(
      client
        .getQueryCache()
        .getAll()
        .some((query) => query.queryKey.includes('organizations')),
    ).toBe(false);
    await act(async () => {
      await router.navigate('/workspace/organizations/9101/restaurants');
    });
    expect(
      await screen.findByRole('heading', {
        name: 'Bienvenue dans votre espace.',
      }),
    ).toBeInTheDocument();
  });
});

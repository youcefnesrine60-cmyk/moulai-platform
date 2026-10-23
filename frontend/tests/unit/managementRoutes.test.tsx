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
  type ReviewProfile,
} from '../../src/shared/access/contracts';
import i18n from '../../src/shared/i18n';

const base = '/workspace/organizations/9101/restaurants/9201';

/** Mount the real route tree; controlled failures exist only in this test's adapter. */
async function mount(
  path = `${base}/catalogue`,
  profile: ReviewProfile = 'owner',
  configure?: (adapter: ReturnType<typeof createSyntheticAdapter>) => void,
) {
  const adapter = createSyntheticAdapter(0);
  await adapter.openReview(profile);
  configure?.(adapter);
  const client = createQueryClient();
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(
    <Providers adapter={adapter} client={client}>
      <RouterProvider router={router} />
    </Providers>,
  );
  return { adapter, router, client };
}

beforeEach(async () => {
  await i18n.changeLanguage('fr');
});

describe('restaurant catalogue and order composition', () => {
  it('validates a product price before confirmation, then applies a scoped local edit', async () => {
    const { adapter } = await mount();
    await screen.findByRole('heading', { name: 'Votre carte, en détail.' });
    await userEvent.click(
      screen.getByRole('button', { name: /Modifier le produit · Couscous/ }),
    );
    let dialog = within(screen.getByRole('dialog'));
    await userEvent.clear(dialog.getByRole('textbox', { name: 'Prix (DZD)' }));
    await userEvent.type(
      dialog.getByRole('textbox', { name: 'Prix (DZD)' }),
      '0',
    );
    await userEvent.click(
      dialog.getByRole('button', { name: 'Vérifier la modification' }),
    );
    expect(dialog.getByRole('textbox', { name: 'Prix (DZD)' })).toHaveAttribute(
      'aria-invalid',
      'true',
    );
    expect(
      dialog.queryByRole('button', { name: 'Appliquer à la revue' }),
    ).not.toBeInTheDocument();
    await userEvent.clear(dialog.getByRole('textbox', { name: 'Prix (DZD)' }));
    await userEvent.type(
      dialog.getByRole('textbox', { name: 'Prix (DZD)' }),
      '975,50',
    );
    await userEvent.click(
      dialog.getByRole('button', { name: 'Vérifier la modification' }),
    );
    dialog = within(screen.getByRole('dialog'));
    expect(dialog.getByText('975.50 DZD')).toBeInTheDocument();
    expect(
      (
        await adapter.workspace(
          { organizationId: 9101, restaurantId: 9201 },
          new AbortController().signal,
        )
      ).products[0]?.price,
    ).toBe(95000);
    await userEvent.click(
      dialog.getByRole('button', { name: 'Appliquer à la revue' }),
    );
    await waitFor(() =>
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument(),
    );
    expect(
      await screen.findByText(
        'Modification appliquée à la revue locale uniquement.',
      ),
    ).toBeInTheDocument();
    expect(
      (
        await adapter.workspace(
          { organizationId: 9101, restaurantId: 9201 },
          new AbortController().signal,
        )
      ).products[0]?.price,
    ).toBe(97550);
  });
  it('preserves an unsaved draft when returning from confirmation and cancels without mutation', async () => {
    const { adapter } = await mount();
    await userEvent.click(
      await screen.findByRole('button', { name: 'Catégories' }),
    );
    await userEvent.click(
      screen.getByRole('button', { name: 'Ajouter une catégorie' }),
    );
    let dialog = within(screen.getByRole('dialog'));
    await userEvent.type(
      dialog.getByRole('textbox', { name: 'Nom' }),
      'Category draft',
    );
    await userEvent.click(
      dialog.getByRole('button', { name: 'Vérifier la modification' }),
    );
    await userEvent.click(
      dialog.getByRole('button', { name: 'Revenir au formulaire' }),
    );
    dialog = within(screen.getByRole('dialog'));
    expect(dialog.getByRole('textbox', { name: 'Nom' })).toHaveValue(
      'Category draft',
    );
    await userEvent.click(dialog.getByRole('button', { name: 'Annuler' }));
    expect(
      (
        await adapter.workspace(
          { organizationId: 9101, restaurantId: 9201 },
          new AbortController().signal,
        )
      ).reviewRevision,
    ).toBe(1);
  });
  it('edits a group with its existing product and shows an empty option list', async () => {
    await mount();
    await userEvent.click(
      await screen.findByRole('button', {
        name: 'Options & groupes',
      }),
    );
    await userEvent.click(
      screen.getByRole('button', { name: /Modifier le groupe/ }),
    );
    const dialog = within(screen.getByRole('dialog'));
    await userEvent.click(
      dialog.getByRole('checkbox', { name: 'Choix obligatoire' }),
    );
    await userEvent.click(
      dialog.getByRole('button', { name: 'Vérifier la modification' }),
    );
    await userEvent.click(
      dialog.getByRole('button', { name: 'Appliquer à la revue' }),
    );
    await waitFor(() =>
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument(),
    );
    expect(screen.getByText('Choix obligatoire')).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole('button', { name: 'Ajouter un groupe' }),
    );
    const create = within(screen.getByRole('dialog'));
    await userEvent.type(
      create.getByRole('textbox', { name: 'Nom' }),
      'Empty group',
    );
    await userEvent.click(
      create.getByRole('button', { name: 'Vérifier la modification' }),
    );
    await userEvent.click(
      create.getByRole('button', { name: 'Appliquer à la revue' }),
    );
    expect(
      await screen.findByText('Ce groupe ne contient aucune option.'),
    ).toBeInTheDocument();
  });
  it('keeps Staff read-only in both catalogue and order details', async () => {
    const staff = '/workspace/organizations/9101/restaurants/9202';
    const { router } = await mount(`${staff}/catalogue`, 'employee');
    await screen.findByRole('heading', { name: 'Votre carte, en détail.' });
    expect(
      screen.queryByRole('button', { name: 'Ajouter un produit' }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /Modifier le produit/ }),
    ).not.toBeInTheDocument();
    await act(async () => {
      await router.navigate(`${staff}/orders/920260`);
    });
    await screen.findByRole('heading', { name: 'REV-9202-001' });
    expect(
      screen.queryByRole('button', { name: 'Modifier la note' }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText(/transitions de commande restent désactivées/),
    ).toBeInTheDocument();
  });
  it('denies a forged order ID without displaying another restaurant’s order', async () => {
    await mount(`${base}/orders/920360`);
    expect(
      await screen.findByRole('heading', {
        name: 'Cet espace n’est pas disponible.',
      }),
    ).toBeInTheDocument();
    expect(screen.queryByText('REV-9203-001')).not.toBeInTheDocument();
  });
  it('hides note editing for a completed order even from Owner', async () => {
    await mount(`${base}/orders/920163`);
    await screen.findByRole('heading', { name: 'REV-9201-004' });
    expect(
      screen.queryByRole('button', { name: 'Modifier la note' }),
    ).not.toBeInTheDocument();
  });
  it('denies a direct catalogue path outside the Staff restaurant grant', async () => {
    await mount(`${base}/catalogue`, 'employee');
    expect(
      await screen.findByRole('heading', {
        name: 'Cet espace n’est pas disponible.',
      }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Couscous maison/)).not.toBeInTheDocument();
  });
  it('renders empty catalogue with no create-product affordance before categories exist', async () => {
    await mount(`${base}/catalogue`, 'owner', (adapter) => {
      const read = adapter.workspace;
      vi.spyOn(adapter, 'workspace').mockImplementation(
        async (scope, signal) => ({
          ...(await read(scope, signal)),
          categories: [],
          products: [],
          groups: [],
          options: [],
          orders: [],
        }),
      );
    });
    expect(
      await screen.findByRole('heading', { name: 'Aucun résultat.' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Ajouter un produit' }),
    ).toBeDisabled();
  });
  it('recovers a workspace read error through the shared retry state', async () => {
    await mount(`${base}/catalogue`, 'owner', (adapter) => {
      vi.spyOn(adapter, 'workspace').mockRejectedValueOnce(
        new AccessError('temporary'),
      );
    });
    expect(
      await screen.findByRole('heading', {
        name: 'Votre espace n’a pas pu être chargé.',
      }),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Réessayer' }));
    expect(
      await screen.findByRole('heading', { name: 'Votre carte, en détail.' }),
    ).toBeInTheDocument();
  });
  it('does not announce a failed update as saved or erase the confirmation', async () => {
    await mount(`${base}/catalogue`, 'owner', (adapter) => {
      vi.spyOn(adapter, 'saveReview').mockRejectedValue(
        new AccessError('noAccess'),
      );
    });
    await userEvent.click(
      await screen.findByRole('button', { name: 'Catégories' }),
    );
    await userEvent.click(
      screen.getByRole('button', { name: 'Ajouter une catégorie' }),
    );
    const dialog = within(screen.getByRole('dialog'));
    await userEvent.type(
      dialog.getByRole('textbox', { name: 'Nom' }),
      'Attempt',
    );
    await userEvent.click(
      dialog.getByRole('button', { name: 'Vérifier la modification' }),
    );
    await userEvent.click(
      dialog.getByRole('button', { name: 'Appliquer à la revue' }),
    );
    expect(await dialog.findByRole('alert')).toHaveTextContent(
      'Modification refusée',
    );
    expect(
      dialog.getByRole('button', { name: 'Appliquer à la revue' }),
    ).toBeDisabled();
    expect(
      screen.queryByText(
        'Modification appliquée à la revue locale uniquement.',
      ),
    ).not.toBeInTheDocument();
  });
  it('filters order states and paginates only the selected restaurant', async () => {
    await mount(`${base}/orders`);
    await screen.findByRole('heading', {
      name: 'Les commandes, au même endroit.',
    });
    expect(
      screen.getAllByRole('link', { name: /Voir la commande ·/ }),
    ).toHaveLength(5);
    await userEvent.click(screen.getByRole('button', { name: 'Suivant' }));
    expect(
      screen.getAllByRole('link', { name: /Voir la commande ·/ }),
    ).toHaveLength(3);
    await userEvent.selectOptions(
      screen.getByRole('combobox', { name: 'État de commande' }),
      'pending',
    );
    expect(
      screen.getAllByRole('link', { name: /Voir la commande ·/ }),
    ).toHaveLength(1);
    expect(
      screen.getByRole('link', { name: 'Voir la commande · REV-9201-001' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Suivant' })).toBeDisabled();
  });
  it('shows Arabic catalogue fields and semantic RTL without changing resource IDs', async () => {
    await mount();
    await screen.findByRole('heading', { name: 'Votre carte, en détail.' });
    await userEvent.click(screen.getByRole('button', { name: 'العربية' }));
    expect(
      screen.getByRole('heading', { name: 'قائمة مطعمك بالتفصيل.' }),
    ).toBeInTheDocument();
    expect(document.documentElement).toHaveAttribute('dir', 'rtl');
    await userEvent.click(screen.getByRole('button', { name: 'إضافة منتج' }));
    expect(
      within(screen.getByRole('dialog')).getByRole('textbox', {
        name: 'السعر (دج)',
      }),
    ).toBeInTheDocument();
  });
});

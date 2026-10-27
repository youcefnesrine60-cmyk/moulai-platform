// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { beforeEach, describe, expect, it } from 'vitest';
import { Providers, createQueryClient } from '../../src/app/Providers';
import { routes } from '../../src/app/router';
import { createSyntheticAdapter } from '../../src/review/syntheticAdapter';
import i18n from '../../src/shared/i18n';

const path = '/workspace/organizations/9101/restaurants/9201/catalogue';

/** Keep the real cache, providers, scope and form composition throughout preference changes. */
async function mount() {
  const adapter = createSyntheticAdapter(0);
  await adapter.openReview('owner');
  const client = createQueryClient();
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(
    <Providers adapter={adapter} client={client}>
      <RouterProvider router={router} />
    </Providers>,
  );
  await screen.findByRole('heading', { name: 'Votre carte, en détail.' });
  return { adapter, router, client };
}

beforeEach(async () => {
  window.moulaiTheme.choose('light');
  await i18n.changeLanguage('fr');
});

describe('live language and appearance changes', () => {
  it('preserves an invalid product draft, validation and selected company across FR/EN/AR and themes', async () => {
    const { adapter, router } = await mount();
    await userEvent.click(
      screen.getByRole('button', { name: 'Ajouter un produit' }),
    );
    const dialog = within(screen.getByRole('dialog'));
    await userEvent.type(
      dialog.getByRole('textbox', { name: 'Nom' }),
      'Draft · مسودة',
    );
    await userEvent.type(
      dialog.getByRole('textbox', { name: 'Prix (DZD)' }),
      '0',
    );
    await userEvent.click(
      dialog.getByRole('button', { name: 'Vérifier la modification' }),
    );
    await userEvent.click(
      dialog.getByRole('combobox', { name: i18n.t('preferences.language') }),
    );
    await userEvent.click(screen.getByRole('option', { name: 'English — EN' }));
    expect(
      dialog.getByRole('heading', { name: 'Add product' }),
    ).toBeInTheDocument();
    expect(dialog.getByRole('textbox', { name: 'Name' })).toHaveValue(
      'Draft · مسودة',
    );
    expect(dialog.getByRole('textbox', { name: 'Price (DZD)' })).toHaveValue(
      '0',
    );
    expect(
      dialog.getByText('Check this field and the stated limits.'),
    ).toBeInTheDocument();
    await act(async () => {
      window.moulaiTheme.choose('dark');
    });
    await userEvent.click(
      dialog.getByRole('combobox', { name: i18n.t('preferences.language') }),
    );
    await userEvent.click(screen.getByRole('option', { name: 'العربية — AR' }));
    expect(document.documentElement).toHaveAttribute('dir', 'rtl');
    expect(document.documentElement).toHaveAttribute('data-theme', 'dark');
    expect(dialog.getByRole('textbox', { name: 'الاسم' })).toHaveValue(
      'Draft · مسودة',
    );
    expect(router.state.location.pathname).toBe(path);
    expect(
      (
        await adapter.workspace(
          { organizationId: 9101, restaurantId: 9201 },
          new AbortController().signal,
        )
      ).reviewRevision,
    ).toBe(1);
  });
  it('keeps a confirmation and its draft intact when language changes before returning to edit', async () => {
    await mount();
    await userEvent.click(screen.getByRole('button', { name: 'Catégories' }));
    await userEvent.click(
      screen.getByRole('button', { name: 'Ajouter une catégorie' }),
    );
    const dialog = within(screen.getByRole('dialog'));
    await userEvent.type(
      dialog.getByRole('textbox', { name: 'Nom' }),
      'Untouched draft',
    );
    await userEvent.click(
      dialog.getByRole('button', { name: 'Vérifier la modification' }),
    );
    await userEvent.click(
      dialog.getByRole('combobox', { name: i18n.t('preferences.language') }),
    );
    await userEvent.click(screen.getByRole('option', { name: 'English — EN' }));
    expect(
      dialog.getByRole('heading', { name: 'Confirm review change' }),
    ).toBeInTheDocument();
    expect(dialog.getByText('Untouched draft')).toBeInTheDocument();
    await userEvent.click(dialog.getByRole('button', { name: 'Back to form' }));
    expect(dialog.getByRole('textbox', { name: 'Name' })).toHaveValue(
      'Untouched draft',
    );
  });
});

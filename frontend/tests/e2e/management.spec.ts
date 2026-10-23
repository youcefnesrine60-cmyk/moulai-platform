// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { expect, test, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const base = '/workspace/organizations/9101/restaurants/9201';

/** Enter the explicit synthetic review and select an admitted restaurant. */
async function enter(page: Page, staff = false): Promise<void> {
  await page.goto('/access');
  if (staff) {
    await page.getByRole('combobox', { name: 'Profil de test' }).click();
    await page
      .getByRole('option', {
        name: 'Staff · un restaurant accordé',
        exact: true,
      })
      .click();
  }
  await page.getByRole('button', { name: 'Ouvrir la revue locale' }).click();
  await page
    .getByRole('link', { name: 'Ouvrir l’entreprise · Maison Safran' })
    .click();
  await page
    .getByRole('link', {
      name: `Ouvrir le restaurant · Alger · ${staff ? 'Les Jardins' : 'Centre'}`,
      exact: true,
    })
    .click();
  await expect(
    page.getByRole('heading', {
      name: `Alger · ${staff ? 'Les Jardins' : 'Centre'}`,
      exact: true,
    }),
  ).toBeVisible();
}

/** Browser-only navigation retains the session without reloading or touching an API. */
async function navigate(page: Page, path: string): Promise<void> {
  await page.evaluate((destination) => {
    history.pushState(null, '', destination);
    dispatchEvent(new PopStateEvent('popstate'));
  }, path);
}

/** Confirm that a validated change is local, and wait for the scoped query refresh. */
async function apply(page: Page): Promise<void> {
  const dialog = page.getByRole('dialog');
  await dialog
    .getByRole('button', { name: 'Vérifier la modification' })
    .click();
  await expect(
    dialog.getByRole('heading', { name: 'Confirmer la modification de revue' }),
  ).toBeVisible();
  await dialog.getByRole('button', { name: 'Appliquer à la revue' }).click();
  await expect(dialog).toHaveCount(0);
  await expect(
    page.getByRole('status').filter({
      hasText: 'Modification appliquée à la revue locale uniquement.',
    }),
  ).toBeVisible();
}

test.beforeEach(async ({ page }) => {
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    expect(['127.0.0.1', 'localhost']).toContain(url.hostname);
    expect(['5173', '4173']).toContain(url.port);
    await route.continue();
  });
  page.on('pageerror', (error) => {
    throw error;
  });
});

test('restaurant editing, confirmation, keyboard cancellation and contextual rename', async ({
  page,
}, info) => {
  await enter(page);
  const button = page.getByRole('button', { name: 'Modifier la fiche' });
  await button.click();
  await expect(page.getByRole('dialog')).toBeVisible();
  const scan = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
    .analyze();
  expect(scan.violations).toEqual([]);
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(button).toBeFocused();
  await button.click();
  await page
    .getByRole('dialog')
    .getByRole('textbox', { name: 'Nom', exact: true })
    .fill('Restaurant de revue · وسط');
  await apply(page);
  await expect(
    page.getByRole('heading', { name: 'Restaurant de revue · وسط' }),
  ).toBeVisible();
  await page.screenshot({
    path: `../artifacts/frontend-management-validation/${info.project.name}-restaurant-fr.png`,
    fullPage: true,
  });
  await page
    .getByRole('link', { name: 'Changer de restaurant', exact: true })
    .click();
  await expect(
    page.getByRole('link', {
      name: 'Ouvrir le restaurant · Restaurant de revue · وسط',
    }),
  ).toBeVisible();
});

test('category/product creation, exact decimal validation and availability filters', async ({
  page,
}, info) => {
  await enter(page);
  await page
    .getByRole('navigation', { name: 'Votre périmètre actuel' })
    .getByRole('link', { name: 'Catalogue' })
    .click();
  await page.getByRole('button', { name: 'Catégories', exact: true }).click();
  await page.getByRole('button', { name: 'Ajouter une catégorie' }).click();
  await page
    .getByRole('dialog')
    .getByRole('textbox', { name: 'Nom', exact: true })
    .fill('Desserts de revue');
  await apply(page);
  await page.getByRole('button', { name: 'Produits', exact: true }).click();
  await page.getByRole('button', { name: 'Ajouter un produit' }).click();
  const dialog = page.getByRole('dialog');
  await dialog
    .getByRole('textbox', { name: 'Nom', exact: true })
    .fill('Dessert de revue');
  await dialog
    .getByRole('combobox', { name: 'Catégorie', exact: true })
    .selectOption({ label: 'Desserts de revue' });
  await dialog.getByRole('textbox', { name: 'Prix (DZD)' }).fill('0');
  await dialog
    .getByRole('button', { name: 'Vérifier la modification' })
    .click();
  await expect(
    dialog.getByRole('textbox', { name: 'Prix (DZD)' }),
  ).toHaveAttribute('aria-invalid', 'true');
  await dialog.getByRole('textbox', { name: 'Prix (DZD)' }).fill('325,50');
  await apply(page);
  await page
    .getByRole('button', {
      name: 'Modifier le produit · Dessert de revue',
      exact: true,
    })
    .click();
  await dialog
    .getByRole('checkbox', { name: 'Disponible', exact: true })
    .uncheck();
  await apply(page);
  await page
    .getByRole('combobox', { name: 'Catégorie', exact: true })
    .selectOption({ label: 'Desserts de revue' });
  await expect(
    page.getByRole('heading', { name: 'Dessert de revue', exact: true }),
  ).toBeVisible();
  await page
    .getByRole('combobox', { name: 'Disponible', exact: true })
    .selectOption('available');
  await expect(
    page.getByRole('heading', { name: 'Aucun résultat.' }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Effacer les filtres' }).click();
  await expect(
    page.getByRole('heading', { name: 'Couscous maison · كسكس الدار' }),
  ).toBeVisible();
  await page.screenshot({
    path: `../artifacts/frontend-management-validation/${info.project.name}-catalogue-fr.png`,
    fullPage: true,
  });
});

test('product option groups, required/multiple choice and zero-priced option editing', async ({
  page,
}) => {
  await enter(page);
  await navigate(page, `${base}/catalogue`);
  await page.getByRole('button', { name: 'Options & groupes' }).click();
  await page
    .getByRole('button', { name: 'Ajouter un groupe', exact: true })
    .click();
  const dialog = page.getByRole('dialog');
  await dialog
    .getByRole('textbox', { name: 'Nom', exact: true })
    .fill('Choix de revue');
  await dialog.getByRole('checkbox', { name: 'Choix obligatoire' }).check();
  await apply(page);
  await page
    .getByRole('button', {
      name: 'Ajouter une option · Choix de revue',
      exact: true,
    })
    .click();
  await dialog
    .getByRole('textbox', { name: 'Nom', exact: true })
    .fill('Sans supplément de revue');
  await dialog.getByRole('textbox', { name: 'Supplément (DZD)' }).fill('0');
  await apply(page);
  await page
    .getByRole('button', {
      name: 'Modifier l’option · Sans supplément de revue',
    })
    .click();
  await dialog
    .getByRole('checkbox', { name: 'Disponible', exact: true })
    .uncheck();
  await apply(page);
  const group = page.locator('section').filter({
    has: page.getByRole('heading', { name: 'Choix de revue', exact: true }),
  });
  await expect(group.getByText('Indisponible', { exact: false })).toBeVisible();
  await expect(
    group.getByText('Choix obligatoire', { exact: true }),
  ).toBeVisible();
  await expect(group.getByText('Un seul choix', { exact: true })).toBeVisible();
});

test('orders filtering/pagination, detailed amounts and note-only confirmation', async ({
  page,
}, info) => {
  await enter(page);
  await navigate(page, `${base}/orders`);
  await expect(
    page.getByRole('link', { name: /Voir la commande ·/ }),
  ).toHaveCount(5);
  await page.getByRole('button', { name: 'Suivant', exact: true }).click();
  await expect(
    page.getByRole('link', { name: /Voir la commande ·/ }),
  ).toHaveCount(3);
  await page
    .getByRole('combobox', { name: 'État de commande' })
    .selectOption('pending');
  await expect(
    page.getByRole('link', { name: /Voir la commande ·/ }),
  ).toHaveCount(1);
  await page.screenshot({
    path: `../artifacts/frontend-management-validation/${info.project.name}-orders-fr.png`,
    fullPage: true,
  });
  await page
    .getByRole('link', { name: 'Voir la commande · REV-9201-001' })
    .click();
  await expect(
    page.getByRole('heading', { name: 'REV-9201-001' }),
  ).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'Articles commandés' }),
  ).toBeVisible();
  const totalsBefore = await page.locator('dl').innerText();
  await page.getByRole('button', { name: 'Modifier la note' }).click();
  await page
    .getByRole('dialog')
    .getByRole('textbox', { name: 'Note client' })
    .fill('Note synthétique · ملاحظة المراجعة');
  await apply(page);
  await expect(
    page.getByText('Note synthétique · ملاحظة المراجعة', { exact: true }),
  ).toBeVisible();
  expect(await page.locator('dl').innerText()).toBe(totalsBefore);
  await expect(
    page.getByRole('button', {
      name: /Confirmer la commande|Encaisser|Préparer/,
    }),
  ).toHaveCount(0);
  await page.screenshot({
    path: `../artifacts/frontend-management-validation/${info.project.name}-order-detail-fr.png`,
    fullPage: true,
  });
  await navigate(page, `${base}/orders/920163`);
  await expect(
    page.getByRole('heading', { name: 'REV-9201-004' }),
  ).toBeVisible();
  await expect(
    page.getByRole('button', { name: 'Modifier la note' }),
  ).toHaveCount(0);
  await navigate(page, `${base}/orders/920360`);
  await expect(
    page.getByRole('heading', { name: 'Cet espace n’est pas disponible.' }),
  ).toBeVisible();
  await expect(page.getByText('REV-9203-001')).toHaveCount(0);
});

test('Staff receives read-only catalogue/orders and cannot enter another restaurant', async ({
  page,
}) => {
  await enter(page, true);
  const staff = '/workspace/organizations/9101/restaurants/9202';
  await expect(
    page.getByRole('button', { name: 'Modifier la fiche' }),
  ).toHaveCount(0);
  await navigate(page, `${staff}/catalogue`);
  await expect(
    page.getByRole('heading', { name: 'Votre carte, en détail.' }),
  ).toBeVisible();
  await expect(
    page.getByRole('button', {
      name: /Ajouter un produit|Modifier le produit/,
    }),
  ).toHaveCount(0);
  await navigate(page, `${staff}/orders/920260`);
  await expect(
    page.getByRole('heading', { name: 'REV-9202-001' }),
  ).toBeVisible();
  await expect(
    page.getByRole('button', { name: 'Modifier la note' }),
  ).toHaveCount(0);
  await navigate(page, `${base}/catalogue`);
  await expect(
    page.getByRole('heading', { name: 'Cet espace n’est pas disponible.' }),
  ).toBeVisible();
});

test('same-owner company switch never shares catalogue data or a pending editor', async ({
  page,
}) => {
  await enter(page);
  await navigate(page, `${base}/catalogue`);
  await expect(
    page.getByRole('heading', { name: 'Couscous maison · كسكس الدار' }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Ajouter un produit' }).click();
  await navigate(
    page,
    '/workspace/organizations/9102/restaurants/9203/catalogue',
  );
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(
    page.getByRole('heading', { name: 'Couscous Atlas · كسكس الأطلس' }),
  ).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'Couscous maison · كسكس الدار' }),
  ).toHaveCount(0);
  await navigate(
    page,
    '/workspace/organizations/9101/restaurants/9203/catalogue',
  );
  await expect(
    page.getByRole('heading', { name: 'Cet espace n’est pas disponible.' }),
  ).toBeVisible();
});

test('French and Arabic management views, modal keyboard and 360px layout pass targeted axe scans', async ({
  page,
}, info) => {
  test.setTimeout(60000);
  await enter(page);
  await navigate(page, `${base}/catalogue`);
  await expect(
    page.getByRole('heading', { name: 'Votre carte, en détail.' }),
  ).toBeVisible();
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page.getByRole('button', { name: 'العربية' }).click();
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
  if (info.project.name === 'mobile')
    await page.setViewportSize({ width: 360, height: 800 });
  await page.screenshot({
    path: `../artifacts/frontend-management-validation/${info.project.name}-catalogue-ar.png`,
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  const trigger = page.getByRole('button', { name: 'إضافة منتج' });
  await trigger.click();
  await expect(
    page.getByRole('dialog').getByRole('textbox', { name: 'السعر (دج)' }),
  ).toBeVisible();
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page.keyboard.press('Escape');
  await expect(trigger).toBeFocused();
  await navigate(page, `${base}/orders`);
  await expect(
    page.getByRole('heading', { name: 'كل الطلبات في مكان واحد.' }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page.screenshot({
    path: `../artifacts/frontend-management-validation/${info.project.name}-orders-ar.png`,
    fullPage: true,
  });
  await navigate(page, `${base}/orders/920260`);
  await expect(
    page.getByRole('heading', { name: 'هذه المساحة غير متاحة.' }),
  ).toBeVisible();
  await navigate(page, `${base}/orders/920160`);
  await expect(
    page.getByRole('heading', { name: 'REV-9201-001' }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page.screenshot({
    path: `../artifacts/frontend-management-validation/${info.project.name}-order-detail-ar.png`,
    fullPage: true,
  });
});

test('normal build refuses direct management entry without a review or live sign-in', async ({
  page,
}) => {
  for (const path of [
    `${base}/catalogue`,
    `${base}/orders`,
    `${base}/orders/920160`,
  ]) {
    await page.goto(`http://127.0.0.1:4173${path}`);
    await expect(page).toHaveURL('http://127.0.0.1:4173/access');
    await expect(
      page.getByRole('button', { name: 'Continuer avec Keycloak' }),
    ).toBeDisabled();
    await expect(
      page.getByRole('button', { name: 'Ouvrir la revue locale' }),
    ).toHaveCount(0);
  }
});

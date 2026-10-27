// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { expect, test, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

/** Enter only the explicitly labeled fixture review; never a real login flow. */
async function enter(
  page: Page,
  profile = 'Owner · deux entreprises',
): Promise<void> {
  await page.goto('/access');
  await expect(
    page.getByRole('heading', { name: 'Bienvenue dans votre espace.' }),
  ).toBeVisible();
  if (profile !== 'Owner · deux entreprises') {
    await page.getByRole('combobox', { name: 'Profil de test' }).click();
    await page.getByRole('option', { name: profile, exact: true }).click();
  }
  await page.getByRole('button', { name: 'Ouvrir la revue locale' }).click();
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

test('explicit owner selection, A/B isolation, back navigation and no overflow', async ({
  page,
}, testInfo) => {
  await enter(page);
  await expect(
    page.getByRole('heading', { name: 'Chaque entreprise, son espace.' }),
  ).toBeVisible();
  await expect(
    page.getByText(
      'Revue locale · données synthétiques · aucun service connecté',
    ),
  ).toBeVisible();
  await page.screenshot({
    path: `../artifacts/frontend-validation/${testInfo.project.name}-companies-fr.png`,
    fullPage: true,
  });
  await page
    .getByRole('link', { name: 'Ouvrir l’entreprise · Maison Safran' })
    .click();
  await expect(
    page.getByRole('heading', { name: '2 restaurants accessibles' }),
  ).toBeVisible();
  await expect(page.getByText('Oran · Front de mer')).toHaveCount(0);
  await page
    .getByRole('link', { name: 'Ouvrir le restaurant · Alger · Centre' })
    .click();
  await expect(
    page.getByRole('heading', { name: 'Alger · Centre' }),
  ).toBeVisible();
  await page.goBack();
  await expect(
    page.getByRole('heading', { name: 'Maison Safran' }),
  ).toBeVisible();
  await page.getByRole('link', { name: 'Retour aux entreprises' }).click();
  await page
    .getByRole('link', { name: 'Ouvrir l’entreprise · Comptoir Atlas' })
    .click();
  await expect(
    page.getByRole('link', {
      name: 'Ouvrir le restaurant · Oran · Front de mer',
    }),
  ).toBeVisible();
  await expect(page.getByText('Alger · Centre')).toHaveCount(0);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test('staff explicit grants and foreign restaurant denial', async ({
  page,
}) => {
  await enter(page, 'Staff · un restaurant accordé');
  await page
    .getByRole('link', { name: 'Ouvrir l’entreprise · Maison Safran' })
    .click();
  await expect(
    page.getByRole('heading', { name: '1 restaurant accessible' }),
  ).toBeVisible();
  await expect(page.getByText('Alger · Centre')).toHaveCount(0);
  await page
    .getByRole('link', { name: 'Ouvrir le restaurant · Alger · Les Jardins' })
    .click();
  await expect(
    page.getByRole('heading', { name: 'Alger · Les Jardins' }),
  ).toBeVisible();
  await expect(page.getByText('Abonnement & paiements')).toHaveCount(0);
  // In-app navigation preserves the ephemeral session while exercising URL tampering.
  await page.evaluate(() => {
    history.pushState(
      null,
      '',
      '/workspace/organizations/9101/restaurants/9201',
    );
    dispatchEvent(new PopStateEvent('popstate'));
  });
  await expect(
    page.getByRole('heading', { name: 'Cet espace n’est pas disponible.' }),
  ).toBeVisible();
});

test('empty grants stay empty', async ({ page }) => {
  await enter(page, 'Staff · aucun restaurant accordé');
  await page
    .getByRole('link', { name: 'Ouvrir l’entreprise · Maison Safran' })
    .click();
  await expect(
    page.getByRole('heading', { name: 'Aucun restaurant accordé.' }),
  ).toBeVisible();
  await expect(
    page.getByRole('link', { name: /Ouvrir le restaurant/ }),
  ).toHaveCount(0);
});

test('unlinked and suspended identities have explicit denial screens', async ({
  page,
}) => {
  await enter(page, 'Identité sans association');
  await expect(
    page.getByRole('heading', {
      name: 'Aucun accès associé à cette identité.',
    }),
  ).toBeVisible();
  await page
    .getByRole('button', { name: 'Changer de profil de revue' })
    .click();
  await page.getByRole('combobox', { name: 'Profil de test' }).click();
  await page
    .getByRole('option', { name: 'Accès suspendu', exact: true })
    .click();
  await page.getByRole('button', { name: 'Ouvrir la revue locale' }).click();
  await expect(
    page.getByRole('heading', { name: 'Votre accès est suspendu.' }),
  ).toBeVisible();
});

test('temporary failure has working retry and an exit', async ({ page }) => {
  await enter(page, 'Erreur temporaire');
  await expect(
    page.getByRole('heading', { name: 'Votre espace n’a pas pu être chargé.' }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Réessayer' }).click();
  await expect(
    page.getByRole('heading', { name: 'Votre espace n’a pas pu être chargé.' }),
  ).toBeVisible();
  await page
    .getByRole('button', { name: 'Changer de profil de revue' })
    .click();
  await expect(
    page.getByRole('heading', { name: 'Bienvenue dans votre espace.' }),
  ).toBeVisible();
});

test('platform has its own navigation, without tenant access', async ({
  page,
}) => {
  await enter(page, 'Administration plateforme');
  await expect(
    page.getByRole('heading', { name: 'Un espace dédié à la plateforme.' }),
  ).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'Revue des paiements' }),
  ).toBeVisible();
  await expect(page.getByText('Maison Safran')).toHaveCount(0);
  await page.evaluate(() => {
    history.pushState(null, '', '/workspace');
    dispatchEvent(new PopStateEvent('popstate'));
  });
  await expect(
    page.getByRole('heading', {
      name: 'Cet espace ne vous est pas accessible.',
    }),
  ).toBeVisible();
});

test('Arabic text, semantic RTL, keyboard/mobile menu and accessibility', async ({
  page,
}, testInfo) => {
  await enter(page);
  await page
    .getByRole('combobox', {
      name: /Langue de l.interface|Interface language|لغة الواجهة/,
    })
    .click();
  await page.getByRole('option', { name: 'العربية — AR' }).click();
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
  await expect(page.locator('html')).toHaveAttribute('lang', 'ar');
  await expect(
    page.getByRole('heading', { name: 'لكل مؤسسة مساحتها.' }),
  ).toBeVisible();
  if (testInfo.project.name === 'mobile') {
    await page.getByRole('button', { name: 'فتح القائمة' }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await expect(
      page.getByRole('button', { name: 'فتح القائمة' }),
    ).toBeFocused();
  }
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  const scan = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
    .analyze();
  expect(scan.violations).toEqual([]);
  await page.screenshot({
    path: `../artifacts/frontend-validation/${testInfo.project.name}-companies-ar.png`,
    fullPage: true,
  });
});

test('loading and access screen are readable and accessible', async ({
  page,
}, testInfo) => {
  await page.goto('/access');
  await expect(
    page.getByRole('heading', { name: 'Bienvenue dans votre espace.' }),
  ).toBeVisible();
  const scan = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
    .analyze();
  expect(scan.violations).toEqual([]);
  await page.screenshot({
    path: `../artifacts/frontend-validation/${testInfo.project.name}-access-fr.png`,
    fullPage: true,
  });
  await page.getByRole('button', { name: 'Ouvrir la revue locale' }).click();
  await expect(page.getByRole('status')).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'Chaque entreprise, son espace.' }),
  ).toBeVisible();
});

test('production build stays disconnected and contains no synthetic review control', async ({
  page,
}) => {
  await page.goto('http://127.0.0.1:4173/access');
  await expect(
    page.getByRole('heading', { name: 'Bienvenue dans votre espace.' }),
  ).toBeVisible();
  await expect(
    page.getByRole('button', { name: 'Continuer avec Keycloak' }),
  ).toBeDisabled();
  await expect(
    page.getByRole('button', { name: 'Ouvrir la revue locale' }),
  ).toHaveCount(0);
  await page.goto('http://127.0.0.1:4173/workspace');
  await expect(page).toHaveURL('http://127.0.0.1:4173/access');
});

test('manager has explicit resources without billing or platform permissions', async ({
  page,
}) => {
  await enter(page, 'Manager · entreprise A');
  await expect(
    page.getByRole('link', { name: 'Ouvrir l’entreprise · Comptoir Atlas' }),
  ).toHaveCount(0);
  await page
    .getByRole('link', { name: 'Ouvrir l’entreprise · Maison Safran' })
    .click();
  await expect(
    page.getByRole('heading', { name: '1 restaurant accessible' }),
  ).toBeVisible();
  await expect(
    page.getByRole('link', {
      name: 'Ouvrir le restaurant · Alger · Les Jardins',
    }),
  ).toHaveCount(0);
  await expect(page.getByText('Abonnement & paiements')).toHaveCount(0);
});

test('minimum 360px Arabic layout keeps navigation and cards inside the viewport', async ({
  page,
}) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await enter(page);
  await page
    .getByRole('combobox', {
      name: /Langue de l.interface|Interface language|لغة الواجهة/,
    })
    .click();
  await page.getByRole('option', { name: 'العربية — AR' }).click();
  await expect(
    page.getByRole('heading', { name: 'لكل مؤسسة مساحتها.' }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.getByRole('button', { name: 'فتح القائمة' }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  const bounds = await page.getByRole('dialog').boundingBox();
  expect(bounds?.width).toBeLessThanOrEqual(360);
  await page.keyboard.press('Escape');
});

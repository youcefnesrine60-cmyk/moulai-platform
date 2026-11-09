// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Actual local browser workflow over the explicitly dated financial fixture; no real bank transaction or fake API transport.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {
  launch,
  login,
  root,
  request,
  checked,
} from './operationalHarness.mjs';
const output = path.join(root, 'artifacts/operational-o3-20261108');
const enrollment = JSON.parse(
  fs.readFileSync(
    path.join(output, 'finance-enrollment/enrollment-journey.json'),
    'utf8',
  ),
);
assert.equal(enrollment.status, 'PASS');
const clock = JSON.parse(
  fs.readFileSync(path.join(output, 'finance-clock-fixture.json'), 'utf8'),
);
const { organization_id: organization, restaurant_id: restaurant } =
  enrollment.completed;
assert.equal(clock.restaurant_id, restaurant);
const browser = await launch(),
  checks = [];
let phase = 'login',
  owner;
function record(status, extra = {}) {
  fs.writeFileSync(
    path.join(output, 'saas-payment-journey.json'),
    JSON.stringify(
      {
        status,
        phase,
        checks,
        clockFixture: 'finance-clock-fixture.json',
        syntheticFundsOnly: true,
        externalBankOperation: false,
        externalCalls: false,
        ...extra,
      },
      null,
      2,
    ),
  );
}
async function post(page, suffix, click) {
  const pending = page.waitForResponse(
    (response) =>
      response.request().method() === 'POST' &&
      new URL(response.url()).pathname.endsWith(suffix),
  );
  await click();
  const response = await pending;
  const body = await response.json();
  assert.equal(
    response.status(),
    200,
    body.detail?.code ?? 'Expected successful local operation',
  );
  return body;
}
function decimal(value) {
  return String(value)
    .replace(/(\.\d*?[1-9])0+$/, '$1')
    .replace(/\.0+$/, '');
}
try {
  owner = await login(browser, 'billing-scenario');
  phase = 'main-workspace-navigation';
  await owner
    .getByRole('link', { name: /LOCAL-FAKE — Société de recette O4 paiement/ })
    .click();
  phase = 'restaurant-selection';
  await owner.getByRole('link', { name: /LOCAL-FAKE — Restaurant O4/ }).click();
  phase = 'offer-navigation';
  await owner
    .getByRole('link', { name: 'Mon offre SaaS', exact: true })
    .click();
  const available = checked(
    await request(
      owner,
      `/api/web/organizations/${organization}/restaurants/${restaurant}/offer`,
    ),
  );
  const basic = available.plans.find((plan) => plan.code === 'basic');
  assert.ok(basic);
  phase = 'plan-selection';
  await owner
    .getByRole('combobox', { name: /^Formule/ })
    .selectOption(String(basic.id));
  phase = 'country-aware-simulation';
  const pricing = await post(owner, '/offer/simulation', () =>
    owner
      .getByRole('button', { name: 'Simuler sans souscrire', exact: true })
      .click(),
  );
  assert.equal(pricing.binding_quote, false);
  assert.equal(pricing.pricing.parameters.base_selection.country_code, 'DZ');
  assert.equal(pricing.pricing.parameters.currency, 'DZD');
  checks.push({
    step: 'main-ui-server-simulation',
    country: 'DZ',
    currency: 'DZD',
    base: pricing.pricing.parameters.B,
  });
  const section = owner
    .getByRole('heading', {
      name: 'Abonnement SaaS et justificatifs',
      exact: true,
    })
    .locator('..');
  await section
    .getByRole('combobox', { name: /^Mode de virement manuel/ })
    .selectOption('ccp');
  phase = 'retained-owned-checkout';
  const invoice = await post(owner, '/saas-payments', () =>
    section
      .getByRole('button', {
        name: 'Retenir l’offre et créer la demande de paiement',
        exact: true,
      })
      .click(),
  );
  assert.equal(invoice.status, 'pending');
  assert.equal(
    decimal(invoice.amount),
    decimal(pricing.pricing.final_amount_due),
  );
  const duplicate = await post(owner, '/saas-payments', () =>
    section
      .getByRole('button', {
        name: 'Retenir l’offre et créer la demande de paiement',
        exact: true,
      })
      .click(),
  );
  assert.equal(duplicate.id, invoice.id);
  assert.equal(duplicate.subscription_id, invoice.subscription_id);
  checks.push({
    step: 'retained-quote-and-repeated-checkout',
    payment: invoice.id,
    subscription: invoice.subscription_id,
    amount: invoice.amount,
    duplicate: false,
  });
  record('RUNNING');
  phase = 'upload-does-not-settle';
  const reference = 'LOCAL-FAKE-TRANSFER-O4-' + invoice.id;
  await section
    .getByLabel('Référence du virement fictif', { exact: true })
    .fill(reference);
  await section
    .getByLabel('Justificatif fictif du virement', { exact: true })
    .setInputFiles({
      name: 'LOCAL-FAKE-transfer.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from(
        '%PDF-1.4\nDOCUMENT FICTIF — AUCUN TRANSFERT BANCAIRE REEL — ' +
          reference +
          '\n%%EOF',
      ),
    });
  await section
    .getByRole('checkbox', {
      name: 'Je confirme que ce justificatif est fictif et réservé à cette recette locale.',
      exact: true,
    })
    .check();
  await post(owner, '/receipt', () =>
    section
      .getByRole('button', { name: 'Déposer le justificatif', exact: true })
      .click(),
  );
  const paymentRoot = `/api/web/organizations/${organization}/restaurants/${restaurant}/saas-payments`;
  const waiting = checked(await request(owner, paymentRoot)).find(
    (row) => row.id === invoice.id,
  );
  assert.equal(waiting.status, 'pending');
  assert.equal(waiting.receipt_status, 'pending');
  await owner.screenshot({
    path: path.join(output, 'saas-payment-awaiting-review.png'),
    fullPage: true,
  });
  checks.push({
    step: 'receipt-upload-persisted-without-activation',
    status: 'pending',
  });
  phase = 'distinct-funds-review';
  const countryReviewer = await login(browser, 'country-reviewer');
  const body = {
    decision: 'approve',
    funds_received: true,
    bank_transaction_reference: reference,
    received_amount: invoice.amount,
    received_currency: invoice.currency,
    note: 'Recette fictive uniquement : contrôle indépendant simulé, sans transfert réel.',
  };
  assert.equal(
    (
      await request(
        countryReviewer,
        `/api/web/platform/saas-payments/${invoice.id}/review`,
        body,
      )
    ).status,
    403,
  );
  const reviewer = await login(browser, 'saas-reviewer');
  await reviewer
    .getByRole('link', { name: 'Revue des paiements SaaS', exact: true })
    .click();
  const recordCard = reviewer
    .locator('article')
    .filter({ hasText: reference.replace(/[ ./_-]/g, '').toUpperCase() });
  await recordCard
    .getByLabel('Montant reçu et vérifié', { exact: true })
    .fill(String(invoice.amount));
  await recordCard
    .getByLabel('Devise reçue', { exact: true })
    .fill(invoice.currency);
  await recordCard
    .getByLabel('Référence du virement fictif', { exact: true })
    .fill(reference);
  await recordCard
    .getByLabel('Motif / informations pour la revue', { exact: true })
    .fill(body.note);
  const check = recordCard.getByRole('checkbox', {
    name: 'J’ai vérifié séparément les fonds de cette recette fictive. Aucun mouvement bancaire réel.',
    exact: true,
  });
  assert.equal(await check.isChecked(), false);
  await check.check();
  await post(reviewer, '/review', () =>
    recordCard
      .getByRole('button', {
        name: 'Valider la réception vérifiée et activer',
        exact: true,
      })
      .click(),
  );
  const repeated = checked(
    await request(
      reviewer,
      `/api/web/platform/saas-payments/${invoice.id}/review`,
      body,
    ),
  );
  assert.equal(repeated.review_status, 'approved');
  await reviewer.screenshot({
    path: path.join(output, 'saas-payment-reviewed.png'),
    fullPage: true,
  });
  phase = 'reload-persistence';
  await owner.reload();
  const paid = checked(await request(owner, paymentRoot)).find(
    (row) => row.id === invoice.id,
  );
  assert.equal(paid.status, 'paid');
  assert.equal(paid.receipt_status, 'approved');
  checks.push({
    step: 'authorized-independent-synthetic-funds-review',
    payment: invoice.id,
    repeatedReview: 'same final result',
    receipt: 'approved',
    reloadPersisted: true,
  });
  await owner.screenshot({
    path: path.join(output, 'saas-payment-persisted.png'),
    fullPage: true,
  });
  record('PASS', {
    payment: invoice.id,
    subscription: invoice.subscription_id,
    amount: invoice.amount,
    currency: invoice.currency,
    scope:
      'actual local UI/services with fictitious clock and funds, not bank settlement',
  });
  console.log(
    JSON.stringify({
      status: 'PASS',
      checks: checks.length,
      payment: invoice.id,
      externalBankOperation: false,
    }),
  );
} catch (error) {
  record('FAIL', {
    errorType: error.constructor.name,
    safeStatus: error.safeStatus,
    safeCode: error.safeCode,
  });
  if (owner)
    await owner
      .screenshot({
        path: path.join(output, 'saas-payment-failure.png'),
        fullPage: true,
      })
      .catch(() => {});
  console.error(
    JSON.stringify({
      status: 'FAIL',
      phase,
      type: error.constructor.name,
      safeStatus: error.safeStatus,
      safeCode: error.safeCode,
    }),
  );
  process.exitCode = 1;
} finally {
  await browser.close();
}

// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Resume only the already persisted fictitious invoice; never repeat its receipt upload or create another checkout.
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
const previous = JSON.parse(
  fs.readFileSync(path.join(output, 'saas-payment-journey.json'), 'utf8'),
);
const retained = previous.checks.find(
  (row) => row.step === 'retained-quote-and-repeated-checkout',
);
assert.ok(retained);
assert.ok(
  previous.checks.find(
    (row) => row.step === 'receipt-upload-persisted-without-activation',
  ),
);
const enrollment = JSON.parse(
  fs.readFileSync(
    path.join(output, 'finance-enrollment/enrollment-journey.json'),
    'utf8',
  ),
);
const { organization_id: organization, restaurant_id: restaurant } =
  enrollment.completed;
const browser = await launch();
let phase = 'owner-read',
  active;
const checks = [];
function save(status, extra = {}) {
  fs.writeFileSync(
    path.join(output, 'saas-review-resume.json'),
    JSON.stringify(
      {
        status,
        phase,
        payment: retained.payment,
        checks,
        initialJourney: 'saas-payment-journey.json',
        fictitiousFundsOnly: true,
        bankTransfer: false,
        externalCalls: false,
        ...extra,
      },
      null,
      2,
    ),
  );
}
try {
  const owner = await login(browser, 'billing-scenario');
  active = owner;
  const paymentRoot = `/api/web/organizations/${organization}/restaurants/${restaurant}/saas-payments`;
  const invoice = checked(await request(owner, paymentRoot)).find(
    (row) => row.id === retained.payment,
  );
  assert.ok(invoice);
  assert.equal(invoice.status, 'pending');
  assert.equal(invoice.receipt_status, 'pending');
  const reference = 'LOCAL-FAKE-TRANSFER-O4-' + invoice.id;
  const body = {
    decision: 'approve',
    funds_received: true,
    bank_transaction_reference: reference,
    received_amount: invoice.amount,
    received_currency: invoice.currency,
    note: 'Recette fictive uniquement : contrôle indépendant simulé, sans transfert réel.',
  };
  phase = 'country-reviewer-direct-api-refused';
  const countryReviewer = await login(browser, 'country-reviewer');
  active = countryReviewer;
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
  checks.push({ step: 'country-reviewer-cannot-confirm-funds', status: 403 });
  save('RUNNING');
  phase = 'payments-reviewer-login';
  const reviewer = await login(browser, 'saas-reviewer');
  active = reviewer;
  phase = 'payments-reviewer-main-link';
  await reviewer
    .getByRole('link', { name: 'Revue des paiements SaaS', exact: true })
    .click();
  await reviewer.waitForURL('**/platform/saas-payments');
  const queue = checked(
    await request(reviewer, '/api/web/platform/saas-payments'),
  );
  checks.push({
    step: 'actual-review-route',
    path: new URL(reviewer.url()).pathname,
    found: queue.some((row) => row.id === invoice.id),
    referenceMatches:
      queue.find((row) => row.id === invoice.id)?.reference === reference,
  });
  save('RUNNING');
  phase = 'receipt-review-form';
  const storedReference = queue.find((row) => row.id === invoice.id)?.reference;
  assert.equal(
    storedReference,
    reference.replace(/[ ./_-]/g, '').toUpperCase(),
  );
  const article = reviewer
    .locator('article')
    .filter({ hasText: storedReference });
  await article.waitFor();
  assert.equal(await article.count(), 1);
  await article
    .getByLabel('Montant reçu et vérifié', { exact: true })
    .fill(String(invoice.amount));
  await article
    .getByLabel('Devise reçue', { exact: true })
    .fill(invoice.currency);
  await article
    .getByLabel('Référence du virement fictif', { exact: true })
    .fill(reference);
  await article
    .getByLabel('Motif / informations pour la revue', { exact: true })
    .fill(body.note);
  const verification = article.getByRole('checkbox', {
    name: 'J’ai vérifié séparément les fonds de cette recette fictive. Aucun mouvement bancaire réel.',
    exact: true,
  });
  assert.equal(await verification.isChecked(), false);
  await verification.check();
  await reviewer.screenshot({
    path: path.join(output, 'saas-funds-review-before-confirm.png'),
    fullPage: true,
  });
  phase = 'explicit-funds-review';
  const pending = reviewer.waitForResponse(
    (response) =>
      response.request().method() === 'POST' &&
      new URL(response.url()).pathname.endsWith(
        `/saas-payments/${invoice.id}/review`,
      ),
  );
  await article
    .getByRole('button', {
      name: 'Valider la réception vérifiée et activer',
      exact: true,
    })
    .click();
  const response = await pending;
  const responseBody = await response.json();
  if (response.status() !== 200)
    throw Object.assign(new Error('Local review rejected'), {
      safeStatus: response.status(),
      safeCode: responseBody.detail?.code,
    });
  phase = 'idempotent-review-and-reload';
  assert.equal(
    checked(
      await request(
        reviewer,
        `/api/web/platform/saas-payments/${invoice.id}/review`,
        body,
      ),
    ).review_status,
    'approved',
  );
  const paid = checked(await request(owner, paymentRoot)).find(
    (row) => row.id === invoice.id,
  );
  assert.equal(paid.status, 'paid');
  assert.equal(paid.receipt_status, 'approved');
  await owner.goto(
    `https://127.0.0.1:5180/workspace/organizations/${organization}/restaurants/${restaurant}/offer`,
  );
  await owner
    .getByText('Réception vérifiée', { exact: false })
    .first()
    .waitFor();
  await owner.reload();
  await owner
    .getByText('Réception vérifiée', { exact: false })
    .first()
    .waitFor();
  await owner.screenshot({
    path: path.join(output, 'saas-payment-persisted.png'),
    fullPage: true,
  });
  await reviewer.screenshot({
    path: path.join(output, 'saas-payment-reviewed.png'),
    fullPage: true,
  });
  checks.push({
    step: 'main-ui-explicit-synthetic-funds-review',
    status: 'paid',
    receipt: 'approved',
    repeatedReview: 'same result',
    persistedAfterReload: true,
  });
  save('PASS', {
    subscription: retained.subscription,
    amount: invoice.amount,
    currency: invoice.currency,
  });
  console.log(
    JSON.stringify({
      status: 'PASS',
      checks: checks.length,
      payment: invoice.id,
    }),
  );
} catch (error) {
  save('FAIL', {
    errorType: error.constructor.name,
    safeStatus: error.safeStatus,
    safeCode: error.safeCode,
    path: active ? new URL(active.url()).pathname : null,
  });
  if (active)
    await active
      .screenshot({
        path: path.join(output, 'saas-review-resume-failure.png'),
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

// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Continue the same UI-created owner's recipe. No date rewrite or bank operation.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { login, origin, request, checked } from './operationalHarness.mjs';
import { redactLocalMessage } from '../src/shared/access/logSafety.ts';
import { roundedCents } from './exactAcceptanceMoney.mjs';

async function submit(page, suffix, action) {
  const pending = page.waitForResponse(
    (r) =>
      r.request().method() === 'POST' &&
      new URL(r.url()).pathname.endsWith(suffix),
  );
  await action();
  const response = await pending;
  const result = await response.json();
  assert.equal(
    response.status(),
    200,
    result.detail?.code ?? 'Expected successful local operation',
  );
  return result;
}
function decimalUnits(value) {
  const match = /^(\d+)(?:\.(\d{0,8}))?$/.exec(String(value));
  assert(match);
  return (
    BigInt(match[1]) * 100000000n + BigInt((match[2] ?? '').padEnd(8, '0'))
  );
}

export async function completeSaasRecipe({
  browser,
  owner,
  finalized,
  output,
}) {
  const { organization_id: organization, restaurant_id: restaurant } =
    finalized;
  const root = `/api/web/organizations/${organization}/restaurants/${restaurant}`;
  const checks = [];
  let phase = 'initial-offer';
  const record = (status, extra = {}) =>
    fs.writeFileSync(
      path.join(output, 'same-owner-saas.json'),
      JSON.stringify(
        {
          status,
          phase,
          organization,
          restaurant,
          checks,
          syntheticFundsOnly: true,
          trialDateFixture: fs.existsSync(
            path.join(output, 'finance-clock-fixture.json'),
          ),
          ...extra,
        },
        null,
        2,
      ),
    );
  record('RUNNING');
  try {
    for (const cycle of ['initial-payment', 'renewal']) {
      phase = cycle + '-offer';
      await owner.goto(origin + '/api/web/auth/login');
      await owner.waitForURL('**/workspace');
      await owner.goto(
        origin +
          `/workspace/organizations/${organization}/restaurants/${restaurant}/offer`,
      );
      const available = checked(await request(owner, root + '/offer'));
      const basic = available.plans.find((x) => x.code === 'basic');
      assert(basic, 'Approved basic configuration required');
      await owner
        .getByRole('combobox', { name: /^Formule/ })
        .selectOption(String(basic.id));
      const quote = await submit(owner, '/offer/simulation', () =>
        owner
          .getByRole('button', { name: 'Simuler sans souscrire', exact: true })
          .click(),
      );
      assert.equal(quote.pricing.parameters.base_selection.country_code, 'DZ');
      assert.equal(
        decimalUnits(quote.pricing.parameters.B),
        3000n * 100000000n,
      );
      assert.equal(
        String(quote.pricing.parameters.payment_adjustment_rate),
        '-0.02',
      );
      const expectedCents = roundedCents(
        quote.pricing.exact.final_price,
        98n,
        100n,
      );
      assert.equal(
        roundedCents(quote.pricing.exact.final_amount_due),
        expectedCents,
      );
      const panel = owner
        .getByRole('heading', {
          name: 'Abonnement SaaS et justificatifs',
          exact: true,
        })
        .locator('..');
      await panel
        .getByRole('combobox', { name: /^Mode de virement manuel/ })
        .selectOption('ccp');
      const retain = () =>
        panel
          .getByRole('button', {
            name: 'Retenir l’offre et créer la demande de paiement',
            exact: true,
          })
          .click();
      const invoice = await submit(owner, '/saas-payments', retain);
      const repeated = await submit(owner, '/saas-payments', retain);
      assert.equal(repeated.id, invoice.id);
      assert.equal(
        roundedCents(invoice.amount),
        roundedCents(quote.pricing.exact.final_amount_due),
      );
      const reference = `LOCAL-FAKE-20261110-${cycle}-${invoice.id}`;
      await panel
        .getByLabel('Référence du virement fictif', { exact: true })
        .fill(reference);
      await panel
        .getByLabel('Justificatif fictif du virement', { exact: true })
        .setInputFiles({
          name: 'LOCAL-FAKE-TRANSFER.pdf',
          mimeType: 'application/pdf',
          buffer: Buffer.from(
            '%PDF-1.4\nDOCUMENT FICTIF — AUCUN TRANSFERT REEL — ' +
              reference +
              '\n%%EOF',
          ),
        });
      await panel
        .getByRole('checkbox', {
          name: 'Je confirme que ce justificatif est fictif et réservé à cette recette locale.',
          exact: true,
        })
        .check();
      await submit(owner, '/receipt', () =>
        panel
          .getByRole('button', { name: 'Déposer le justificatif', exact: true })
          .click(),
      );
      const list = () => request(owner, root + '/saas-payments').then(checked);
      const pending = (await list()).find((x) => x.id === invoice.id);
      assert.equal(pending.status, 'pending');
      assert.equal(pending.receipt_status, 'pending');
      const body = {
        decision: 'approve',
        funds_received: true,
        bank_transaction_reference: reference,
        received_amount: invoice.amount,
        received_currency: invoice.currency,
        note: 'LOCAL-FAKE : contrôle distinct de fonds fictifs, aucun mouvement bancaire.',
      };
      assert.equal(
        (
          await request(
            owner,
            `/api/web/platform/saas-payments/${invoice.id}/review`,
            body,
          )
        ).status,
        403,
      );
      const countryReviewer = await login(browser, 'country-reviewer');
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
      await countryReviewer.context().close();
      const reviewer = await login(browser, 'saas-reviewer');
      await reviewer
        .getByRole('link', { name: 'Revue des paiements SaaS', exact: true })
        .click();
      const card = reviewer.locator(`[data-saas-payment-id="${invoice.id}"]`);
      await card.waitFor();
      await card
        .getByLabel('Montant reçu et vérifié', { exact: true })
        .fill(String(invoice.amount));
      await card
        .getByLabel('Devise reçue', { exact: true })
        .fill(invoice.currency);
      await card
        .getByLabel('Référence du virement fictif', { exact: true })
        .fill(reference);
      await card
        .getByLabel('Motif / informations pour la revue', { exact: true })
        .fill(body.note);
      const funds = card.getByRole('checkbox', {
        name: 'J’ai vérifié séparément les fonds de cette recette fictive. Aucun mouvement bancaire réel.',
        exact: true,
      });
      assert.equal(await funds.isChecked(), false);
      await funds.check();
      await submit(reviewer, '/review', () =>
        card
          .getByRole('button', {
            name: 'Valider la réception vérifiée et activer',
            exact: true,
          })
          .click(),
      );
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
      await owner.reload();
      const paid = (await list()).find((x) => x.id === invoice.id);
      assert.equal(paid.status, 'paid');
      assert.equal(paid.receipt_status, 'approved');
      checks.push({
        cycle,
        payment: invoice.id,
        subscription: invoice.subscription_id,
        amount: invoice.amount,
        currency: invoice.currency,
        B: quote.pricing.parameters.B,
        prePayment: quote.pricing.exact.final_price,
        rate: quote.pricing.parameters.payment_adjustment_rate,
        repeatCheckoutSame: true,
        receiptDoesNotActivate: true,
        distinctReviewer: true,
        repeatApprovalSame: true,
        persistedAfterReload: true,
      });
      await owner.screenshot({
        path: path.join(output, cycle + '-persisted.png'),
        fullPage: true,
      });
      await reviewer.context().close();
      record('RUNNING');
    }
    record('PASS');
  } catch (error) {
    record('FAIL', {
      errorType: error.constructor.name,
      message: redactLocalMessage(error.message),
    });
    throw error;
  }
}

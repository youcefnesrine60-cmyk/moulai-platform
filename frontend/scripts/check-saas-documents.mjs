// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Real local browser sessions and O5 persistence; no intercepted business replies, paid provider or real bank operation.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import AxeBuilder from '@axe-core/playwright';
import {
  launch,
  login,
  newContext,
  root,
  origin,
  request,
  checked,
} from './operationalHarness.mjs';

const output = path.join(root, 'artifacts/saas-documents-20261111/browser');
fs.mkdirSync(output, { recursive: true });
const account = JSON.parse(
  fs.readFileSync(
    path.join(
      root,
      'artifacts/operational-local/3fb5f85a6cc94868acaf7d95b3777a16/private/saas-document-account.json',
    ),
    'utf8',
  ),
);
assert.equal(account.status, 'completed');
const browser = await launch(),
  checks = [],
  captures = [];
let phase = 'local-authentication',
  owner;
function record(status, extra = {}) {
  fs.writeFileSync(
    path.join(output, 'journey.json'),
    JSON.stringify(
      {
        status,
        phase,
        checks,
        captures,
        externalCalls: false,
        realBankFunds: false,
        physicalPhoneScan: 'NOT TESTED',
        ...extra,
      },
      null,
      2,
    ),
  );
}
async function posted(page, suffix, action) {
  const pending = page.waitForResponse(
    (response) =>
      response.request().method() === 'POST' &&
      new URL(response.url()).pathname.endsWith(suffix),
  );
  await action();
  const response = await pending;
  const result = await response.json();
  assert.equal(
    response.status(),
    200,
    result?.detail?.code ?? 'Document command failed',
  );
  return result;
}
try {
  owner = await login(browser, 'billing-scenario');
  const dossier = checked(await request(owner, '/api/web/enrollment'));
  assert.equal(dossier.status, 'completed');
  const api = `/api/web/organizations/${dossier.organization_id}/restaurants/${dossier.restaurant_id}/saas-payments`;
  const payments = checked(await request(owner, api));
  const payment = payments.find(
    (row) => row.status === 'paid' && row.receipt_status === 'approved',
  );
  assert(payment, 'A previously verified local synthetic payment is required');
  const initial = checked(
    await request(owner, `${api}/${payment.id}/documents`),
  );
  assert.equal(
    initial.length,
    0,
    'Do not automatically repeat an already performed documentary recipe',
  );
  phase = 'owner-main-interface-navigation';
  await owner.goto(origin + '/workspace');
  await owner
    .locator(
      `a[href="/workspace/organizations/${dossier.organization_id}/restaurants"]`,
    )
    .first()
    .click();
  await owner
    .locator(
      `a[href="/workspace/organizations/${dossier.organization_id}/restaurants/${dossier.restaurant_id}"]`,
    )
    .first()
    .click();
  await owner
    .getByRole('link', { name: 'Mon offre SaaS', exact: true })
    .click();
  const sheetPath = `/workspace/saas-documents/${dossier.organization_id}/${dossier.restaurant_id}/${payment.id}`;
  await owner.locator(`a[href="${sheetPath}"]`).click();
  await owner
    .getByText(
      'Aucun document définitif émis. La consultation du paiement ne vaut pas émission.',
      { exact: true },
    )
    .waitFor();
  await owner.screenshot({
    path: path.join(output, 'owner-unissued-fr.png'),
    fullPage: true,
  });
  checks.push({
    step: 'main-interface-to-owned-payment-document',
    issued: false,
  });

  phase = 'independent-platform-documentary-authority';
  const adminContext = await newContext(browser),
    admin = await adminContext.newPage();
  await admin.goto(origin + '/access');
  await admin
    .getByRole('button', { name: 'Se connecter', exact: true })
    .click();
  await admin.locator('#username').fill(account.username);
  await admin.locator('#password').fill(account.password);
  await admin.locator('#kc-login').click();
  await admin.waitForURL(origin + '/platform');
  const session = checked(await request(admin, '/api/web/session'));
  assert.deepEqual(session.platformPermissions, [
    'subscriptions.documents.invalidate',
    'subscriptions.documents.issue',
  ]);
  assert.equal(
    (await request(admin, '/api/web/platform/saas-payments')).status,
    403,
  );
  await admin
    .getByRole('link', { name: 'Documents d’abonnement', exact: true })
    .first()
    .click();
  const row = admin.locator(`[data-saas-document-payment="${payment.id}"]`);
  const issued = await posted(
    admin,
    `/saas-payments/${payment.id}/documents`,
    () =>
      row
        .getByRole('button', { name: 'Émettre le document', exact: true })
        .click(),
  );
  assert.equal(issued.state, 'valid');
  assert.equal(issued.content.amount, payment.amount);
  assert.equal(issued.content.currency, payment.currency);
  assert.equal(issued.content.synthetic, true);
  assert.equal(
    new URL(issued.verification_url).pathname,
    '/verify-saas-document',
  );
  assert.equal(
    checked(
      await request(
        admin,
        `/api/web/platform/saas-payments/${payment.id}/documents`,
        {},
      ),
    ).id,
    issued.id,
  );
  checks.push({
    step: 'actual-Keycloak-explicit-document-grants-and-idempotent-emission',
    document: issued.id,
    payment: payment.id,
    paymentsReview: false,
  });

  phase = 'direct-api-permission-and-scope-refusals';
  assert.equal(
    (
      await request(
        owner,
        `/api/web/platform/saas-payments/${payment.id}/documents`,
        {},
      )
    ).status,
    403,
  );
  const paymentReviewer = await login(browser, 'saas-reviewer');
  assert.equal(
    (
      await request(
        paymentReviewer,
        `/api/web/platform/saas-payments/${payment.id}/documents`,
        {},
      )
    ).status,
    403,
  );
  const foreign = await login(browser, 'owner-b');
  assert.equal(
    (await request(foreign, `${api}/${payment.id}/documents`)).status,
    403,
  );
  await foreign.context().close();
  await paymentReviewer.context().close();
  checks.push({
    step: 'owner-payment-reviewer-and-foreign-company-refused',
    status: 403,
  });

  phase = 'owner-reload-print-and-language-review';
  await owner.reload();
  await owner
    .getByRole('heading', { name: 'Document SaaS émis', exact: true })
    .waitFor();
  const retained = checked(
    await request(owner, `${api}/${payment.id}/documents`),
  );
  assert.equal(retained[0].reference, issued.reference);
  for (const locale of ['fr', 'en', 'ar']) {
    await owner.evaluate(
      (locale) => localStorage.setItem('moulai.locale', locale),
      locale,
    );
    await owner.reload();
    await owner.locator('[data-saas-printable] img').first().waitFor();
    await owner.evaluate(() => document.fonts.ready);
    for (const theme of ['light', 'dark'])
      for (const [device, viewport] of Object.entries({
        desktop: { width: 1440, height: 900 },
        mobile: { width: 390, height: 844 },
      })) {
        await owner.setViewportSize(viewport);
        await owner.evaluate(
          (theme) => window.moulaiTheme.choose(theme),
          theme,
        );
        const facts = await owner.evaluate(() => ({
          rtl: document.documentElement.dir,
          horizontalOverflow: document.documentElement.scrollWidth > innerWidth,
          visibleKeys: /saasDoc\.|quality\.|documents\./.test(
            document.body.innerText,
          ),
        }));
        assert.equal(facts.horizontalOverflow, false);
        assert.equal(facts.visibleKeys, false);
        assert.equal(facts.rtl, locale === 'ar' ? 'rtl' : 'ltr');
        const file = `owner-${locale}-${theme}-${device}.png`;
        await owner.screenshot({
          path: path.join(output, file),
          fullPage: true,
        });
        const accessibility = await new AxeBuilder({ page: owner }).analyze();
        assert.deepEqual(
          accessibility.violations.map((item) => item.id),
          [],
        );
        captures.push({
          file,
          locale,
          theme,
          device,
          ...facts,
          axeViolations: 0,
          incomplete: accessibility.incomplete.map((item) => item.id),
        });
      }
    await owner.setViewportSize({ width: 1440, height: 900 });
    await owner.pdf({
      path: path.join(output, `invoice-${locale}.pdf`),
      format: 'A4',
      preferCSSPageSize: true,
      printBackground: true,
      tagged: true,
    });
  }
  checks.push({
    step: 'owned-reload-12-actual-captures-and-3-PDF-exports',
    amount: payment.amount,
    currency: payment.currency,
    frozenReference: true,
    independentQrDecode: 'NOT PERFORMED',
  });

  phase = 'public-minimal-verification';
  const publicContext = await newContext(browser),
    publicPage = await publicContext.newPage();
  await publicPage.goto(issued.verification_url);
  await publicPage
    .getByRole('heading', { name: 'Document valide', exact: true })
    .waitFor();
  const valid = checked(
    await request(publicPage, '/api/web/saas-documents/verify', {
      reference: issued.reference,
    }),
  );
  assert.deepEqual(Object.keys(valid).sort(), [
    'issued_at',
    'issuer',
    'reference',
    'state',
  ]);
  assert.equal(
    checked(
      await request(publicPage, '/api/web/saas-documents/verify', {
        reference: 'A'.repeat(43),
      }),
    ).state,
    'unknown',
  );
  checks.push({
    step: 'minimal-distinct-reader-no-identity-or-financial-disclosure',
    fields: Object.keys(valid),
  });

  phase = 'explicit-invalidation-through-form';
  await row
    .getByLabel('Motif obligatoire', { exact: true })
    .fill('RECETTE LOCALE — invalidation documentaire sans effet financier.');
  await row.getByRole('checkbox').check();
  const invalidated = await posted(
    admin,
    `/saas-documents/${issued.id}/invalidate`,
    () =>
      row
        .getByRole('button', { name: 'Invalider ce document', exact: true })
        .click(),
  );
  assert.equal(invalidated.state, 'invalidated');
  assert.deepEqual(invalidated.content, issued.content);
  await publicPage.reload();
  await publicPage
    .getByRole('heading', {
      name: 'Document invalidé — conserver l’original',
      exact: true,
    })
    .waitFor();
  await publicPage.screenshot({
    path: path.join(output, 'verification-invalidated-fr.png'),
    fullPage: true,
  });
  const after = checked(await request(owner, api)).find(
    (value) => value.id === payment.id,
  );
  assert.deepEqual(after, payment);
  checks.push({
    step: 'persisted-invalidation-public-reader-and-financial-history-preserved',
    paymentUnchanged: true,
    refunds: 0,
    subscriptionMutations: 0,
  });
  record('PASS', {
    paymentId: payment.id,
    documentId: issued.id,
    organization: dossier.organization_id,
    restaurant: dossier.restaurant_id,
    PDFs: 'Exported before deliberate invalidation; their QR now reports invalidated.',
  });
  console.log(
    JSON.stringify({
      status: 'PASS',
      checks: checks.length,
      captures: captures.length,
    }),
  );
} catch (error) {
  record('FAIL', {
    errorType: error.constructor.name,
    safeCode: error.safeCode,
  });
  if (owner)
    await owner
      .screenshot({ path: path.join(output, 'failure.png'), fullPage: true })
      .catch(() => {});
  console.error(
    JSON.stringify({
      status: 'FAIL',
      phase,
      type: error.constructor.name,
      safeCode: error.safeCode,
    }),
  );
  process.exitCode = 1;
} finally {
  await browser.close();
}

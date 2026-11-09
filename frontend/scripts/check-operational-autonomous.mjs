// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Real local Keycloak, real browser controls and persisted O4 services. No fake network responses or provider IA calls.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {
  launch,
  login,
  origin,
  root,
  request,
  checked,
} from './operationalHarness.mjs';
import { prepareOwner } from './autonomousEntry.mjs';

const financeScenario = process.argv.includes('--finance-scenario');
const output = path.join(
  root,
  'artifacts/operational-followup-20261109/autonomous',
  ...(financeScenario ? ['finance-enrollment'] : []),
);
fs.mkdirSync(output, { recursive: true });
const browser = await launch(),
  checks = [],
  captures = [];
let phase = 'login',
  owner;
function persist(status, extra = {}) {
  fs.writeFileSync(
    path.join(output, 'enrollment-journey.json'),
    JSON.stringify(
      {
        status,
        phase,
        checks,
        captures,
        externalCalls: false,
        notifications: false,
        actualBankFunds: false,
        ...extra,
      },
      null,
      2,
    ),
  );
}
async function submitted(page, pathSuffix, action, expected = 200) {
  const pending = page.waitForResponse(
    (response) =>
      response.request().method() === 'POST' &&
      new URL(response.url()).pathname.endsWith(pathSuffix),
  );
  await action();
  const response = await pending;
  const data = response.status() === 204 ? null : await response.json();
  assert.equal(
    response.status(),
    expected,
    typeof data?.detail?.code === 'string'
      ? data.detail.code
      : 'HTTP status mismatch',
  );
  return data;
}
try {
  owner = await prepareOwner(browser);
  phase = 'main-interface-entry';
  await owner
    .getByRole('link', {
      name: 'Créer mon entreprise et mon premier établissement',
      exact: true,
    })
    .click();
  await owner.waitForURL('**/workspace/enrollment');
  let dossier = checked(await request(owner, '/api/web/enrollment'));
  if (!dossier) {
    phase = 'create-dossier-through-form';
    for (const [name, value] of Object.entries({
      company_name: financeScenario
        ? 'LOCAL-FAKE — Société de recette O4 paiement'
        : 'LOCAL-FAKE — Société de recette O4',
      legal_entity_reference: financeScenario
        ? 'LOCAL-FAKE-O4-FINANCE'
        : 'LOCAL-FAKE-O4-ENTITY',
      full_name: 'Propriétaire fictif O4',
      phone: '0000000000',
      email: 'o4-owner@moulai.local.invalid',
      restaurant_name: 'LOCAL-FAKE — Restaurant O4',
      branch_name: 'LOCAL-FAKE — Première succursale',
    }))
      await owner.locator(`input[name="${name}"]`).fill(value);
    dossier = await submitted(owner, '/enrollment', () =>
      owner
        .getByRole('button', { name: 'Enregistrer le dossier', exact: true })
        .click(),
    );
  }
  assert.notEqual(
    dossier.status,
    'completed',
    'This driver must not silently repeat an already completed acceptance journey',
  );
  checks.push({
    step: 'main-access-authenticated-dossier',
    organization: dossier.organization_id,
    persisted: true,
  });
  persist('RUNNING');
  phase = 'documents-in-three-languages';
  for (const locale of financeScenario ? [] : ['fr', 'en', 'ar']) {
    await owner.evaluate(
      (locale) => localStorage.setItem('moulai.locale', locale),
      locale,
    );
    await owner.reload();
    await owner.waitForFunction(
      (locale) => document.documentElement.lang === locale,
      locale,
    );
    const names = {
      fr: 'Afficher et enregistrer la présentation des documents',
      en: 'Display and record document presentation',
      ar: 'عرض الوثائق وتسجيل الاطلاع عليها',
    };
    await submitted(owner, '/documents/present', () =>
      owner.getByRole('button', { name: names[locale], exact: true }).click(),
    );
    for (const theme of ['light', 'dark'])
      for (const [viewport, size] of Object.entries({
        desktop: { width: 1440, height: 1000 },
        mobile: { width: 390, height: 844 },
      })) {
        await owner.setViewportSize(size);
        await owner.evaluate(
          (theme) => window.moulaiTheme.choose(theme),
          theme,
        );
        await owner.evaluate(() => document.fonts.ready);
        const facts = await owner.evaluate(() => ({
          dir: document.documentElement.dir,
          overflow: document.documentElement.scrollWidth > innerWidth,
          keys:
            document.body.innerText.match(
              /\b(?:o3|integration)\.[a-zA-Z_]+/g,
            ) || [],
        }));
        assert.equal(facts.dir, locale === 'ar' ? 'rtl' : 'ltr');
        assert.equal(facts.overflow, false);
        assert.deepEqual(facts.keys, []);
        const file = `enrollment-${locale}-${theme}-${viewport}.png`;
        await owner.screenshot({
          path: path.join(output, file),
          fullPage: true,
          animations: 'disabled',
        });
        captures.push({ file, locale, theme, viewport, ...facts });
      }
  }
  await owner.evaluate(() => localStorage.setItem('moulai.locale', 'fr'));
  await owner.reload();
  await owner.setViewportSize({ width: 1440, height: 1000 });
  const documents = await submitted(owner, '/documents/present', () =>
    owner
      .getByRole('button', {
        name: 'Afficher et enregistrer la présentation des documents',
        exact: true,
      })
      .click(),
  );
  const invalid = await request(
    owner,
    '/api/web/enrollment/documents/respond',
    {
      document_id: documents[0].id,
      version: 'UNKNOWN',
      sha256: documents[0].sha256,
      locale: 'fr',
      action: 'accepted',
    },
  );
  assert.equal(invalid.status, 409);
  checks.push({ step: 'unknown-document-version-direct-api', status: 409 });
  for (const label of [
    'J’accepte ces conditions fictives de recette',
    'J’ai pris connaissance de cette information fictive',
  ]) {
    const input = owner.getByRole('checkbox', { name: label, exact: true });
    if (await input.isDisabled()) {
      assert.equal(await input.isChecked(), true);
      continue;
    }
    assert.equal(await input.isChecked(), false);
    await input.check();
    await submitted(
      owner,
      '/documents/respond',
      () =>
        input
          .locator('..')
          .locator('..')
          .getByRole('button', { name: 'Enregistrer ce choix', exact: true })
          .click(),
      204,
    ).catch((error) => {
      if (error instanceof SyntaxError) return null;
      throw error;
    });
  }
  const optional = owner.getByRole('radio', { name: 'Refuser', exact: true });
  assert.equal(await optional.isChecked(), false);
  await optional.check();
  const optionalForm = optional.locator('..').locator('..').locator('..');
  await optionalForm
    .getByRole('button', { name: 'Enregistrer ce choix', exact: true })
    .click();
  await owner
    .getByRole('button', { name: 'Choix enregistré', exact: true })
    .nth(2)
    .waitFor();
  checks.push({
    step: 'separate-contract-information-and-optional-refusal',
    preselected: false,
  });
  phase = 'country-declaration';
  await owner.getByTestId('billing-country').fill('DZ');
  await owner
    .getByLabel('Motif / informations pour la revue', { exact: true })
    .fill('Pays d’établissement fictif pour cette recette locale uniquement.');
  await owner
    .getByLabel(
      'Justificatif officiel fictif (PDF, PNG ou JPEG, 2 Mio maximum)',
      { exact: true },
    )
    .setInputFiles({
      name: 'LOCAL-FAKE-establishment.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from(
        `%PDF-1.4\nDOCUMENT FICTIF DE RECETTE — ${dossier.legal_entity_reference} — ADRESSE FICTIVE EN ALGERIE\n%%EOF`,
      ),
    });
  await owner
    .getByRole('checkbox', {
      name: 'Je confirme que ce justificatif est fictif et réservé à cette recette locale.',
      exact: true,
    })
    .check();
  let state = checked(
    await request(
      owner,
      `/api/web/organizations/${dossier.organization_id}/billing-country`,
    ),
  );
  if (!state.requests.some((row) => row.status === 'pending'))
    await submitted(owner, '/billing-country', () =>
      owner
        .getByRole('button', {
          name: 'Soumettre à la validation humaine',
          exact: true,
        })
        .click(),
    );
  state = checked(
    await request(
      owner,
      `/api/web/organizations/${dossier.organization_id}/billing-country`,
    ),
  );
  assert.equal(state.validated_country, null);
  await submitted(
    owner,
    '/enrollment/finalize',
    () =>
      owner
        .getByRole('button', {
          name: 'Finaliser l’inscription et l’essai admissible',
          exact: true,
        })
        .click(),
    409,
  );
  checks.push({ step: 'unvalidated-country-does-not-activate', status: 409 });
  persist('RUNNING');
  phase = 'direct-api-permission-refusals';
  const pricing = await login(browser, 'platform-admin'),
    foreign = await login(browser, 'owner-b');
  const reviewBody = {
    decision: 'approve',
    expected_revision: state.revision,
    justification: 'This should be refused',
    evidence_checked: true,
    same_legal_entity: true,
  };
  assert.equal(
    (
      await request(
        pricing,
        `/api/web/platform/billing-country-requests/${state.requests[0].id}/review`,
        reviewBody,
      )
    ).status,
    403,
  );
  assert.equal(
    (
      await request(
        foreign,
        `/api/web/organizations/${dossier.organization_id}/billing-country`,
      )
    ).status,
    403,
  );
  assert.equal(
    (
      await request(
        foreign,
        `/api/web/billing-country-evidence/${state.requests[0].evidence_id}`,
      )
    ).status,
    403,
  );
  checks.push({
    step: 'pricing-grant-and-foreign-owner-refused',
    directApi: true,
    status: 403,
  });
  phase = 'separate-human-country-review';
  const reviewer = await login(browser, 'country-reviewer');
  await reviewer
    .getByRole('link', {
      name: 'Validation du pays de facturation',
      exact: true,
    })
    .click();
  await reviewer
    .getByText(dossier.company_name + ' · Validation humaine en attente', {
      exact: true,
    })
    .locator('..')
    .getByRole('button', { name: 'Examiner le dossier', exact: true })
    .click();
  await reviewer
    .getByRole('checkbox', {
      name: 'J’ai examiné le document officiel fictif et son adresse d’établissement.',
      exact: true,
    })
    .check();
  await reviewer
    .getByRole('checkbox', {
      name: 'Il s’agit de la même entité juridique.',
      exact: true,
    })
    .check();
  await reviewer
    .getByLabel('Motif / informations pour la revue', { exact: true })
    .fill(
      'Revue humaine simulée explicite du document officiel fictif et de son adresse.',
    );
  await submitted(reviewer, '/review', () =>
    reviewer
      .getByRole('button', { name: 'Approuver le pays', exact: true })
      .click(),
  );
  assert.equal(
    (await request(reviewer, '/api/web/platform/saas-payments')).status,
    403,
  );
  await reviewer.screenshot({
    path: path.join(output, 'country-review-fr-desktop.png'),
    fullPage: true,
  });
  checks.push({
    step: 'country-reviewer-distinct-from-pricing-and-payments',
    realLocalAuthentication: true,
  });
  phase = 'atomic-enrollment-finalization';
  const finalized = await submitted(owner, '/enrollment/finalize', () =>
    owner
      .getByRole('button', {
        name: 'Finaliser l’inscription et l’essai admissible',
        exact: true,
      })
      .click(),
  );
  assert.equal(finalized.status, 'completed');
  const repeated = checked(
    await request(owner, '/api/web/enrollment/finalize', {}),
  );
  assert.equal(repeated.restaurant_id, finalized.restaurant_id);
  await owner.reload();
  assert.equal(
    checked(await request(owner, '/api/web/enrollment')).status,
    'completed',
  );
  await owner
    .getByRole('link', { name: 'Ouvrir mon espace', exact: true })
    .click();
  await owner.waitForURL('**/workspace');
  await owner
    .getByRole('link', {
      name: new RegExp('LOCAL-FAKE — Société de recette O4'),
    })
    .waitFor();
  await owner.screenshot({
    path: path.join(output, 'enrollment-completed-workspace.png'),
    fullPage: true,
  });
  checks.push({
    step: 'completed-company-first-establishment-trial',
    organization: finalized.organization_id,
    restaurant: finalized.restaurant_id,
    repeatedSameResult: true,
    reloadPersisted: true,
  });
  persist('PASS', {
    companyCreatedByCLI: false,
    completed: finalized,
    scope:
      'authenticated local enrollment, country and documents; paid subscription journey assessed separately',
  });
  console.log(
    JSON.stringify({
      status: 'PASS',
      checks: checks.length,
      captures: captures.length,
      companyCreatedByCLI: false,
    }),
  );
} catch (error) {
  persist('FAIL', {
    errorType: error.constructor.name,
    sourceLocation: error.stack
      ?.split('\n')
      .filter((line) => line.includes('autonomousEntry.mjs')),
    safeStatus: error.safeStatus,
    safeCode: error.safeCode,
  });
  if (owner)
    await owner
      .screenshot({
        path: path.join(output, 'enrollment-failure.png'),
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

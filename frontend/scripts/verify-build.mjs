// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import assert from 'node:assert/strict';
import { readdir, readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

/** Reject accidental inclusion of known synthetic fixtures in publication output. */
async function verifyBuild() {
  const assets = fileURLToPath(new URL('../dist/assets/', import.meta.url));
  const files = (await readdir(assets)).filter((name) => name.endsWith('.js'));
  assert(files.length > 0, 'Build JavaScript is required.');
  for (const name of files) {
    const source = await readFile(`${assets}/${name}`, 'utf8');
    for (const fixture of [
      'urn:moulai:synthetic-review',
      'Maison Safran',
      'Comptoir Atlas',
      'REV-9201-',
      'Couscous maison',
      'Client de revue 1',
      'IA-REV-',
      'synthetic-visitor-',
      'BILLING-REVIEW-',
      'REGISTRATION-REVIEW-',
      'AUDIT-REVIEW-',
      'PAYMENT-REVIEW-',
      'SYNTHETIC-CCP-NOT-PAYABLE',
      'SYNTHETIC-RIP-NOT-PAYABLE',
    ]) {
      assert(
        !source.includes(fixture),
        `Synthetic fixture detected in ${name}`,
      );
    }
    assert(
      ![
        'syntheticAdapter',
        'restaurantFixtures',
        'managementAdapter',
        'intelligenceAdapter',
        'intelligenceFixtures',
        'officeAdapter',
        'billingFixtures',
      ].some((fixture) => name.includes(fixture)),
      'Synthetic adapter chunk is forbidden.',
    );
  }
  console.info(
    `Verified ${files.length} JavaScript assets: known synthetic fixture data absent.`,
  );
}

await verifyBuild();

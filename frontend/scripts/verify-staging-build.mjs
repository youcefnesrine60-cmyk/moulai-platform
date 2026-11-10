// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Verify the separate authenticated staging artifact without weakening normal build guards.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
const directory = path.resolve(import.meta.dirname, '../staging-dist');
assert.deepEqual(
  JSON.parse(
    fs.readFileSync(path.join(directory, 'staging-build.json'), 'utf8'),
  ),
  { mode: 'staging', syntheticOnly: true, fixtureAdapterIncluded: false },
);
const files = fs
  .readdirSync(path.join(directory, 'assets'))
  .filter((x) => x.endsWith('.js'));
assert(files.length > 0);
const forbidden = [
  'urn:moulai:synthetic-review',
  'Maison Safran',
  'Comptoir Atlas',
  'REV-9201-',
  'IA-REV-',
  'BILLING-REVIEW-',
  'SYNTHETIC-CCP-NOT-PAYABLE',
  '/local-d1/session',
  'https://127.0.0.1:8444',
  'moulai_integrated',
];
for (const name of files) {
  const source = fs.readFileSync(path.join(directory, 'assets', name), 'utf8');
  for (const marker of forbidden)
    assert(
      !source.includes(marker),
      `Forbidden local fixture ${marker} in ${name}`,
    );
  assert(
    !/syntheticAdapter|restaurantFixtures|intelligenceFixtures|billingFixtures|LocalDiningPage/.test(
      name,
    ),
    `Local fixture chunk ${name}`,
  );
}
const source = files
  .map((name) => fs.readFileSync(path.join(directory, 'assets', name), 'utf8'))
  .join('\n');
assert(source.includes('authenticated-staging'));
assert(source.includes('/api/web'));
console.info(
  `Staging build verified: ${files.length} JavaScript assets, authenticated mode, known fixture markers absent.`,
);

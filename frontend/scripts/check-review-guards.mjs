// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import assert from 'node:assert/strict';
import { resolveConfig } from 'vite';

/** Resolve real configurations without starting a server or building assets. */
for (const mode of ['review', 'dining']) {
  await assert.rejects(
    resolveConfig({ mode, logLevel: 'silent' }, 'build'),
    /Synthetic review mode cannot be built/,
  );
  await assert.rejects(
    resolveConfig(
      { mode, logLevel: 'silent', server: { host: '0.0.0.0' } },
      'serve',
    ),
    /Synthetic review must bind to an explicit loopback host/,
  );
}
// The operational host is a local development entry, never a publication mode.
await assert.rejects(
  resolveConfig({ mode: 'operational', logLevel: 'silent' }, 'build'),
  /Synthetic review mode cannot be built/,
);
console.info(
  'Review guards passed: review/dining non-loopback binding and review/dining/operational publication builds refused.',
);

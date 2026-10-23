// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import assert from 'node:assert/strict';
import { resolveConfig } from 'vite';

/** Resolve real configurations without starting a server or building assets. */
await assert.rejects(
  resolveConfig({ mode: 'review', logLevel: 'silent' }, 'build'),
  /Synthetic review mode cannot be built/,
);
await assert.rejects(
  resolveConfig(
    { mode: 'review', logLevel: 'silent', server: { host: '0.0.0.0' } },
    'serve',
  ),
  /Synthetic review must bind to an explicit loopback host/,
);
console.info(
  'Review guards passed: publication build and non-loopback binding refused.',
);

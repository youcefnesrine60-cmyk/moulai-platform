// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import type { AccessAdapter } from './contracts';
import { disconnectedAdapter } from './disconnected';

/** Rollup removes this review-only import from every production build. */
export async function createAccessAdapter(): Promise<AccessAdapter> {
  if (import.meta.env.DEV && import.meta.env.MODE === 'review') {
    if (
      !['127.0.0.1', 'localhost', '[::1]'].includes(
        globalThis.location.hostname,
      )
    ) {
      return disconnectedAdapter;
    }
    const { createSyntheticAdapter } =
      await import('../../review/syntheticAdapter');
    return createSyntheticAdapter();
  }
  return disconnectedAdapter;
}

// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

/** A one-to-one display reference; the persisted canonical reference never changes. */
export function shortReference(id: number): string {
  return `R-${id.toString(36).toUpperCase().padStart(4, '0')}`;
}

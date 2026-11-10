// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// MoulAI™ — presentation of server capabilities, never an authorization grant.
export function localSections(capabilities: readonly string[]): string[] {
  const has = (...values: string[]) =>
    values.some((value) => capabilities.includes(value));
  return [
    'planning',
    ...(has('configure') ? ['configuration'] : []),
    ...(has('configure') ? ['staff'] : []),
    ...(has(
      'service',
      'assistant',
      'collect',
      'finance.read',
      'configure',
      'reservations.cancel_before_arrival',
      'customer',
    )
      ? ['requests']
      : []),
    ...(has(
      'configure',
      'service',
      'clean',
      'orders.read',
      'orders.approve',
      'orders.prepare',
      'orders.complete',
      'documents.issue',
      'finance.read',
    )
      ? ['visits']
      : []),
    ...(has('finance.read') ? ['finance'] : []),
    ...(has(
      'service',
      'assistant',
      'collect',
      'finance.read',
      'configure',
      'reservations.cancel_before_arrival',
    )
      ? ['history']
      : []),
  ];
}

/** Choose a useful view from explicit capabilities; never infer or grant a permission from a role title. */
export function preferredSection(capabilities: readonly string[]): string {
  if (capabilities.includes('configure') || capabilities.includes('service'))
    return 'planning';
  if (capabilities.includes('orders.prepare')) return 'visits';
  if (capabilities.includes('finance.read')) return 'finance';
  if (capabilities.includes('orders.read') || capabilities.includes('collect'))
    return 'visits';
  return 'planning';
}

// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import type { LocalizedLabel } from '../access/contracts';
import type { RestaurantScope } from '../business/contracts';

/** Decimal strings are transport values; JavaScript floats never price an invoice. */
export interface DiningScope extends RestaurantScope {
  readonly branchId: number;
}
export type DiningCapability =
  'read' | 'service' | 'clean' | 'collect' | 'configure';
export type PhysicalState =
  'available' | 'occupied' | 'dirty' | 'maintenance' | 'out_of_service';
export interface DiningBranch {
  readonly id: number;
  readonly name: LocalizedLabel;
}
export interface DiningTableView {
  readonly id: number;
  readonly code: string;
  readonly capacity: readonly [number, number];
  readonly physical: PhysicalState;
  readonly zone: LocalizedLabel;
  readonly occupiedSince: string | null;
  readonly expectedEnd: string | null;
  readonly nextReservation: string | null;
  readonly fullyReserved: boolean;
}
export interface DiningRequestView {
  readonly id: number;
  readonly reference: string;
  readonly tableId: number;
  readonly party: number;
  readonly startsAt: string;
  readonly endsAt: string;
  readonly status: 'pending' | 'held' | 'confirmed' | 'served';
  readonly humanProof: boolean;
  readonly delivery: 'pending' | 'delivered';
}
export interface FoodInvoiceView {
  readonly id: number;
  readonly requestId: number;
  readonly status: 'draft' | 'finalized';
  readonly currency: string;
  readonly total: string;
  readonly received: string;
  readonly allocated: string;
  readonly balance: string;
  readonly receipt: 'verified' | 'absent';
  readonly source: 'synthetic-reconciled-decimal';
}
export interface DiningWorkspace {
  readonly scope: DiningScope;
  readonly source: 'synthetic';
  readonly timezone: string;
  readonly capabilities: readonly DiningCapability[];
  readonly tables: readonly DiningTableView[];
  readonly requests: readonly DiningRequestView[];
  readonly invoice: FoodInvoiceView | null;
}
export type DiningReviewCommand =
  | { readonly kind: 'departure' | 'clean'; readonly tableId: number }
  | { readonly kind: 'finalizeInvoice'; readonly invoiceId: number };
export interface DiningAdapter {
  diningBranches(
    scope: RestaurantScope,
    signal: AbortSignal,
  ): Promise<readonly DiningBranch[]>;
  diningWorkspace(
    scope: DiningScope,
    date: string,
    signal: AbortSignal,
  ): Promise<DiningWorkspace>;
  simulateDining(
    scope: DiningScope,
    command: DiningReviewCommand,
    signal: AbortSignal,
  ): Promise<void>;
}

/** Exact two-decimal review amount arithmetic; no general commercial currency defaults. */
export function syntheticBalance(total: string, advance: string): string {
  const minor = (value: string): bigint => {
    if (!/^\d+\.\d{2}$/.test(value))
      throw new Error('Invalid exact review amount');
    return BigInt(value.replace('.', ''));
  };
  const result = minor(total) - minor(advance);
  if (result < 0n) throw new Error('Excess requires human review');
  return `${result / 100n}.${(result % 100n).toString().padStart(2, '0')}`;
}

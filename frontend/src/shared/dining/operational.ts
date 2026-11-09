// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import type { PhysicalState } from './contracts';
import { isWallClock, checkedInstant, checkedTimezone } from './temporal';

/** Display-only contracts: never infer an authorization or perform a state transition. */
export const physicalStates = [
  'available',
  'occupied',
  'dirty',
  'maintenance',
  'out_of_service',
] as const satisfies readonly PhysicalState[];
export type DisplayPhysical = PhysicalState | 'unknown';
export type DiningTone =
  | 'green'
  | 'orange'
  | 'amber'
  | 'purple'
  | 'gray'
  | 'blue'
  | 'neutral'
  | 'danger';
export type OperationalBadgeKind =
  | DisplayPhysical
  | 'full'
  | 'confirmed'
  | 'hold'
  | 'holdExpired'
  | 'paymentPending'
  | 'paymentReview'
  | 'humanPending'
  | 'closed'
  | 'planningUnknown'
  | 'planningOccupation';
export interface OperationalPeriod {
  readonly kind:
    'reservation' | 'hold' | 'occupation' | 'maintenance' | 'closure';
  readonly start: string;
  readonly end: string;
  readonly expires?: string | null;
  readonly reason?: string | null;
}
export interface OperationalFact {
  readonly label: string;
  readonly key?: string;
  readonly value: string | null;
  readonly temporal?: boolean;
}
export interface OperationalRequest {
  readonly id?: number;
  readonly reference: string;
  readonly status: string;
  readonly holdExpires?: string | null;
  readonly badges: readonly OperationalBadgeKind[];
}
export interface OperationalTable {
  readonly id: number;
  readonly code: string;
  readonly physical: DisplayPhysical;
  readonly capacity: readonly [number, number];
  readonly location: string | null;
  readonly facts: readonly OperationalFact[];
  readonly planningKnown: boolean;
  readonly fullyReserved: boolean;
  readonly closed: boolean;
  readonly nextReservation: OperationalPeriod | null;
  readonly periods: readonly OperationalPeriod[];
  readonly requests: readonly OperationalRequest[];
  readonly alerts: readonly string[];
}
export function displayPhysical(value: string): DisplayPhysical {
  return physicalStates.find((state) => state === value) ?? 'unknown';
}
export function countPhysical(
  tables: readonly OperationalTable[],
): Readonly<Record<DisplayPhysical, number>> {
  const counts: Record<DisplayPhysical, number> = {
    available: 0,
    occupied: 0,
    dirty: 0,
    maintenance: 0,
    out_of_service: 0,
    unknown: 0,
  };
  for (const table of tables) counts[table.physical]++;
  return counts;
}
/** Dates include the branch timezone; time-only legacy review values stay visibly unconverted. */
export function displayMoment(
  value: string,
  locale: string,
  timezone: string,
  contextDay?: string,
): string {
  checkedTimezone(timezone);
  if (isWallClock(value)) return value;
  const date = checkedInstant(value);
  return new Intl.DateTimeFormat(locale, {
    timeZone: timezone,
    ...(contextDay && civilDay(value, timezone) === contextDay
      ? {}
      : { dateStyle: 'long' as const }),
    timeStyle: 'short',
    hourCycle: 'h23',
  }).format(date);
}

/** Compare branch civil dates without converting a date-only planning key. */
export function civilDay(value: string, timezone: string): string | null {
  checkedTimezone(timezone);
  if (isWallClock(value)) return null;
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: timezone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(checkedInstant(value));
  return ['year', 'month', 'day']
    .map((kind) => parts.find((part) => part.type === kind)?.value ?? '')
    .join('-');
}

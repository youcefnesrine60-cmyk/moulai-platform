// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import type { DiningWorkspace } from '../../shared/dining/contracts';
import {
  displayPhysical,
  type OperationalTable,
  type OperationalPeriod,
} from '../../shared/dining/operational';

/** Synthetic projections remain labelled as simulations; missing observations stay unknown. */
export function reviewTablePresentation(
  data: DiningWorkspace,
  locale: 'fr' | 'en' | 'ar',
): readonly OperationalTable[] {
  return data.tables.map((table) => {
    const match = table.nextReservation?.match(
      /^(\d{2}:\d{2})[–—](\d{2}:\d{2})$/,
    );
    const next: OperationalPeriod | null =
      match?.[1] && match[2]
        ? { kind: 'reservation', start: match[1], end: match[2] }
        : null;
    return {
      id: table.id,
      code: table.code,
      physical: displayPhysical(table.physical),
      capacity: table.capacity,
      location: table.zone[locale],
      facts:
        table.physical === 'occupied'
          ? [
              {
                label: 'arrivalActual',
                value: table.occupiedSince,
                temporal: true,
              },
              {
                label: 'endExpected',
                value: table.expectedEnd,
                temporal: true,
              },
            ]
          : table.physical === 'dirty'
            ? [
                { label: 'cleanStartExpected', value: null },
                { label: 'cleanEndExpected', value: null },
                { label: 'cleanStartActual', value: null },
                { label: 'cleanEndActual', value: null },
              ]
            : ['maintenance', 'out_of_service'].includes(table.physical)
              ? [
                  { label: 'blockReason', value: null },
                  { label: 'unavailableUntil', value: null },
                ]
              : [],
      planningKnown: true,
      fullyReserved: table.fullyReserved,
      closed: false,
      nextReservation: next,
      periods: next ? [next] : [],
      alerts: [],
      requests: data.requests
        .filter((row) => row.tableId === table.id)
        .map((row) => ({
          id: row.id,
          reference: row.reference,
          status: row.status,
          badges:
            row.status === 'pending' && !row.humanProof
              ? ['humanPending' as const]
              : row.status === 'held'
                ? ['hold' as const]
                : [],
        })),
    };
  });
}

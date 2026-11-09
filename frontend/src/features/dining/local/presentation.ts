// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import type {
  Snapshot,
  Planning,
  StoredRequest,
} from '../../../shared/dining/local/client';
import {
  displayPhysical,
  type OperationalTable,
  type OperationalBadgeKind,
  type OperationalPeriod,
  type OperationalFact,
} from '../../../shared/dining/operational';
import { civilDay } from '../../../shared/dining/operational';
import {
  checkedInstant,
  checkedTimezone,
  checkedDay,
} from '../../../shared/dining/temporal';

/** Branch-local dates are presentation boundaries, never reservation validation. */
function dateAt(value: string, zone: string): string | null {
  checkedInstant(value);
  return civilDay(value, zone);
}
function onDay(start: string, end: string, day: string, zone: string): boolean {
  const first = dateAt(start, zone);
  const time = checkedInstant(end).getTime();
  const last = dateAt(new Date(time - 1).toISOString(), zone);
  return first !== null && last !== null && first <= day && day <= last;
}
/** These badges report persisted facts; they do not approve money or human availability. */
export function requestPresentation(
  data: Snapshot,
  request: StoredRequest,
): readonly OperationalBadgeKind[] {
  if (!['pending', 'held'].includes(request.status)) return [];
  const badges: OperationalBadgeKind[] = ['humanPending'];
  if (request.status === 'held') {
    const claims =
      data.claims?.filter(
        (row) =>
          row.request_id === request.id && row.active && row.kind === 'hold',
      ) ?? [];
    const at = Date.parse(data.server_time ?? '');
    const current = claims.some(
      (row) => row.expires_at !== null && Date.parse(row.expires_at) > at,
    );
    const expired =
      claims.length > 0 &&
      claims.every(
        (row) => row.expires_at !== null && Date.parse(row.expires_at) <= at,
      );
    badges.unshift(expired ? 'holdExpired' : 'hold');
    if (current && data.receipts !== undefined) {
      const receipts = data.receipts.filter(
        (row) => row.request_id === request.id,
      );
      const quote = data.quotes?.find((row) => row.request_id === request.id);
      if (receipts.length && !receipts.some((row) => row.status === 'verified'))
        badges.push('paymentReview');
      else if (!receipts.length && quote && !/^0+(?:\.0+)?$/.test(quote.amount))
        badges.push('paymentPending');
    }
  }
  return badges;
}
export function localTablePresentation(
  data: Snapshot,
  planning: Planning | null,
  day: string,
  locale: 'fr' | 'en' | 'ar',
): readonly OperationalTable[] {
  const timezone = data.policy?.timezone;
  if (data.tables?.length) {
    checkedTimezone(timezone ?? '');
    checkedInstant(data.server_time ?? '');
  }
  if (timezone) checkedTimezone(timezone);
  checkedDay(day);
  if (data.server_time) checkedInstant(data.server_time);
  const at = Date.parse(data.server_time ?? '');
  return (data.tables ?? []).map((table) => {
    const plan = planning?.find((row) => row.id === table.id);
    const active = (data.occupation_tables ?? []).find(
      (row) => row.table_id === table.id && row.active,
    );
    const actual = data.occupations?.find(
      (row) => row.id === active?.occupation_id,
    );
    const facts: OperationalFact[] = [];
    const alerts: string[] = [];
    if (table.physical_state === 'occupied') {
      facts.push(
        {
          label: 'arrivalActual',
          value: actual?.arrived_at ?? null,
          temporal: true,
        },
        {
          label: 'endExpected',
          value: actual?.expected_end ?? null,
          temporal: true,
        },
      );
      if (
        actual &&
        Date.parse(actual.expected_end) < at &&
        actual.departed_at === null
      )
        alerts.push('occupationLate');
    }
    if (table.physical_state === 'dirty') {
      facts.push(
        {
          label: 'cleanStartExpected',
          value: actual?.cleaning_expected_start ?? null,
          temporal: true,
        },
        {
          label: 'cleanEndExpected',
          value: actual?.cleaning_expected_end ?? null,
          temporal: true,
        },
        {
          label: 'cleanStartActual',
          value: actual?.cleaning_actual_start ?? null,
          temporal: true,
        },
        {
          label: 'cleanEndActual',
          value: actual?.cleaning_actual_end ?? null,
          temporal: true,
        },
      );
      if (
        actual &&
        actual.cleaning_actual_end === null &&
        Date.parse(actual.cleaning_expected_end) < at
      )
        alerts.push('cleaningLate');
    }
    const applicable = (data.blackouts ?? []).filter(
      (row) =>
        row.active &&
        (row.table_id === table.id ||
          row.zone_id === table.zone_id ||
          (row.table_id === null && row.zone_id === null)),
    );
    if (['maintenance', 'out_of_service'].includes(table.physical_state)) {
      const blocks = applicable.filter(
        (row) =>
          Date.parse(row.starts_at) <= at && at < Date.parse(row.ends_at),
      );
      facts.push({
        label: 'blockReason',
        value: blocks.map((row) => row.reason).join(' · ') || null,
      });
      if (blocks.length)
        for (const block of blocks)
          facts.push(
            {
              label: 'unavailableFrom',
              key: `from_${block.id}`,
              value: block.starts_at,
              temporal: true,
            },
            {
              label: 'unavailableUntil',
              key: `until_${block.id}`,
              value: block.ends_at,
              temporal: true,
            },
          );
      else
        facts.push({ label: 'unavailableUntil', value: null, temporal: true });
    }
    const periods: OperationalPeriod[] = (plan?.claims ?? []).map((claim) => ({
      kind:
        claim.kind === 'reservation'
          ? 'reservation'
          : claim.kind === 'hold'
            ? 'hold'
            : 'occupation',
      start: claim.start,
      end: claim.end,
      expires:
        claim.kind === 'hold'
          ? (data.claims?.find(
              (row) =>
                row.table_id === table.id &&
                row.request_id === claim.request_id &&
                row.active &&
                row.kind === 'hold',
            )?.expires_at ?? null)
          : null,
    }));
    if (timezone)
      for (const block of applicable.filter((row) =>
        onDay(row.starts_at, row.ends_at, day, timezone),
      ))
        periods.push({
          kind: block.kind === 'maintenance' ? 'maintenance' : 'closure',
          start: block.starts_at,
          end: block.ends_at,
          reason: block.reason,
        });
    const next =
      periods
        .filter(
          (row) => row.kind === 'reservation' && Date.parse(row.start) >= at,
        )
        .sort((a, b) => Date.parse(a.start) - Date.parse(b.start))[0] ?? null;
    if (
      periods.some(
        (claim) =>
          claim.kind === 'reservation' &&
          applicable.some(
            (block) =>
              Date.parse(block.starts_at) < Date.parse(claim.end) &&
              Date.parse(block.ends_at) > Date.parse(claim.start),
          ),
      )
    )
      alerts.push('planningConflict');
    const linked = new Set(
      (data.request_tables ?? [])
        .filter((row) => row.table_id === table.id)
        .map((row) => row.request_id),
    );
    const requests = (data.requests ?? [])
      .filter(
        (row) =>
          linked.has(row.id) &&
          timezone &&
          onDay(row.starts_at, row.ends_at, day, timezone),
      )
      .map((row) => ({
        id: row.id,
        reference: row.reference,
        status: row.status,
        holdExpires:
          data.claims?.find(
            (claim) =>
              claim.request_id === row.id &&
              claim.active &&
              claim.kind === 'hold',
          )?.expires_at ?? null,
        badges: requestPresentation(data, row),
      }));
    if (requests.some((row) => row.status === 'manual_review'))
      alerts.push('manualReview');
    const location = [table.zone_id, table.location_id]
      .map(
        (id) => data.references?.find((row) => row.id === id)?.labels[locale],
      )
      .filter(Boolean)
      .join(' · ');
    return {
      id: table.id,
      code: table.code,
      physical: displayPhysical(table.physical_state),
      capacity: [table.min_capacity, table.max_capacity] as const,
      location: location || null,
      facts,
      planningKnown: plan !== undefined,
      fullyReserved: plan?.fully_reserved ?? false,
      closed: plan?.closed ?? false,
      nextReservation: next,
      periods,
      requests,
      alerts,
    };
  });
}

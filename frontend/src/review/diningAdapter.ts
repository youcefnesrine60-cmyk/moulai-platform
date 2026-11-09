// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { AccessError } from '../shared/access/contracts';
import type { RestaurantScope } from '../shared/business/contracts';
import {
  syntheticBalance,
  type DiningAdapter,
  type DiningScope,
  type DiningWorkspace,
} from '../shared/dining/contracts';

/** Explicit, in-memory fiction. No server, payment, QR authority or live restaurant. */
export function createDiningAdapter(
  authorize: (scope: RestaurantScope, permission: string) => void,
  canOperate: () => boolean,
  pause: (signal: AbortSignal) => Promise<void>,
  generation: () => number,
): DiningAdapter & { reset(): void } {
  const workspaces = new Map<string, DiningWorkspace>();
  const key = (scope: DiningScope): string =>
    `${scope.organizationId}:${scope.restaurantId}:${scope.branchId}`;
  const admit = (scope: DiningScope): void => {
    authorize(scope, 'tenant.restaurants.read');
    if (
      ![scope.restaurantId * 100 + 1, scope.restaurantId * 100 + 2].includes(
        scope.branchId,
      )
    )
      throw new AccessError('notFound');
  };
  const seed = (scope: DiningScope): DiningWorkspace => ({
    scope,
    source: 'synthetic',
    timezone: 'Africa/Algiers',
    capabilities: canOperate()
      ? ['read', 'service', 'clean', 'collect', 'configure']
      : ['read'],
    tables: [
      {
        id: 1,
        code: 'T01',
        capacity: [2, 4],
        physical: 'occupied',
        zone: { fr: 'Terrasse', en: 'Terrace', ar: 'الشرفة' },
        occupiedSince: '20:05',
        expectedEnd: '21:30',
        nextReservation: '22:00–23:30',
        fullyReserved: false,
      },
      {
        id: 2,
        code: 'T02',
        capacity: [1, 2],
        physical: 'dirty',
        zone: { fr: 'Salle', en: 'Dining room', ar: 'القاعة' },
        occupiedSince: null,
        expectedEnd: null,
        nextReservation: '22:00–23:00',
        fullyReserved: false,
      },
      {
        id: 3,
        code: 'T03',
        capacity: [2, 6],
        physical: 'available',
        zone: { fr: 'Jardin', en: 'Garden', ar: 'الحديقة' },
        occupiedSince: null,
        expectedEnd: null,
        nextReservation: '20:00–23:00',
        fullyReserved: true,
      },
      {
        id: 4,
        code: 'T04',
        capacity: [2, 4],
        physical: 'maintenance',
        zone: { fr: 'Salle', en: 'Dining room', ar: 'القاعة' },
        occupiedSince: null,
        expectedEnd: null,
        nextReservation: null,
        fullyReserved: false,
      },
    ],
    requests: [
      {
        id: 1,
        reference: 'DEMO-RSV-001',
        tableId: 1,
        party: 4,
        startsAt: '20:00',
        endsAt: '21:30',
        status: 'confirmed',
        humanProof: true,
        delivery: 'delivered',
      },
      {
        id: 2,
        reference: 'DEMO-RSV-002',
        tableId: 2,
        party: 2,
        startsAt: '22:00',
        endsAt: '23:00',
        status: 'pending',
        humanProof: false,
        delivery: 'pending',
      },
    ],
    invoice: {
      id: 1,
      requestId: 1,
      status: 'draft',
      currency: 'DZD',
      total: '6000.00',
      received: '1500.00',
      allocated: '0.00',
      balance: '6000.00',
      receipt: 'verified',
      source: 'synthetic-reconciled-decimal',
    },
  });
  const get = (scope: DiningScope): DiningWorkspace => {
    const id = key(scope);
    const value = workspaces.get(id) ?? seed(scope);
    workspaces.set(id, value);
    return value;
  };
  return {
    reset() {
      workspaces.clear();
    },
    async diningBranches(scope, signal) {
      const admittedGeneration = generation();
      await pause(signal);
      if (admittedGeneration !== generation())
        throw new AccessError('noAccess');
      authorize(scope, 'tenant.restaurants.read');
      return [
        {
          id: scope.restaurantId * 100 + 1,
          name: {
            fr: 'Succursale Centre — fictive',
            en: 'Central branch — fictional',
            ar: 'فرع المركز — تجريبي',
          },
        },
        {
          id: scope.restaurantId * 100 + 2,
          name: {
            fr: 'Succursale Jardin — fictive',
            en: 'Garden branch — fictional',
            ar: 'فرع الحديقة — تجريبي',
          },
        },
      ];
    },
    async diningWorkspace(scope, date, signal) {
      const admittedGeneration = generation();
      await pause(signal);
      if (admittedGeneration !== generation())
        throw new AccessError('noAccess');
      admit(scope);
      if (
        !/^\d{4}-\d{2}-\d{2}$/.test(date) ||
        Number.isNaN(Date.parse(`${date}T00:00:00Z`)) ||
        new Date(`${date}T00:00:00Z`).toISOString().slice(0, 10) !== date
      )
        throw new AccessError('notFound');
      const current = get(scope);
      return structuredClone(
        date === '2026-11-03'
          ? current
          : {
              ...current,
              tables: current.tables.map((table) => ({
                ...table,
                fullyReserved: false,
                nextReservation: null,
              })),
              requests: [],
              invoice: null,
            },
      );
    },
    async simulateDining(scope, command, signal) {
      const admittedGeneration = generation();
      await pause(signal);
      if (admittedGeneration !== generation())
        throw new AccessError('noAccess');
      admit(scope);
      if (!canOperate()) throw new AccessError('noAccess');
      const current = get(scope);
      if (command.kind === 'finalizeInvoice') {
        if (!current.invoice || command.invoiceId !== current.invoice.id)
          throw new AccessError('notFound');
        if (current.invoice.status === 'finalized') return;
        workspaces.set(key(scope), {
          ...current,
          invoice: {
            ...current.invoice,
            status: 'finalized',
            allocated: current.invoice.received,
            balance: syntheticBalance(
              current.invoice.total,
              current.invoice.received,
            ),
          },
        });
      } else {
        const table = current.tables.find((row) => row.id === command.tableId);
        if (
          !table ||
          (command.kind === 'departure' && table.physical !== 'occupied') ||
          (command.kind === 'clean' && table.physical !== 'dirty')
        )
          throw new AccessError('noAccess');
        workspaces.set(key(scope), {
          ...current,
          tables: current.tables.map((row) =>
            row.id !== table.id
              ? row
              : {
                  ...row,
                  physical:
                    command.kind === 'departure' ? 'dirty' : 'available',
                  occupiedSince: null,
                  expectedEnd: null,
                },
          ),
        });
      }
    },
  };
}
